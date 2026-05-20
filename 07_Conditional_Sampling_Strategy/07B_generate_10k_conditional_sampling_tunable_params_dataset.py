from pathlib import Path
import numpy as np
import pandas as pd

# ============================================================
# CONFIG
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

PATIENT_ID = "pediatric_dcm_population_100"
CAMPAIGN_NAME = "conditional_sampling_100_patients_100_variations_v1"

N_VARIATIONS_PER_PATIENT = 100
RANDOM_SEED = 42
CHUNK_SIZE = 50

patients_csv = (
    ROOT
    / "01_Data"
    / "Conditional_Sampling"
    / "patients"
    / "conditional_sampling_100_patients.csv"
)

bounds_csv = (
    ROOT
    / "01_Data"
    / "patient_configs"
    / "pediatric_dcm_patient_01"
    / "stage_1_tunable_bounds_v3_physiological.csv"
)

output_dir = (
    ROOT
    / "01_Data"
    / "Conditional_Sampling"
    / "generated_samples"
    / CAMPAIGN_NAME
)

chunks_dir = output_dir / "chunks"
output_dir.mkdir(parents=True, exist_ok=True)
chunks_dir.mkdir(parents=True, exist_ok=True)

# ============================================================
# LOAD DATA
# ============================================================

patients = pd.read_csv(patients_csv)
bounds = pd.read_csv(bounds_csv)

required_bound_cols = {"variable", "lower_bound", "upper_bound"}
missing = required_bound_cols - set(bounds.columns)

if missing:
    raise ValueError(f"Missing columns in bounds CSV: {missing}")

tunables = bounds["variable"].tolist()

# ============================================================
# LATIN HYPERCUBE SAMPLING
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

# ============================================================
# GENERATE 100 VARIATIONS PER PATIENT
# ============================================================

rows = []
global_simulation_id = 1

for _, patient in patients.iterrows():

    patient_id = int(patient["patient_id"])

    lhs = latin_hypercube(
        n_samples=N_VARIATIONS_PER_PATIENT,
        n_dimensions=len(tunables),
        seed=RANDOM_SEED + patient_id,
    )

    for variation_id in range(1, N_VARIATIONS_PER_PATIENT + 1):

        row = {
            "simulation_id": global_simulation_id,
            "patient_id": patient_id,
            "variation_id": variation_id,
            "campaign_name": CAMPAIGN_NAME,
            "sampling_method": "conditional_patient_sampling_plus_lhs_tunables",
            "random_seed": RANDOM_SEED,
        }

        # Add patient-specific variables
        for col in patients.columns:
            if col != "patient_id":
                row[col] = patient[col]

        # Add tunable parameters
        for j, variable in enumerate(tunables):
            b = bounds.loc[bounds["variable"] == variable].iloc[0]
            lower = b["lower_bound"]
            upper = b["upper_bound"]

            row[variable] = lower + lhs[variation_id - 1, j] * (upper - lower)

        rows.append(row)
        global_simulation_id += 1

dataset = pd.DataFrame(rows)

# ============================================================
# SAVE FULL DATASET
# ============================================================

full_output_path = output_dir / f"{CAMPAIGN_NAME}_FULL_INPUT_DATASET.csv"
dataset.to_csv(full_output_path, index=False)

# ============================================================
# CREATE CHUNKS + MANIFEST FOR SLURM
# ============================================================

n_chunks = int(np.ceil(len(dataset) / CHUNK_SIZE))
manifest_rows = []

results_base_dir = (
    ROOT
    / "01_Data"
    / "Conditional_Sampling"
    / "simulation_results"
    / CAMPAIGN_NAME
)

results_chunks_dir = results_base_dir / "chunks"
logs_dir = results_base_dir / "logs"

results_chunks_dir.mkdir(parents=True, exist_ok=True)
logs_dir.mkdir(parents=True, exist_ok=True)

for chunk_id in range(1, n_chunks + 1):

    start = (chunk_id - 1) * CHUNK_SIZE
    end = min(start + CHUNK_SIZE, len(dataset))

    chunk_df = dataset.iloc[start:end].copy()

    chunk_samples_path = chunks_dir / f"samples_chunk_{chunk_id:05d}.csv"
    chunk_results_path = results_chunks_dir / f"results_chunk_{chunk_id:05d}.csv"

    chunk_df.to_csv(chunk_samples_path, index=False)

    manifest_rows.append({
        "array_id": chunk_id,
        "samples_path": chunk_samples_path.as_posix(),
        "results_path": chunk_results_path.as_posix(),
        "n_cases": len(chunk_df),
    })

manifest = pd.DataFrame(manifest_rows)

manifest_path = output_dir / f"{CAMPAIGN_NAME}_manifest.csv"
manifest.to_csv(manifest_path, index=False)

# ============================================================
# SUMMARY
# ============================================================

print("=" * 80)
print("07B CONDITIONAL SAMPLING DATASET GENERATION COMPLETE")
print("=" * 80)
print(f"Patients loaded: {len(patients)}")
print(f"Variations per patient: {N_VARIATIONS_PER_PATIENT}")
print(f"Total simulations: {len(dataset)}")
print(f"Number of chunks: {n_chunks}")
print(f"Chunk size: {CHUNK_SIZE}")

print("\nFull input dataset:")
print(full_output_path)

print("\nManifest:")
print(manifest_path)

print("\nResults directory:")
print(results_base_dir)

print("\nUse this in SLURM:")
print(f"#SBATCH --array=1-{n_chunks}%20")
print("=" * 80)