"""
03A_100_case_pilot_sample.py

Generate a pilot sample of 100 tunable-parameter combinations for the
pediatric DCM no-VAD linear scenario.

Input:
    ../01_Data/patient_configs/pediatric_dcm_patient_01/pediatric_dcm_patient_01_config.json

Output:
    ../01_Data/generated_samples/pediatric_dcm_patient_01/pediatric_dcm_patient_01_stage_1_samples_pilot_100.csv
    ../01_Data/generated_samples/pediatric_dcm_patient_01/pediatric_dcm_patient_01_stage_1_samples_pilot_100_metadata.json
"""

import json
from pathlib import Path

import pandas as pd
from scipy.stats import qmc


# ------------------------------------------------------------
# 1. Paths and settings
# ------------------------------------------------------------

patient_id = "pediatric_dcm_patient_01"

n_samples = 100
random_seed = 42

data_dir = Path("../01_Data")

config_path = (
    data_dir
    / "patient_configs"
    / patient_id
    / f"{patient_id}_config.json"
)

output_dir = data_dir / "generated_samples" / patient_id
output_dir.mkdir(parents=True, exist_ok=True)

samples_path = output_dir / f"{patient_id}_stage_1_samples_pilot_100.csv"
metadata_path = output_dir / f"{patient_id}_stage_1_samples_pilot_100_metadata.json"


# ------------------------------------------------------------
# 2. Load patient-specific config
# ------------------------------------------------------------

with open(config_path, "r") as f:
    patient_config = json.load(f)

stage_1_bounds = pd.DataFrame(patient_config["stage_1_tunables"])

print("Loaded patient config:")
print("Patient ID:", patient_config["patient_id"])
print("Scenario:", patient_config["scenario"])
print("\nStage 1 tunables:")
print(stage_1_bounds)


# ------------------------------------------------------------
# 3. Validate bounds
# ------------------------------------------------------------

required_cols = ["variable", "baseline", "lower_bound", "upper_bound"]

missing_cols = [
    col for col in required_cols
    if col not in stage_1_bounds.columns
]

if missing_cols:
    raise ValueError(f"Missing required columns in bounds table: {missing_cols}")

for col in ["baseline", "lower_bound", "upper_bound"]:
    stage_1_bounds[col] = pd.to_numeric(stage_1_bounds[col], errors="coerce")

if stage_1_bounds[["baseline", "lower_bound", "upper_bound"]].isna().any().any():
    bad_rows = stage_1_bounds[
        stage_1_bounds[["baseline", "lower_bound", "upper_bound"]]
        .isna()
        .any(axis=1)
    ]
    print(bad_rows)
    raise ValueError("Some bounds are missing or non-numeric.")

invalid_bounds = stage_1_bounds[
    stage_1_bounds["lower_bound"] >= stage_1_bounds["upper_bound"]
]

if len(invalid_bounds) > 0:
    print(invalid_bounds)
    raise ValueError("Some lower bounds are greater than or equal to upper bounds.")

print("\nBounds validated successfully.")


# ------------------------------------------------------------
# 4. Generate Latin Hypercube samples
# ------------------------------------------------------------

variables = stage_1_bounds["variable"].tolist()
lower_bounds = stage_1_bounds["lower_bound"].to_numpy()
upper_bounds = stage_1_bounds["upper_bound"].to_numpy()

n_dimensions = len(variables)

sampler = qmc.LatinHypercube(
    d=n_dimensions,
    seed=random_seed
)

sample_unit = sampler.random(n=n_samples)

sample_scaled = qmc.scale(
    sample_unit,
    lower_bounds,
    upper_bounds
)

samples_df = pd.DataFrame(sample_scaled, columns=variables)

samples_df.insert(0, "simulation_id", range(1, n_samples + 1))


# ------------------------------------------------------------
# 5. Add baseline row
# ------------------------------------------------------------

baseline_values = stage_1_bounds.set_index("variable")["baseline"].to_dict()

baseline_row = {"simulation_id": 0}

for var in variables:
    baseline_row[var] = baseline_values[var]

baseline_df = pd.DataFrame([baseline_row])

samples_with_baseline_df = pd.concat(
    [baseline_df, samples_df],
    ignore_index=True
)

print("\nGenerated samples:")
print(samples_with_baseline_df.head())


# ------------------------------------------------------------
# 6. Validate generated samples
# ------------------------------------------------------------

for _, row in stage_1_bounds.iterrows():
    var = row["variable"]
    low = row["lower_bound"]
    high = row["upper_bound"]

    values = samples_with_baseline_df[var]

    if values.min() < low or values.max() > high:
        raise ValueError(f"{var} has values outside bounds.")

print("\nAll generated samples are within bounds.")

print("\nSample summary:")
print(samples_with_baseline_df.describe().T)


# ------------------------------------------------------------
# 7. Save samples
# ------------------------------------------------------------

samples_with_baseline_df.to_csv(samples_path, index=False)

metadata = {
    "patient_id": patient_id,
    "scenario": patient_config["scenario"],
    "n_samples_requested": n_samples,
    "n_rows_saved": len(samples_with_baseline_df),
    "sampling_method": "Latin Hypercube Sampling",
    "random_seed": random_seed,
    "includes_baseline_row": True,
    "baseline_simulation_id": 0,
    "variables": variables,
    "samples_file": str(samples_path),
}

with open(metadata_path, "w") as f:
    json.dump(metadata, f, indent=4)

print("\nSaved pilot samples to:")
print(samples_path)

print("\nSaved metadata to:")
print(metadata_path)

print("\nDone.")