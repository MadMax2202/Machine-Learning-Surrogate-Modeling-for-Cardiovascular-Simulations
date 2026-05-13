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

chunks_results_dir = results_dir / "chunks"
resume_samples_dir = samples_dir / "resume_chunks"
resume_results_dir = results_dir / "resume_chunks"
resume_logs_dir = resume_results_dir / "logs"

resume_samples_dir.mkdir(parents=True, exist_ok=True)
resume_results_dir.mkdir(parents=True, exist_ok=True)
resume_logs_dir.mkdir(parents=True, exist_ok=True)

samples_path = samples_dir / "pediatric_dcm_patient_01_expansion_stress_test_1000_samples.csv"
final_results_path = results_dir / "pediatric_dcm_patient_01_expansion_stress_test_1000_results_RESUMED.csv"

matlab_script_dir = ROOT / "04_Matlab_&_Simulink"
matlab_runner_name = "run_parallel_expansion_stress_test_pediatric_noVAD_linear"


# ------------------------------------------------------------
# 2. Resume settings
# ------------------------------------------------------------

num_matlab_processes = 2
resume_chunk_size = 50


# ------------------------------------------------------------
# 3. Load original samples
# ------------------------------------------------------------

if not samples_path.exists():
    raise FileNotFoundError(f"Missing original samples file: {samples_path}")

samples = pd.read_csv(samples_path)

if "simulation_id" not in samples.columns:
    raise ValueError("samples file must contain a simulation_id column")

samples["simulation_id"] = samples["simulation_id"].astype(int)

print(f"Loaded original samples: {samples_path}")
print(f"Total original samples: {len(samples)}")


# ------------------------------------------------------------
# 4. Load existing partial results
# ------------------------------------------------------------

existing_result_files = []

existing_result_files.extend(sorted(chunks_results_dir.glob("results_chunk_*.csv")))
existing_result_files.extend(sorted(resume_results_dir.glob("resume_results_chunk_*.csv")))

existing_dfs = []

for path in existing_result_files:
    try:
        df = pd.read_csv(path)

        if "simulation_id" not in df.columns:
            print(f"Skipping {path.name}: no simulation_id column")
            continue

        if len(df) == 0:
            print(f"Skipping {path.name}: empty")
            continue

        df = df.dropna(subset=["simulation_id"]).copy()
        df["simulation_id"] = df["simulation_id"].astype(int)

        existing_dfs.append(df)
        print(f"Loaded existing result file: {path.name} | rows = {len(df)}")

    except Exception as e:
        print(f"Could not read {path}: {e}")

if existing_dfs:
    existing_results = pd.concat(existing_dfs, ignore_index=True)
    existing_results = existing_results.drop_duplicates(
        subset=["simulation_id"],
        keep="last",
    )
else:
    existing_results = pd.DataFrame(columns=["simulation_id"])

done_ids = set(existing_results["simulation_id"].astype(int).tolist())

print(f"\nAlready simulated rows found: {len(done_ids)}")
print(f"First few done ids: {sorted(done_ids)[:20]}")
print(f"Last few done ids: {sorted(done_ids)[-20:] if done_ids else []}")


# ------------------------------------------------------------
# 5. Create remaining samples
# ------------------------------------------------------------

remaining_samples = samples[~samples["simulation_id"].isin(done_ids)].copy()
remaining_samples = remaining_samples.sort_values("simulation_id")

print(f"\nRemaining simulations to run: {len(remaining_samples)}")

if "expansion_factor" in remaining_samples.columns:
    print("\nRemaining count by expansion factor:")
    print(remaining_samples["expansion_factor"].value_counts().sort_index())

if len(remaining_samples) == 0:
    print("\nNothing left to run. Merging existing results only.")
    existing_results = existing_results.sort_values("simulation_id")
    existing_results.to_csv(final_results_path, index=False)
    print(f"Merged final file saved to: {final_results_path}")
    raise SystemExit


# ------------------------------------------------------------
# 6. DO NOT DELETE OLD RESUME RESULTS
# ------------------------------------------------------------

# Important:
# We do NOT delete old resume_results_chunk_*.csv files.
# Those files contain already completed simulations.

# Optional: remove only old resume input files.
# Safe because inputs can be regenerated from remaining_samples.
for old_file in resume_samples_dir.glob("resume_samples_chunk_NEW_*.csv"):
    old_file.unlink()


# ------------------------------------------------------------
# 7. Find next free resume chunk index
# ------------------------------------------------------------

existing_resume_result_files = sorted(resume_results_dir.glob("resume_results_chunk_*.csv"))

existing_indices = []

for path in existing_resume_result_files:
    stem = path.stem  # example: resume_results_chunk_005
    try:
        idx = int(stem.split("_")[-1])
        existing_indices.append(idx)
    except ValueError:
        pass

next_chunk_index = max(existing_indices, default=0) + 1

print(f"\nNext new resume chunk index will start at: {next_chunk_index:03d}")


# ------------------------------------------------------------
# 8. Split remaining samples into NEW resume chunks
# ------------------------------------------------------------

resume_chunk_paths = []
resume_result_paths = []
resume_chunk_indices = []

