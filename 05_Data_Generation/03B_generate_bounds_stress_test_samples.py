import json
from pathlib import Path

import pandas as pd
from scipy.stats import qmc


patient_id = "pediatric_dcm_patient_01"
random_seed = 42

# Number of samples per expansion level
n_samples_per_factor = 30

# Expansion factors to test
expansion_factors = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]

data_dir = Path("../01_Data")

config_path = (
    data_dir
    / "patient_configs"
    / patient_id
    / f"{patient_id}_config.json"
)

output_dir = data_dir / "generated_samples" / patient_id / "bounds_stress_test"
output_dir.mkdir(parents=True, exist_ok=True)

samples_path = output_dir / f"{patient_id}_bounds_stress_test_samples.csv"
bounds_path = output_dir / f"{patient_id}_bounds_stress_test_bounds_by_factor.csv"
metadata_path = output_dir / f"{patient_id}_bounds_stress_test_metadata.json"


with open(config_path, "r") as f:
    patient_config = json.load(f)

bounds_df = pd.DataFrame(patient_config["stage_1_tunables"])

required_cols = ["variable", "baseline", "lower_bound", "upper_bound"]

missing = [c for c in required_cols if c not in bounds_df.columns]
if missing:
    raise ValueError(f"Missing columns in bounds table: {missing}")

for col in ["baseline", "lower_bound", "upper_bound"]:
    bounds_df[col] = pd.to_numeric(bounds_df[col], errors="coerce")

if bounds_df[["baseline", "lower_bound", "upper_bound"]].isna().any().any():
    raise ValueError("Some bounds are missing or non-numeric.")

variables = bounds_df["variable"].tolist()

all_samples = []
all_bounds = []

simulation_id = 0

for factor_index, factor in enumerate(expansion_factors):
    factor_bounds = bounds_df.copy()
    factor_bounds["expansion_factor"] = factor

    factor_bounds["expanded_lower_bound"] = (
        factor_bounds["baseline"]
        - factor * (factor_bounds["baseline"] - factor_bounds["lower_bound"])
    )

    factor_bounds["expanded_upper_bound"] = (
        factor_bounds["baseline"]
        + factor * (factor_bounds["upper_bound"] - factor_bounds["baseline"])
    )

    # Optional safety clipping for fraction-like variables
    fraction_vars = [
        "k_Vsys",
        "k_Vusv_sys",
        "k_Vusv_sys_ven",
        "k_Vusv_pulm_ven",
        "k_Csys",
        "k_Rpulmart",
        "k_ESP_LV",
        "k_ESP_RV",
    ]

    mask_fraction = factor_bounds["variable"].isin(fraction_vars)
    factor_bounds.loc[mask_fraction, "expanded_lower_bound"] = (
        factor_bounds.loc[mask_fraction, "expanded_lower_bound"].clip(lower=0.01)
    )

    # Some coefficients can reasonably go above 1, like ESP factors.
    # For pure fraction variables, cap at 0.999.
    pure_fraction_vars = [
        "k_Vsys",
        "k_Vusv_sys",
        "k_Vusv_sys_ven",
        "k_Vusv_pulm_ven",
        "k_Csys",
        "k_Rpulmart",
    ]

    mask_pure_fraction = factor_bounds["variable"].isin(pure_fraction_vars)
    factor_bounds.loc[mask_pure_fraction, "expanded_upper_bound"] = (
        factor_bounds.loc[mask_pure_fraction, "expanded_upper_bound"].clip(upper=0.999)
    )

    all_bounds.append(factor_bounds)

    lower = factor_bounds["expanded_lower_bound"].to_numpy()
    upper = factor_bounds["expanded_upper_bound"].to_numpy()

    sampler = qmc.LatinHypercube(
        d=len(variables),
        seed=random_seed + factor_index,
    )

    unit_samples = sampler.random(n=n_samples_per_factor)
    scaled_samples = qmc.scale(unit_samples, lower, upper)

    samples_df = pd.DataFrame(scaled_samples, columns=variables)
    samples_df.insert(0, "expansion_factor", factor)

    ids = list(range(simulation_id, simulation_id + n_samples_per_factor))
    samples_df.insert(0, "simulation_id", ids)

    simulation_id += n_samples_per_factor

    all_samples.append(samples_df)


all_samples_df = pd.concat(all_samples, ignore_index=True)
all_bounds_df = pd.concat(all_bounds, ignore_index=True)

all_samples_df.to_csv(samples_path, index=False)
all_bounds_df.to_csv(bounds_path, index=False)

metadata = {
    "patient_id": patient_id,
    "scenario": patient_config["scenario"],
    "n_samples_per_factor": n_samples_per_factor,
    "expansion_factors": expansion_factors,
    "total_samples": len(all_samples_df),
    "sampling_method": "Latin Hypercube Sampling per expansion factor",
    "variables": variables,
    "samples_file": str(samples_path),
    "bounds_file": str(bounds_path),
}

with open(metadata_path, "w") as f:
    json.dump(metadata, f, indent=4)

print("Saved stress-test samples to:", samples_path)
print("Saved expanded bounds to:", bounds_path)
print("Saved metadata to:", metadata_path)
print("Total samples:", len(all_samples_df))
print(all_samples_df.head())