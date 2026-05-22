from pathlib import Path
import importlib.util
import numpy as np
import pandas as pd


# ============================================================
# CONFIG
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

CAMPAIGN_NAME = "conditional_sampling_100_patients_100_variations_v2"

N_VARIATIONS_PER_PATIENT = 100
RANDOM_SEED = 42
CHUNK_SIZE = 50

# Input: 100 patients that survived Round 1 + Round 2
patients_csv = (
    ROOT
    / "01_Data"
    / "Conditional_Sampling_v2"
    / "patients"
    / "conditional_sampling_100_round2_valid_patients.csv"
)

# Tunable bounds
bounds_csv = (
    ROOT
    / "01_Data"
    / "patient_configs"
    / "pediatric_dcm_patient_01"
    / "stage_1_tunable_bounds_v3_physiological.csv"
)

# Python file containing build_full_scalar_config(row)
config_builder_script = (
    ROOT
    / "08_Conditional_Sampling_v2"
    / "08C_compute_simulink_model_inputs.py"
)

output_dir = (
    ROOT
    / "01_Data"
    / "Conditional_Sampling_v2"
    / "generated_samples"
    / CAMPAIGN_NAME
)

chunks_dir = output_dir / "chunks"

results_base_dir = (
    ROOT
    / "01_Data"
    / "Conditional_Sampling_v2"
    / "simulation_results"
    / CAMPAIGN_NAME
)

results_chunks_dir = results_base_dir / "chunks"
logs_dir = results_base_dir / "logs"

output_dir.mkdir(parents=True, exist_ok=True)
chunks_dir.mkdir(parents=True, exist_ok=True)
results_chunks_dir.mkdir(parents=True, exist_ok=True)
logs_dir.mkdir(parents=True, exist_ok=True)


# ============================================================
# IMPORT CONFIG BUILDER
# ============================================================

def load_config_builder(script_path: Path):
    """
    Import build_full_scalar_config from 02_build_full_scalar_patient_configs.py
    even though the file starts with a number.
    """
    if not script_path.exists():
        raise FileNotFoundError(f"Could not find config builder script: {script_path}")

    spec = importlib.util.spec_from_file_location("config_builder_module", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "build_full_scalar_config"):
        raise AttributeError(
            f"{script_path} does not contain a function named build_full_scalar_config."
        )

    return module.build_full_scalar_config


build_full_scalar_config = load_config_builder(config_builder_script)


# ============================================================
# HELPERS
# ============================================================

def latin_hypercube(n_samples: int, n_dimensions: int, seed: int) -> np.ndarray:
    """
    Simple Latin Hypercube Sampling in [0, 1].
    """
    rng = np.random.default_rng(seed)
    lhs = np.zeros((n_samples, n_dimensions))

    for j in range(n_dimensions):
        cut_points = np.linspace(0, 1, n_samples + 1)
        points = rng.uniform(cut_points[:-1], cut_points[1:])
        rng.shuffle(points)
        lhs[:, j] = points

    return lhs


def clean_value(value):
    """
    Convert numpy/pandas values to plain Python-friendly values.
    """
    if pd.isna(value):
        return np.nan
    return value


def make_minimal_patient_row(patient: pd.Series) -> dict:
    """
    Keep only patient target variables and optional sampled physiological variables.

    Important:
    We do NOT keep old derived config variables such as Ctot, Rsysart, ESP_RV, etc.
    Those must be recomputed after each tunable variation.

    Also important:
    We do NOT keep Rsysven here, because k_Rsysven is tunable.
    If Rsysven is kept, build_full_scalar_config may reuse the old Rsysven and ignore
    the new k_Rsysven.
    """

    possible_keep_columns = [
        # IDs
        "patient_id",
        "base_patient_id",

        # patient targets
        "age",
        "weight",
        "BSA",
        "hr",
        "SAP",
        "DAP",
        "CVP",
        "LAP",
        "sPAP",
        "dPAP",
        "mPAP",
        "EDVLV",
        "ESVLV",
        "EDVRV",
        "ESVRV",
        "EDV_LV",
        "ESV_LV",
        "EDV_RV",
        "ESV_RV",

        # optional physiological inputs that are patient-level, not tunable-dependent
        "MAP",
        "CO",
        "COLV",
        "SVR",
        "PVR",
        "mcfp",
    ]

    row = {}

    for col in possible_keep_columns:
        if col in patient.index:
            row[col] = clean_value(patient[col])

    return row


