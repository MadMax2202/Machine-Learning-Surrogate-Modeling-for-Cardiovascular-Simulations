from pathlib import Path
import pandas as pd

# ============================================================
# CONFIG
# ============================================================

PATIENT_ID = "pediatric_dcm_patient_01"
CAMPAIGN_NAME = "stage_1_10k_supercomputer_v2"

ROOT = Path(__file__).resolve().parents[1]

CHUNKS_DIR = (
    ROOT
    / "01_Data"
    / "simulation_results"
    / PATIENT_ID
    / CAMPAIGN_NAME
    / "chunks"
)

OUTPUT_PATH = (
    ROOT
    / "01_Data"
    / "simulation_results"
    / PATIENT_ID
    / CAMPAIGN_NAME
    / f"{PATIENT_ID}_{CAMPAIGN_NAME}_FULL_DATASET.csv"
)

# ============================================================
# LOAD CHUNKS
# ============================================================

chunk_files = sorted(CHUNKS_DIR.glob("results_chunk_*.csv"))

if len(chunk_files) == 0:
    raise FileNotFoundError(
        f"No chunk files found in:\n{CHUNKS_DIR}"
    )

print("=" * 60)
print(f"Found {len(chunk_files)} chunk files.")
print("=" * 60)

all_dfs = []

for i, chunk_path in enumerate(chunk_files, start=1):

    print(f"[{i}/{len(chunk_files)}] Loading: {chunk_path.name}")

    try:
        df = pd.read_csv(chunk_path)

        print(f"    Rows: {len(df)}")

        all_dfs.append(df)

    except Exception as e:
        print(f"    ERROR reading {chunk_path.name}")
        print(f"    {e}")

# ============================================================
# MERGE
# ============================================================

print("\nMerging all chunks...")

merged_df = pd.concat(all_dfs, ignore_index=True)

# ============================================================
# CLEAN / SORT
# ============================================================

if "simulation_id" in merged_df.columns:

    merged_df = merged_df.sort_values(
        by="simulation_id"
    ).reset_index(drop=True)

    merged_df = merged_df.drop_duplicates(
        subset="simulation_id",
        keep="first"
    )

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

if "simulation_status" in merged_df.columns:

    success_count = (
        merged_df["simulation_status"] == "success"
    ).sum()

    failed_count = (
        merged_df["simulation_status"] == "failed"
    ).sum()

    print(f"Successful simulations: {success_count}")
    print(f"Failed simulations: {failed_count}")

print(f"\nSaved merged dataset to:\n{OUTPUT_PATH}")
print("=" * 60)
