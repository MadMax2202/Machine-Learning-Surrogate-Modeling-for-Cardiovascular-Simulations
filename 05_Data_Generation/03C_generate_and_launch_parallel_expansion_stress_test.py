import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd


# ------------------------------------------------------------
# 1. Paths
# ------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

samples_dir = (
    ROOT
    / "01_Data"
    / "generated_samples"
    / "pediatric_dcm_patient_01"
    / "expansion_stress_test_1000"
)

results_dir = (
    ROOT
    / "01_Data"
    / "simulation_results"
    / "pediatric_dcm_patient_01"
    / "expansion_stress_test_1000"
)

chunks_samples_dir = samples_dir / "chunks"
chunks_results_dir = results_dir / "chunks"

samples_dir.mkdir(parents=True, exist_ok=True)
results_dir.mkdir(parents=True, exist_ok=True)
chunks_samples_dir.mkdir(parents=True, exist_ok=True)
chunks_results_dir.mkdir(parents=True, exist_ok=True)

samples_path = samples_dir / "pediatric_dcm_patient_01_expansion_stress_test_1000_samples.csv"
final_results_path = results_dir / "pediatric_dcm_patient_01_expansion_stress_test_1000_results.csv"

matlab_script_dir = ROOT / "04_Matlab_&_Simulink"
matlab_runner_name = "run_parallel_expansion_stress_test_pediatric_noVAD_linear"


# ------------------------------------------------------------
# 2. Settings
# ------------------------------------------------------------

# 4 MATLAB processes = 4 parallel chunks.
num_matlab_processes = 4

# TEST MODE:
# 10 per expansion factor -> 40 total simulations.
cases_per_expansion_factor = 250

# Later, for full 1000:
# cases_per_expansion_factor = 250

tunables = [
    "k_Vtot",
    "k_Vsys",
    "k_Vusv_sys",
    "k_Vusv_sys_ven",
    "k_Vusv_pulm_ven",
    "k_Ctot",
    "k_Csys",
    "k_Rsysven",
    "k_Rpulmart",
    "k_ESP_LV",
    "k_ESP_RV",
]


# ------------------------------------------------------------
# 3. Baseline values
# IMPORTANT:
# Replace with your exact baseline values if these are not the same
# as your previous stress-test generator.
# ------------------------------------------------------------

baseline = {
    "k_Vtot": 77.0,
    "k_Vsys": 0.82,
    "k_Vusv_sys": 0.82,
    "k_Vusv_sys_ven": 0.93,
    "k_Vusv_pulm_ven": 0.86,
    "k_Ctot": 2.15,
    "k_Csys": 0.83,
    "k_Rsysven": 0.06,
    "k_Rpulmart": 0.63,
    "k_ESP_LV": 0.90,
    "k_ESP_RV": 0.90,
}


# ------------------------------------------------------------
# 4. Cleanup old outputs
# ------------------------------------------------------------

for old_file in chunks_results_dir.glob("results_chunk_*.csv"):
    old_file.unlink()

if final_results_path.exists():
    final_results_path.unlink()

for old_file in chunks_samples_dir.glob("samples_chunk_*.csv"):
    old_file.unlink()

if samples_path.exists():
    samples_path.unlink()


# ------------------------------------------------------------
# 5. Sample generation
# ------------------------------------------------------------