def apply_final_presim_checks(df: pd.DataFrame) -> pd.Series:
    """
    Optional final check on the 10k full configs.
    This catches tunable variations that became invalid even if the base patient was valid.
    """

    valid = pd.Series(True, index=df.index)

    required_positive = [
        "SV_LV",
        "SV_RV",
        "CO",
        "SVR",
        "PVR",
        "Ctot",
        "Csys",
        "Cpulm",
        "Csysart",
        "Csysven",
        "Cpulmart",
        "Cpulmven",
        "Rsysven",
        "Rsysart",
        "Rpulmart",
        "Rpulmven",
        "Vtot",
        "Vsys",
        "Vpulm",
        "Vsv_tot",
        "Vusv_tot",
        "Vusv_sys",
        "Vusv_pulm",
        "Vusv_sys_ven",
        "Vusv_pulm_ven",
    ]

    for col in required_positive:
        if col in df.columns:
            valid &= df[col].notna()
            valid &= np.isfinite(df[col])
            valid &= df[col] > 0

    if "ESP_RV" in df.columns and "EDP_RV" in df.columns:
        valid &= df["ESP_RV"] > df["EDP_RV"]

    if "ESP_LV" in df.columns and "EDP_LV" in df.columns:
        valid &= df["ESP_LV"] > df["EDP_LV"]

    if "LASV" in df.columns and "RASV" in df.columns:
        valid &= (df["LASV"] - df["RASV"]).abs() < 1

    return valid


# ============================================================
# LOAD DATA
# ============================================================

patients = pd.read_csv(patients_csv)
bounds = pd.read_csv(bounds_csv)

print("=" * 80)
print("LOADED INPUTS")
print("=" * 80)
print(f"Patients CSV: {patients_csv}")
print(f"Patients shape: {patients.shape}")
print(f"Bounds CSV: {bounds_csv}")
print(f"Bounds shape: {bounds.shape}")

required_bound_cols = {"variable", "lower_bound", "upper_bound"}
missing_bound_cols = required_bound_cols - set(bounds.columns)

if missing_bound_cols:
    raise ValueError(f"Missing columns in bounds CSV: {missing_bound_cols}")

tunables = bounds["variable"].tolist()

print()
print("Tunables:")
for t in tunables:
    print(f"  - {t}")

if len(patients) != 100:
    print()
    print(f"WARNING: Expected 100 patients, but loaded {len(patients)} patients.")


# ============================================================
# GENERATE 100 VARIATIONS PER PATIENT
# ============================================================

rows = []
failed_rows = []

global_simulation_id = 1

for patient_idx, patient in patients.iterrows():

    if "base_patient_id" in patient.index:
        base_patient_id = int(patient["base_patient_id"])
    elif "patient_id" in patient.index:
        base_patient_id = int(patient["patient_id"])
    else:
        base_patient_id = int(patient_idx + 1)

    original_patient_id = int(patient["patient_id"]) if "patient_id" in patient.index else base_patient_id

    lhs = latin_hypercube(
        n_samples=N_VARIATIONS_PER_PATIENT,
        n_dimensions=len(tunables),
        seed=RANDOM_SEED + base_patient_id,
    )

    base_patient_row = make_minimal_patient_row(patient)

    for variation_id in range(1, N_VARIATIONS_PER_PATIENT + 1):

        variation_input = dict(base_patient_row)

        variation_input["simulation_id"] = global_simulation_id
        variation_input["patient_id"] = original_patient_id
        variation_input["base_patient_id"] = base_patient_id
        variation_input["variation_id"] = variation_id
        variation_input["campaign_name"] = CAMPAIGN_NAME
        variation_input["sampling_method"] = "round2_valid_patient_plus_lhs_tunables"
        variation_input["random_seed"] = RANDOM_SEED

        # Add sampled tunable parameters
        for j, variable in enumerate(tunables):
            bound_row = bounds.loc[bounds["variable"] == variable].iloc[0]

            lower = float(bound_row["lower_bound"])
            upper = float(bound_row["upper_bound"])

            sampled_value = lower + lhs[variation_id - 1, j] * (upper - lower)

            variation_input[variable] = sampled_value

        try:
            # Recompute full scalar config after applying tunable variation
            config = build_full_scalar_config(pd.Series(variation_input))

            # Re-add metadata that the config builder may not preserve
            config["simulation_id"] = global_simulation_id
            config["patient_id"] = original_patient_id
            config["base_patient_id"] = base_patient_id
            config["variation_id"] = variation_id
            config["campaign_name"] = CAMPAIGN_NAME
            config["sampling_method"] = "round2_valid_patient_plus_lhs_tunables"
            config["random_seed"] = RANDOM_SEED
            config["config_status"] = "success"
            config["config_error"] = ""

            rows.append(config)

        except Exception as exc:
            failed_rows.append({
                "simulation_id": global_simulation_id,
                "patient_id": original_patient_id,
                "base_patient_id": base_patient_id,
                "variation_id": variation_id,
                "campaign_name": CAMPAIGN_NAME,
                "config_status": "failed",
                "config_error": str(exc),
            })

        global_simulation_id += 1


