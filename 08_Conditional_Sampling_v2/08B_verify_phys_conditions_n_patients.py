from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# Paths
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

input_path = (
    ROOT
    / "01_Data"
    / "Conditional_Sampling_v2"
    / "patients"
    / "conditional_sampling_1000_patients.csv"
)

output_path = (
    ROOT
    / "01_Data"
    / "Conditional_Sampling_v2"
    / "patients"
    / "conditional_sampling_300_round1_valid_patients.csv"
)

invalid_output_path = (
    ROOT
    / "01_Data"
    / "Conditional_Sampling_v2"
    / "patients"
    / "conditional_sampling_round1_invalid_patients.csv"
)


# ============================================================
# Helpers
# ============================================================

def get_col(df: pd.DataFrame, possible_names: list[str]) -> pd.Series:
    """
    Return a dataframe column using any accepted column name.
    """
    for name in possible_names:
        if name in df.columns:
            return df[name]

    raise KeyError(
        f"Missing required column. Tried: {possible_names}. "
        f"Available columns are: {list(df.columns)}"
    )


def has_col(df: pd.DataFrame, possible_names: list[str]) -> bool:
    return any(name in df.columns for name in possible_names)


# ============================================================
# Load 500-patient dataset
# ============================================================

patients = pd.read_csv(input_path)

print(f"Loaded dataset:")
print(input_path)
print(f"Initial shape: {patients.shape}")


# ============================================================
# Read required columns
# ============================================================

EDVLV = get_col(patients, ["EDVLV", "EDV_LV"])
ESVLV = get_col(patients, ["ESVLV", "ESV_LV"])

EDVRV = get_col(patients, ["EDVRV", "EDV_RV"])
ESVRV = get_col(patients, ["ESVRV", "ESV_RV"])

LAP = get_col(patients, ["LAP"])
mPAP = get_col(patients, ["mPAP"])

SAP = get_col(patients, ["SAP"])
DAP = get_col(patients, ["DAP"])

CVP = get_col(patients, ["CVP"])

sPAP = get_col(patients, ["sPAP"])
dPAP = get_col(patients, ["dPAP", "dPAPA"])  # accepts typo too

Rsysven = get_col(patients, ["Rsysven", "Rsysven_real"])

# ============================================================
# Compute LVSV / RVSV if not already present
# ============================================================

if has_col(patients, ["LVSV", "SV_LV"]):
    LVSV = get_col(patients, ["LVSV", "SV_LV"])
else:
    LVSV = EDVLV - ESVLV
    patients["LVSV"] = LVSV

if has_col(patients, ["RVSV", "SV_RV"]):
    RVSV = get_col(patients, ["RVSV", "SV_RV"])
else:
    RVSV = EDVRV - ESVRV
    patients["RVSV"] = RVSV


# ============================================================
# Round 1 physiological conditions
# ============================================================

cond_equal_stroke_volume = (LVSV - RVSV).abs() < 1
cond_lap_below_mpap = LAP < mPAP
cond_sap_above_cvp = SAP > CVP
cond_systemic_pulse_pressure = (SAP - DAP).abs() > 30
cond_pulmonary_pulse_pressure = (sPAP - dPAP).abs() > 15
cond_rv_volume_order = EDVRV > ESVRV
cond_lv_volume_order = EDVLV > ESVLV
cond_rsysven_positive = Rsysven > 0

round1_valid = (
    cond_equal_stroke_volume
    & cond_lap_below_mpap
    & cond_sap_above_cvp
    & cond_systemic_pulse_pressure
    & cond_pulmonary_pulse_pressure
    & cond_rv_volume_order
    & cond_lv_volume_order
    & cond_rsysven_positive
)


# ============================================================
# Add diagnostic columns
# ============================================================

patients["round1_valid"] = round1_valid

patients["round1_cond_equal_stroke_volume"] = cond_equal_stroke_volume
patients["round1_cond_lap_below_mpap"] = cond_lap_below_mpap
patients["round1_cond_sap_above_cvp"] = cond_sap_above_cvp
patients["round1_cond_systemic_pulse_pressure"] = cond_systemic_pulse_pressure
patients["round1_cond_pulmonary_pulse_pressure"] = cond_pulmonary_pulse_pressure
patients["round1_cond_rv_volume_order"] = cond_rv_volume_order
patients["round1_cond_lv_volume_order"] = cond_lv_volume_order
patients["round1_cond_rsysven_positive"] = cond_rsysven_positive

# ============================================================
# Split valid / invalid
# ============================================================

valid_patients = patients[round1_valid].copy()
invalid_patients = patients[~round1_valid].copy()

print()
print(f"Patients passing Round 1: {len(valid_patients)} / {len(patients)}")
print(f"Patients failing Round 1: {len(invalid_patients)} / {len(patients)}")

print()
print("Condition pass counts:")
print(f"abs(LVSV - RVSV) < 1 ml:      {cond_equal_stroke_volume.sum()} / {len(patients)}")
print(f"LAP < mPAP:                   {cond_lap_below_mpap.sum()} / {len(patients)}")
print(f"SAP > CVP:                    {cond_sap_above_cvp.sum()} / {len(patients)}")
print(f"abs(SAP - DAP) > 30 mmHg:     {cond_systemic_pulse_pressure.sum()} / {len(patients)}")
print(f"abs(sPAP - dPAP) > 15 mmHg:   {cond_pulmonary_pulse_pressure.sum()} / {len(patients)}")
print(f"EDVRV > ESVRV:                {cond_rv_volume_order.sum()} / {len(patients)}")
print(f"EDVLV > ESVLV:                {cond_lv_volume_order.sum()} / {len(patients)}")
print(f"Rsysven > 0:                    {cond_rsysven_positive.sum()} / {len(patients)}")


# ============================================================
# Select exactly 300 valid patients
# ============================================================

n_target = 300

if len(valid_patients) < n_target:
    raise ValueError(
        f"Only {len(valid_patients)} patients passed Round 1, "
        f"but you requested {n_target}."
    )

selected_patients = valid_patients.sample(
    n=n_target,
    random_state=42
).reset_index(drop=True)


# ============================================================
# Save outputs
# ============================================================

output_path.parent.mkdir(parents=True, exist_ok=True)

selected_patients.to_csv(output_path, index=False)
invalid_patients.to_csv(invalid_output_path, index=False)

print()
print(f"Saved selected 300 Round 1 valid patients to:")
print(output_path)

print()
print(f"Saved Round 1 invalid patients to:")
print(invalid_output_path)

print()
print(f"Final selected shape: {selected_patients.shape}")