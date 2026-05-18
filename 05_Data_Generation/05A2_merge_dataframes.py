from pathlib import Path
import pandas as pd

# ------------------------------------------------------------
# 1. Paths
# ------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

results_dir = (
    ROOT
    / "01_Data"
    / "simulation_results"
    / "pediatric_dcm_patient_01"
    / "expansion_stress_test_1000"
)

chunks_dir = results_dir / "chunks"
resume_chunks_dir = results_dir / "resume_chunks"

# Output file
merged_output_path = results_dir / "merged_all_results.csv"

# ------------------------------------------------------------
# 2. Collect all CSV files
# ------------------------------------------------------------

csv_files = []

# Add chunk CSVs
csv_files.extend(chunks_dir.glob("*.csv"))

# Add resume chunk CSVs
csv_files.extend(resume_chunks_dir.glob("*.csv"))

print(f"Found {len(csv_files)} CSV files.")

# ------------------------------------------------------------
# 3. Read and merge
# ------------------------------------------------------------

dfs = []

for file in csv_files:
    try:
        df = pd.read_csv(file)
        df["source_file"] = file.name  # optional, useful for debugging
        dfs.append(df)

        print(f"Loaded: {file.name} | shape = {df.shape}")

    except Exception as e:
        print(f"Failed to read {file.name}: {e}")

# Merge all dataframes
merged_df = pd.concat(dfs, ignore_index=True)

# ------------------------------------------------------------
# 4. Optional cleanup
# ------------------------------------------------------------

# Remove duplicate simulation IDs if they exist
if "simulation_id" in merged_df.columns:
    before = len(merged_df)

    merged_df = merged_df.drop_duplicates(
        subset="simulation_id",
        keep="last"
    )

    after = len(merged_df)

    print(f"Removed {before - after} duplicate simulations.")

# Sort by simulation ID
if "simulation_id" in merged_df.columns:
    merged_df = merged_df.sort_values("simulation_id")

# ------------------------------------------------------------
# 5. Save merged CSV
# ------------------------------------------------------------

merged_df.to_csv(merged_output_path, index=False)

print("\n--------------------------------------------------")
print("MERGE COMPLETE")
print("--------------------------------------------------")
print(f"Final shape: {merged_df.shape}")
print(f"Saved to:\n{merged_output_path}")