dataset = pd.DataFrame(rows)
failed_df = pd.DataFrame(failed_rows)


# ============================================================
# FINAL PRE-SIM CHECKS ON 10K CONFIGS
# ============================================================

if len(dataset) > 0:
    dataset["final_presim_valid"] = apply_final_presim_checks(dataset)
else:
    dataset["final_presim_valid"] = []

valid_for_sim = dataset[dataset["final_presim_valid"]].copy()
invalid_for_sim = dataset[~dataset["final_presim_valid"]].copy()


# ============================================================
# SAVE FULL DATASETS
# ============================================================

full_output_path = output_dir / f"{CAMPAIGN_NAME}_FULL_CONFIG_DATASET.csv"
valid_output_path = output_dir / f"{CAMPAIGN_NAME}_VALID_FOR_SIM.csv"
invalid_output_path = output_dir / f"{CAMPAIGN_NAME}_INVALID_FOR_SIM.csv"
failed_output_path = output_dir / f"{CAMPAIGN_NAME}_FAILED_CONFIG_GENERATION.csv"

dataset.to_csv(full_output_path, index=False)
valid_for_sim.to_csv(valid_output_path, index=False)
invalid_for_sim.to_csv(invalid_output_path, index=False)

if len(failed_df) > 0:
    failed_df.to_csv(failed_output_path, index=False)


# ============================================================
# CREATE CHUNKS + MANIFEST FOR SLURM
# ============================================================

dataset_for_chunks = valid_for_sim.reset_index(drop=True)

n_chunks = int(np.ceil(len(dataset_for_chunks) / CHUNK_SIZE))
manifest_rows = []

for chunk_id in range(1, n_chunks + 1):

    start = (chunk_id - 1) * CHUNK_SIZE
    end = min(start + CHUNK_SIZE, len(dataset_for_chunks))

    chunk_df = dataset_for_chunks.iloc[start:end].copy()

    chunk_samples_path = chunks_dir / f"samples_chunk_{chunk_id:05d}.csv"
    chunk_results_path = results_chunks_dir / f"results_chunk_{chunk_id:05d}.csv"

    chunk_df.to_csv(chunk_samples_path, index=False)

    manifest_rows.append({
        "array_id": chunk_id,
        "samples_path": chunk_samples_path.as_posix(),
        "results_path": chunk_results_path.as_posix(),
        "n_cases": len(chunk_df),
    })

manifest = pd.DataFrame(manifest_rows)

manifest_path = output_dir / f"{CAMPAIGN_NAME}_manifest.csv"
manifest.to_csv(manifest_path, index=False)


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 80)
print("10K TUNABLE VARIATION CONFIG GENERATION COMPLETE")
print("=" * 80)

print(f"Base patients loaded: {len(patients)}")
print(f"Variations per patient: {N_VARIATIONS_PER_PATIENT}")
print(f"Requested total variations: {len(patients) * N_VARIATIONS_PER_PATIENT}")
print(f"Successfully generated configs: {len(dataset)}")
print(f"Failed config generations: {len(failed_df)}")

print()
print(f"Valid for simulation: {len(valid_for_sim)}")
print(f"Invalid before simulation: {len(invalid_for_sim)}")

print()
print(f"Number of chunks: {n_chunks}")
print(f"Chunk size: {CHUNK_SIZE}")

print()
print("Full config dataset:")
print(full_output_path)

print()
print("Valid-for-sim dataset:")
print(valid_output_path)

print()
print("Invalid-for-sim dataset:")
print(invalid_output_path)

if len(failed_df) > 0:
    print()
    print("Failed config generation dataset:")
    print(failed_output_path)

print()
print("Manifest:")
print(manifest_path)

print()
print("Results directory:")
print(results_base_dir)

print()
print("Use this in SLURM:")
print(f"#SBATCH --array=1-{n_chunks}%20")

print("=" * 80)