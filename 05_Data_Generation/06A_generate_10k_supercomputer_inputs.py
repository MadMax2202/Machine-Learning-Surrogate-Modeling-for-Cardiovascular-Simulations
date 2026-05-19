from pathlib import Path
import numpy as np
import pandas as pd


# ============================================================
# 06A - Generate 10k supercomputer inputs
# Pediatric DCM / no VAD / linear / stage 1 bounds v2
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

PATIENT_ID = "pediatric_dcm_patient_01"
CAMPAIGN_NAME = "stage_1_10k_supercomputer_v2"

N_SAMPLES = 10_000
CHUNK_SIZE = 50
RANDOM_SEED = 42


# ============================================================
# Paths matching your project structure
# ============================================================

samples_dir = (
    ROOT
    / "01_Data"
    / "generated_samples"
    / PATIENT_ID
    / CAMPAIGN_NAME
)

results_dir = (
    ROOT
    / "01_Data"
    / "simulation_results"
    / PATIENT_ID
    / CAMPAIGN_NAME
)

chunks_samples_dir = samples_dir / "chunks"
chunks_results_dir = results_dir / "chunks"
logs_dir = results_dir / "logs"

for folder in [
    samples_dir,
    results_dir,
    chunks_samples_dir,
    chunks_results_dir,
    logs_dir,
]:
    folder.mkdir(parents=True, exist_ok=True)


# ============================================================
# Stage 1 bounds v2
# From bounds stress-test error analysis
# ============================================================

stage_1_bounds_v2 = pd.DataFrame([
    ["k_Vtot", 67.5, 60.0, 85.0,
     "Keep original range; no clear instability pattern observed."],

    ["k_Vsys", 0.84, 0.75, 0.93,
     "Reduced upper bound to keep pulmonary blood volume fraction positive and avoid Vpulm_fraction violations."],

    ["k_Vusv_sys", 0.84, 0.75, 0.93,
     "Reduced upper bound to keep pulmonary unstressed volume fraction positive and avoid Vusv_pulm_fraction violations."],

    ["k_Vusv_sys_ven", 0.95, 0.90, 0.99,
     "Keep original range; no direct instability signal observed."],

    ["k_Vusv_pulm_ven", 0.90, 0.80, 0.97,
     "Keep original range; no direct instability signal observed."],

    ["k_Ctot", 2.15, 1.72, 2.58,
     "Keep original ±20% range; invalid cases were not driven by total compliance itself."],

    ["k_Csys", 0.85, 0.75, 0.93,
     "Reduced upper bound because failures and invalid outputs concentrate near k_Csys ≈ 1; ensures Cpulm_fraction remains safely positive."],

    ["k_Rsysven", 60 / 1000, 0.048, 0.072,
     "Keep original ±20% range; no clear instability pattern observed."],

    ["k_Rpulmart", 2 / 3, 0.50, 0.80,
     "Keep original range for now; possible secondary interaction but no clear standalone threshold."],

    ["k_ESP_LV", 0.90, 0.75, 1.05,
     "Keep original range; no clear standalone instability threshold."],

    ["k_ESP_RV", 0.90, 0.75, 1.05,
     "Keep original range; no clear standalone instability threshold."],

], columns=[
    "variable",
    "baseline",
    "lower_bound",
    "upper_bound",
    "bound_reason",
])


# ============================================================
# Latin Hypercube Sampling
# ============================================================

def latin_hypercube(n_samples: int, n_dimensions: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    lhs = np.zeros((n_samples, n_dimensions))

    for j in range(n_dimensions):
        cut_points = np.linspace(0, 1, n_samples + 1)
        points = rng.uniform(cut_points[:-1], cut_points[1:])
        rng.shuffle(points)
        lhs[:, j] = points

    return lhs


variables = stage_1_bounds_v2["variable"].tolist()
lhs = latin_hypercube(N_SAMPLES, len(variables), RANDOM_SEED)

samples = pd.DataFrame()
samples["simulation_id"] = np.arange(1, N_SAMPLES + 1, dtype=int)

for j, variable in enumerate(variables):
    row = stage_1_bounds_v2.loc[stage_1_bounds_v2["variable"] == variable].iloc[0]

    lower = row["lower_bound"]
    upper = row["upper_bound"]

    samples[variable] = lower + lhs[:, j] * (upper - lower)


# ============================================================
# Add metadata
# ============================================================

samples["campaign_name"] = CAMPAIGN_NAME
samples["bounds_version"] = "stage_1_bounds_v2"
samples["sampling_method"] = "latin_hypercube"
samples["random_seed"] = RANDOM_SEED


# ============================================================
# Save full files
# ============================================================

full_samples_path = samples_dir / f"{PATIENT_ID}_{CAMPAIGN_NAME}_samples.csv"
bounds_path = samples_dir / f"{PATIENT_ID}_{CAMPAIGN_NAME}_bounds.csv"

samples.to_csv(full_samples_path, index=False)
stage_1_bounds_v2.to_csv(bounds_path, index=False)

print("Saved full 10k sample dataset:")
print(full_samples_path)
print(f"Shape: {samples.shape}")

print("\nSaved bounds file:")
print(bounds_path)


# ============================================================
# Split into chunks for SLURM array
# ============================================================

n_chunks = int(np.ceil(N_SAMPLES / CHUNK_SIZE))
manifest_rows = []

for chunk_id in range(1, n_chunks + 1):
    start = (chunk_id - 1) * CHUNK_SIZE
    end = min(start + CHUNK_SIZE, N_SAMPLES)

    chunk_df = samples.iloc[start:end].copy()

    chunk_samples_path = chunks_samples_dir / f"samples_chunk_{chunk_id:05d}.csv"
    chunk_results_path = chunks_results_dir / f"results_chunk_{chunk_id:05d}.csv"

    chunk_df.to_csv(chunk_samples_path, index=False)

    manifest_rows.append({
        "array_id": chunk_id,
        "samples_path": chunk_samples_path.as_posix(),
        "results_path": chunk_results_path.as_posix(),
        "n_cases": len(chunk_df),
    })

manifest = pd.DataFrame(manifest_rows)

manifest_path = samples_dir / f"{PATIENT_ID}_{CAMPAIGN_NAME}_manifest.csv"
manifest.to_csv(manifest_path, index=False)

print("\nCreated SLURM chunks.")
print(f"Number of simulations: {N_SAMPLES}")
print(f"Chunk size: {CHUNK_SIZE}")
print(f"Number of chunks: {n_chunks}")
print(f"Manifest saved to:")
print(manifest_path)

print("\nUse this in SLURM:")
print(f"#SBATCH --array=1-{n_chunks}%50")