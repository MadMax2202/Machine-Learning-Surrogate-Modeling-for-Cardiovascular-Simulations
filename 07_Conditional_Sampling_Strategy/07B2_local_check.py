from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

csv_path = (
    ROOT
    / "01_Data"
    / "Conditional_Sampling"
    / "generated_samples"
    / "conditional_sampling_100_patients_100_variations_v1"
    / "conditional_sampling_100_patients_100_variations_v1_FULL_INPUT_DATASET.csv"
)

print("Looking for:")
print(csv_path)

if not csv_path.exists():
    raise FileNotFoundError(f"File not found: {csv_path}")

df = pd.read_csv(csv_path)

print("Shape:", df.shape)
print("Unique patients:", df["patient_id"].nunique())
print("Rows per patient:")
print(df.groupby("patient_id").size().head())

print(df.head())