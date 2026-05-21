from pathlib import Path
import re
import pandas as pd

# ============================================================
# CONFIG
# ============================================================

CAMPAIGN_NAME = "conditional_sampling_100_patients_100_variations_v1"
EXPECTED_CHUNKS = 200

ROOT = Path(__file__).resolve().parents[1]

RESULTS_DIR = (
    ROOT
    / "01_Data"
    / "Conditional_Sampling"
    / "simulation_results"
    / CAMPAIGN_NAME
)

CHUNKS_DIR = RESULTS_DIR / "chunks"

OUTPUT_PATH = (
    RESULTS_DIR
    / f"{CAMPAIGN_NAME}_FULL_DATASET.csv"
)

# ============================================================
# FIND CHUNKS
# ============================================================

chunk_files = sorted(
    CHUNKS_DIR.glob("results_chunk_*.csv"),
    key=lambda p: int(re.search(r"results_chunk_(\d+)\.csv", p.name).group(1))
)

if len(chunk_files) == 0:
    raise FileNotFoundError(
        f"No chunk files found in:\n{CHUNKS_DIR}"
    )

existing_chunks = set()

for p in chunk_files:
    match = re.search(r"results_chunk_(\d+)\.csv", p.name)
    if match:
        existing_chunks.add(int(match.group(1)))

expected_chunks = set(range(1, EXPECTED_CHUNKS + 1))
missing_chunks = sorted(expected_chunks - existing_chunks)

print("=" * 60)
print(f"Campaign: {CAMPAIGN_NAME}")
print(f"Chunks directory: {CHUNKS_DIR}")
print(f"Found {len(chunk_files)} chunk files.")
print(f"Expected {EXPECTED_CHUNKS} chunk files.")
print(f"Missing chunks: {missing_chunks}")
print("=" * 60)

if missing_chunks:
    raise RuntimeError(
        f"Missing chunk files: {missing_chunks}\n"
        "Do not merge yet unless you intentionally want an incomplete dataset."
    )

# ============================================================
# LOAD CHUNKS
# ============================================================

all_dfs = []
bad_files = []
empty_files = []

reference_columns = None
column_mismatch_files = []

for i, chunk_path in enumerate(chunk_files, start=1):

    print(f"[{i}/{len(chunk_files)}] Loading: {chunk_path.name}")

    try:
        df = pd.read_csv(chunk_path)

        print(f"    Rows: {len(df)} | Columns: {len(df.columns)}")

        if df.empty:
            empty_files.append(chunk_path.name)

        if reference_columns is None:
            reference_columns = list(df.columns)
        elif list(df.columns) != reference_columns:
            column_mismatch_files.append(chunk_path.name)

        all_dfs.append(df)

    except Exception as e:
        print(f"    ERROR reading {chunk_path.name}")
        print(f"    {e}")
        bad_files.append((chunk_path.name, str(e)))

if bad_files:
    raise RuntimeError(f"Some chunk files could not be read: {bad_files}")

if empty_files:
    raise RuntimeError(f"Some chunk files are empty: {empty_files}")

if column_mismatch_files:
    raise RuntimeError(
        f"Some chunk files do not have the same columns: {column_mismatch_files[:20]}"
    )

# ============================================================
# MERGE
# ============================================================

print("\nMerging all chunks...")

merged_df = pd.concat(all_dfs, ignore_index=True)

# ============================================================
# CLEAN / SORT
# ============================================================

before_duplicates = len(merged_df)

if "simulation_id" in merged_df.columns:

    merged_df = merged_df.sort_values(
        by="simulation_id"
    ).reset_index(drop=True)

    merged_df = merged_df.drop_duplicates(
        subset="simulation_id",
        keep="first"
    ).reset_index(drop=True)

after_duplicates = len(merged_df)
duplicates_removed = before_duplicates - after_duplicates

# ============================================================
# SAVE
# ============================================================

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

merged_df.to_csv(OUTPUT_PATH, index=False)

# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 60)
print("MERGE COMPLETE")
print("=" * 60)

print(f"Final dataset shape: {merged_df.shape}")
print(f"Duplicates removed: {duplicates_removed}")

if "simulation_status" in merged_df.columns:

    status_counts = merged_df["simulation_status"].value_counts(dropna=False)

    print("\nSimulation status counts:")
    print(status_counts)

elif "status" in merged_df.columns:

    status_counts = merged_df["status"].value_counts(dropna=False)

    print("\nStatus counts:")
    print(status_counts)

else:
    print("\nNo simulation_status/status column found.")

print(f"\nSaved merged dataset to:\n{OUTPUT_PATH}")
print("=" * 60)