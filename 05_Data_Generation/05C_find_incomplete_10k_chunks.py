from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

PATIENT_ID = "pediatric_dcm_patient_01"
CAMPAIGN_NAME = "stage_1_10k_supercomputer_v2"

manifest_path = (
    ROOT
    / "01_Data"
    / "generated_samples"
    / PATIENT_ID
    / CAMPAIGN_NAME
    / f"{PATIENT_ID}_{CAMPAIGN_NAME}_manifest.csv"
)

manifest = pd.read_csv(manifest_path)

incomplete = []

for _, row in manifest.iterrows():
    array_id = int(row["array_id"])
    result_path = Path(row["results_path"])
    expected_n = int(row["n_cases"])

    if not result_path.exists():
        incomplete.append(array_id)
        continue

    try:
        result_df = pd.read_csv(result_path)
        n_rows = len(result_df)

        if n_rows < expected_n:
            incomplete.append(array_id)

    except Exception:
        incomplete.append(array_id)

out_path = (
    ROOT
    / "01_Data"
    / "simulation_results"
    / PATIENT_ID
    / CAMPAIGN_NAME
    / "incomplete_chunks.txt"
)

out_path.parent.mkdir(parents=True, exist_ok=True)

with open(out_path, "w") as f:
    for chunk_id in incomplete:
        f.write(f"{chunk_id}\n")

print(f"Incomplete chunks: {len(incomplete)}")
print(f"Saved to: {out_path}")

if incomplete:
    print("First incomplete chunks:")
    print(incomplete[:50])