def latin_hypercube(
    n_samples: int,
    n_dim: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Simple dependency-free Latin Hypercube sampler in [0, 1].
    """
    result = np.zeros((n_samples, n_dim))

    for j in range(n_dim):
        cut = np.linspace(0, 1, n_samples + 1)
        points = cut[:-1] + rng.random(n_samples) * (1.0 / n_samples)
        rng.shuffle(points)
        result[:, j] = points

    return result


def generate_group(
    start_id: int,
    n_cases: int,
    expansion_factor: float,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Generate one expansion-factor group.

    Logic:
        factor 1.25 -> +/- 12.5%
        factor 1.50 -> +/- 25%
        factor 1.75 -> +/- 37.5%
        factor 2.00 -> +/- 50%
    """
    lhs = latin_hypercube(n_cases, len(tunables), rng)

    relative_spread = (expansion_factor - 1.0) / 2.0

    rows = []

    for i in range(n_cases):
        row = {
            "simulation_id": start_id + i,
            "expansion_factor": expansion_factor,
        }

        for j, name in enumerate(tunables):
            base = baseline[name]
            low = base * (1.0 - relative_spread)
            high = base * (1.0 + relative_spread)
            row[name] = low + lhs[i, j] * (high - low)

        rows.append(row)

    return pd.DataFrame(rows)


rng = np.random.default_rng(42)

groups = []
simulation_id = 1

for factor in [1.25, 1.50, 1.75, 2.00]:
    group = generate_group(
        start_id=simulation_id,
        n_cases=cases_per_expansion_factor,
        expansion_factor=factor,
        rng=rng,
    )
    groups.append(group)
    simulation_id += cases_per_expansion_factor

samples = pd.concat(groups, ignore_index=True)
samples.to_csv(samples_path, index=False)

print(f"Saved samples to: {samples_path}")
print("\nExpansion factor counts:")
print(samples["expansion_factor"].value_counts().sort_index())


# ------------------------------------------------------------
# 6. Split into chunks
# ------------------------------------------------------------

chunk_paths = []
chunk_result_paths = []

# Since the data is ordered by factor and we have 4 factors,
# this creates one chunk per expansion factor in test mode.
chunks = np.array_split(samples, num_matlab_processes)

# np.array_split can sometimes return arrays depending on versions,
# so force each chunk back to a DataFrame if needed.
fixed_chunks = []

for chunk in chunks:
    if isinstance(chunk, pd.DataFrame):
        fixed_chunks.append(chunk.copy())
    else:
        fixed_chunks.append(pd.DataFrame(chunk, columns=samples.columns))

for chunk_idx, chunk_df in enumerate(fixed_chunks, start=1):
    chunk_samples_path = chunks_samples_dir / f"samples_chunk_{chunk_idx:02d}.csv"
    chunk_results_path = chunks_results_dir / f"results_chunk_{chunk_idx:02d}.csv"

    chunk_df.to_csv(chunk_samples_path, index=False)

    chunk_paths.append(chunk_samples_path)
    chunk_result_paths.append(chunk_results_path)

print(f"\nCreated {len(chunk_paths)} chunks:")
for p in chunk_paths:
    print(f"  {p.name}")


# ------------------------------------------------------------
# 7. Launch one MATLAB process for one chunk
# ------------------------------------------------------------

def run_matlab_chunk(
    chunk_idx: int,
    chunk_samples_path: Path,
    chunk_results_path: Path,
) -> int:
    matlab_command = (
        f"{matlab_runner_name}("
        f"'{chunk_samples_path.as_posix()}', "
        f"'{chunk_results_path.as_posix()}'"
        f");"
    )

    cmd = [
        "matlab",
        "-batch",
        matlab_command,
    ]

    print(f"\nLaunching MATLAB chunk {chunk_idx:02d}...")
    print(" ".join(cmd))

    completed = subprocess.run(
        cmd,
        cwd=matlab_script_dir,
        check=False,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            f"MATLAB chunk {chunk_idx:02d} failed with return code "
            f"{completed.returncode}"
        )

    return chunk_idx


# ------------------------------------------------------------
# 8. Launch chunks in parallel
# ------------------------------------------------------------

print(f"\nLaunching {num_matlab_processes} MATLAB processes in parallel...")

with ThreadPoolExecutor(max_workers=num_matlab_processes) as executor:
    futures = []

    for idx, (chunk_samples_path, chunk_results_path) in enumerate(
        zip(chunk_paths, chunk_result_paths),
        start=1,
    ):
        futures.append(
            executor.submit(
                run_matlab_chunk,
                idx,
                chunk_samples_path,
                chunk_results_path,
            )
        )

    for future in as_completed(futures):
        finished_idx = future.result()
        print(f"MATLAB chunk {finished_idx:02d} finished.")


# ------------------------------------------------------------
# 9. Merge results
# ------------------------------------------------------------

print("\nMerging chunk results...")

result_dfs = []

for path in chunk_result_paths:
    if not path.exists():
        raise FileNotFoundError(f"Missing chunk result file: {path}")

    result_dfs.append(pd.read_csv(path))

final_results = pd.concat(result_dfs, ignore_index=True)
final_results = final_results.sort_values("simulation_id")

final_results.to_csv(final_results_path, index=False)

print(f"\nFinal results saved to: {final_results_path}")

print("\nSimulation status counts:")
print(final_results["simulation_status"].value_counts(dropna=False))

print("\nFailure rate by expansion factor:")
print(
    final_results
    .assign(failed=final_results["simulation_status"].eq("failed"))
    .groupby("expansion_factor")["failed"]
    .mean()
    .mul(100)
)

print("\nChunk result files:")
for path in chunk_result_paths:
    print(f"  {path}")