n_remaining = len(remaining_samples)
n_chunks = int(np.ceil(n_remaining / resume_chunk_size))

for local_chunk_idx in range(n_chunks):
    start = local_chunk_idx * resume_chunk_size
    end = min(start + resume_chunk_size, n_remaining)

    chunk_df = remaining_samples.iloc[start:end].copy()

    global_chunk_idx = next_chunk_index + local_chunk_idx

    chunk_samples_path = resume_samples_dir / f"resume_samples_chunk_NEW_{global_chunk_idx:03d}.csv"
    chunk_results_path = resume_results_dir / f"resume_results_chunk_{global_chunk_idx:03d}.csv"

    chunk_df.to_csv(chunk_samples_path, index=False)

    resume_chunk_paths.append(chunk_samples_path)
    resume_result_paths.append(chunk_results_path)
    resume_chunk_indices.append(global_chunk_idx)

print(f"\nCreated {len(resume_chunk_paths)} NEW resume chunks:")
for idx, p in zip(resume_chunk_indices, resume_chunk_paths):
    print(f"  chunk {idx:03d}: {p.name}")


# ------------------------------------------------------------
# 9. MATLAB launcher
# ------------------------------------------------------------

def run_matlab_chunk(chunk_idx: int, chunk_samples_path: Path, chunk_results_path: Path) -> int:
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

    log_path = resume_logs_dir / f"resume_chunk_{chunk_idx:03d}.log"

    print(f"\n[PYTHON] Launching MATLAB resume chunk {chunk_idx:03d}...", flush=True)
    print("[PYTHON] " + " ".join(cmd), flush=True)
    print(f"[PYTHON] Log file: {log_path}", flush=True)

    with open(log_path, "w", encoding="utf-8") as log_file:
        completed = subprocess.run(
            cmd,
            cwd=matlab_script_dir,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            check=False,
        )

    if completed.returncode != 0:
        raise RuntimeError(
            f"MATLAB resume chunk {chunk_idx:03d} failed with return code "
            f"{completed.returncode}. Check log: {log_path}"
        )

    return chunk_idx


# ------------------------------------------------------------
# 10. Run remaining chunks, 2 MATLAB processes at a time
# ------------------------------------------------------------

print(f"\nLaunching resume run with {num_matlab_processes} MATLAB processes...")

with ThreadPoolExecutor(max_workers=num_matlab_processes) as executor:
    futures = []

    for chunk_idx, chunk_samples_path, chunk_results_path in zip(
        resume_chunk_indices,
        resume_chunk_paths,
        resume_result_paths,
    ):
        futures.append(
            executor.submit(
                run_matlab_chunk,
                chunk_idx,
                chunk_samples_path,
                chunk_results_path,
            )
        )

    for future in as_completed(futures):
        finished_idx = future.result()
        print(f"[PYTHON] MATLAB resume chunk {finished_idx:03d} finished.", flush=True)


# ------------------------------------------------------------
# 11. Merge old partial results + all resume results
# ------------------------------------------------------------

print("\nMerging existing + resumed results...")

all_result_files = []

all_result_files.extend(sorted(chunks_results_dir.glob("results_chunk_*.csv")))
all_result_files.extend(sorted(resume_results_dir.glob("resume_results_chunk_*.csv")))

all_dfs = []

for path in all_result_files:
    try:
        df = pd.read_csv(path)

        if len(df) == 0:
            print(f"Skipping {path.name}: empty")
            continue

        if "simulation_id" not in df.columns:
            print(f"Skipping {path.name}: no simulation_id")
            continue

        df = df.dropna(subset=["simulation_id"]).copy()
        df["simulation_id"] = df["simulation_id"].astype(int)

        all_dfs.append(df)
        print(f"Merging {path.name} | rows = {len(df)}")

    except Exception as e:
        print(f"Could not merge {path.name}: {e}")

if not all_dfs:
    raise RuntimeError("No valid result files found to merge.")

final_results = pd.concat(all_dfs, ignore_index=True)

final_results = final_results.drop_duplicates(
    subset=["simulation_id"],
    keep="last",
)

final_results = final_results.sort_values("simulation_id")
final_results.to_csv(final_results_path, index=False)

print(f"\nFinal resumed results saved to:")
print(final_results_path)

if "simulation_status" in final_results.columns:
    print("\nFinal simulation status counts:")
    print(final_results["simulation_status"].value_counts(dropna=False))

if "simulation_status" in final_results.columns and "expansion_factor" in final_results.columns:
    print("\nFinal failure rate by expansion factor:")
    print(
        final_results
        .assign(failed=final_results["simulation_status"].eq("failed"))
        .groupby("expansion_factor")["failed"]
        .mean()
        .mul(100)
    )

print("\nCoverage:")
print(f"Expected total samples: {len(samples)}")
print(f"Final result rows:      {len(final_results)}")
print(f"Missing rows:           {len(samples) - len(final_results)}")

missing_ids = sorted(
    set(samples["simulation_id"].astype(int))
    - set(final_results["simulation_id"].astype(int))
)

if missing_ids:
    print("\nMissing simulation_ids:")
    print(missing_ids[:100])
else:
    print("\nAll simulation_ids are covered.")