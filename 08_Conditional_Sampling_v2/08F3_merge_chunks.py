from pathlib import Path
import re
import pandas as pd


# ============================================================
# CONFIG
# ============================================================

CAMPAIGN_NAME = "conditional_sampling_100_patients_100_variations_v2"
EXPECTED_CHUNKS = 198

ROOT = Path(__file__).resolve().parents[1]

RESULTS_DIR = (
    ROOT
    / "01_Data"
    / "Conditional_Sampling_v2"
    / "simulation_results"
    / CAMPAIGN_NAME
)

CHUNKS_DIR = RESULTS_DIR / "chunks"

OUTPUT_PATH = RESULTS_DIR / f"{CAMPAIGN_NAME}_MERGED_RESULTS.csv"

INCOMPLETE_OUTPUT_PATH = RESULTS_DIR / f"{CAMPAIGN_NAME}_MERGED_RESULTS_INCOMPLETE.csv"


# ============================================================
# FIND CHUNKS
# ============================================================

if not CHUNKS_DIR.exists():
    raise FileNotFoundError(f"Chunks directory does not exist:\n{CHUNKS_DIR}")

chunk_files = sorted(
    CHUNKS_DIR.glob("results_chunk_*.csv"),
    key=lambda p: int(re.search(r"results_chunk_(\d+)\.csv", p.name).group(1))
)

if len(chunk_files) == 0:
    raise FileNotFoundError(f"No result chunk files found in:\n{CHUNKS_DIR}")

existing_chunks = set()

for p in chunk_files:
    match = re.search(r"results_chunk_(\d+)\.csv", p.name)
    if match:
        existing_chunks.add(int(match.group(1)))

expected_chunks = set(range(1, EXPECTED_CHUNKS + 1))
missing_chunks = sorted(expected_chunks - existing_chunks)

print("=" * 80)
print(f"Campaign: {CAMPAIGN_NAME}")
print(f"Chunks directory: {CHUNKS_DIR}")
print(f"Found chunk files: {len(chunk_files)}")
print(f"Expected chunks:   {EXPECTED_CHUNKS}")
print(f"Missing chunks:    {missing_chunks}")
print("=" * 80)

if missing_chunks:
    print()
    print("WARNING: Some chunks are missing.")
    print("The script will NOT write the final complete output.")
    print("It will write an incomplete merged file instead.")
    print()


# ============================================================
# LOAD CHUNKS
# ============================================================

all_dfs = []
bad_files = []
empty_files = []
short_files = []
column_mismatch_files = []

reference_columns = None

for i, chunk_path in enumerate(chunk_files, start=1):

    print(f"[{i}/{len(chunk_files)}] Loading: {chunk_path.name}")

    try:
        df = pd.read_csv(chunk_path)

        n_rows = len(df)
        n_cols = len(df.columns)

        print(f"    Rows: {n_rows} | Columns: {n_cols}")

        if df.empty:
            empty_files.append(chunk_path.name)
            continue

        # Useful warning: most chunks should have 50 rows.
        # Last chunk may have fewer because 9882 is not divisible by 50.
        chunk_match = re.search(r"results_chunk_(\d+)\.csv", chunk_path.name)
        chunk_id = int(chunk_match.group(1)) if chunk_match else None

        if chunk_id != EXPECTED_CHUNKS and n_rows != 50:
            short_files.append((chunk_path.name, n_rows))

        if reference_columns is None:
            reference_columns = list(df.columns)
        elif list(df.columns) != reference_columns:
            column_mismatch_files.append(chunk_path.name)

        all_dfs.append(df)

    except Exception as e:
        print(f"    ERROR reading {chunk_path.name}")
        print(f"    {e}")
        bad_files.append((chunk_path.name, str(e)))


# ============================================================
# VALIDATE CHUNKS
# ============================================================

if bad_files:
    raise RuntimeError(f"Some chunk files could not be read:\n{bad_files}")

if empty_files:
    raise RuntimeError(f"Some chunk files are empty:\n{empty_files}")

if column_mismatch_files:
    raise RuntimeError(
        "Some chunk files do not have the same columns. "
        f"First mismatches:\n{column_mismatch_files[:20]}"
    )

if short_files:
    print()
    print("WARNING: Some non-final chunks have fewer than 50 rows:")
    for name, n_rows in short_files[:20]:
        print(f"  {name}: {n_rows} rows")
    if len(short_files) > 20:
        print(f"  ... and {len(short_files) - 20} more")


# ============================================================
# MERGE
# ============================================================

print()
print("Merging chunks...")

merged_df = pd.concat(all_dfs, ignore_index=True)

print(f"Raw merged shape: {merged_df.shape}")


# ============================================================
# CLEAN / SORT / DEDUPLICATE
# ============================================================

before_duplicates = len(merged_df)

if "simulation_id" in merged_df.columns:
    merged_df = (
        merged_df
        .sort_values(by="simulation_id")
        .drop_duplicates(subset="simulation_id", keep="first")
        .reset_index(drop=True)
    )

after_duplicates = len(merged_df)
duplicates_removed = before_duplicates - after_duplicates


# ============================================================
# SUMMARY CHECKS
# ============================================================

expected_rows_from_chunks = None

# If all chunks exist, compute expected rows from actual files.
# In your case: 197 chunks of 50 + final chunk of 32 = 9882.
if "simulation_id" in merged_df.columns:
    n_unique_sim_ids = merged_df["simulation_id"].nunique()
else:
    n_unique_sim_ids = None

status_counts = None

if "simulation_status" in merged_df.columns:
    status_counts = merged_df["simulation_status"].value_counts(dropna=False)
elif "status" in merged_df.columns:
    status_counts = merged_df["status"].value_counts(dropna=False)


# ============================================================
# SAVE
# ============================================================

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

if missing_chunks:
    save_path = INCOMPLETE_OUTPUT_PATH
else:
    save_path = OUTPUT_PATH

merged_df.to_csv(save_path, index=False)


# ============================================================
# PRINT FINAL SUMMARY
# ============================================================

print()
print("=" * 80)
print("MERGE COMPLETE")
print("=" * 80)

print(f"Found chunks:          {len(chunk_files)} / {EXPECTED_CHUNKS}")
print(f"Missing chunks:        {missing_chunks}")
print(f"Final dataset shape:   {merged_df.shape}")
print(f"Duplicates removed:    {duplicates_removed}")

if n_unique_sim_ids is not None:
    print(f"Unique simulation_id:  {n_unique_sim_ids}")

if status_counts is not None:
    print()
    print("Simulation status counts:")
    print(status_counts)
else:
    print()
    print("No simulation_status/status column found.")

if "simulation_status" in merged_df.columns:
    n_failed = (merged_df["simulation_status"] != "success").sum()
    print()
    print(f"Non-success simulations: {n_failed}")

print()
print(f"Saved merged dataset to:\n{save_path}")

if missing_chunks:
    print()
    print("WARNING: This is an incomplete merge because chunks are missing.")
    print("Final complete output was not overwritten.")

print("=" * 80)