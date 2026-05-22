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
    / "configs"
    / "conditional_sampling_300_full_scalar_configs_before_sim.csv"
)

output_path = (
    ROOT
    / "01_Data"
    / "Conditional_Sampling_v2"
    / "patients"
    / "conditional_sampling_100_round2_valid_patients.csv"
)

valid_configs_output_path = (
    ROOT
    / "01_Data"
    / "Conditional_Sampling_v2"
    / "configs"
    / "conditional_sampling_round2_valid_full_configs.csv"
)

invalid_output_path = (
    ROOT
    / "01_Data"
    / "Conditional_Sampling_v2"
    / "configs"
    / "conditional_sampling_round2_invalid_full_configs.csv"
)


# ============================================================
# Helpers
# ============================================================

def get_col(df: pd.DataFrame, possible_names: list[str]) -> pd.Series:
    for name in possible_names:
        if name in df.columns:
            return df[name]

    raise KeyError(
        f"Missing required column. Tried: {possible_names}. "
        f"Available columns are: {list(df.columns)}"
    )


def safe_ratio(a: pd.Series, b: pd.Series) -> pd.Series:
    return a / b.replace(0, np.nan)


# ============================================================
# Load full config CSV
# ============================================================

df = pd.read_csv(input_path)

print("Loaded full scalar config dataset:")
print(input_path)
print(f"Initial shape: {df.shape}")


# ============================================================
# Required columns
# ============================================================

LASV = get_col(df, ["LASV", "SV_LA"])
RASV = get_col(df, ["RASV", "SV_RA"])

SV_LV = get_col(df, ["SV_LV", "LVSV"])
SV_RV = get_col(df, ["SV_RV", "RVSV"])

CVP = get_col(df, ["CVP"])

# RAP is not explicitly present in your current config CSV.
# In your pre-sim config, Pm_RA is initialized as CVP, so we use Pm_RA as RAP proxy.
RAP = get_col(df, ["RAP", "Pm_RA"])

ESP_RV = get_col(df, ["ESP_RV", "ESPRV"])
EDP_RV = get_col(df, ["EDP_RV", "EDPRV"])

ESP_LV = get_col(df, ["ESP_LV", "ESPLV"])
EDP_LV = get_col(df, ["EDP_LV", "EDPLV"])


# ============================================================
# Round 2 physiological conditions
# ============================================================

# LASV and RASV same order of magnitude.
# Meaning: neither is more than 10x the other.
asv_max = pd.concat([LASV, RASV], axis=1).max(axis=1)
asv_min = pd.concat([LASV, RASV], axis=1).min(axis=1)

cond_lasv_rasv_same_order = (
    (LASV > 0)
    & (RASV > 0)
    & (safe_ratio(asv_max, asv_min) < 10)
)

# abs(LASV - RASV) < 1 ml
cond_lasv_rasv_difference = (LASV - RASV).abs() < 1

# ASV < VSV / 3
# Apply separately for left and right side.
cond_lasv_below_lvsv_third = LASV < (SV_LV / 3)
cond_rasv_below_rvsv_third = RASV < (SV_RV / 3)
cond_asv_below_vsv_third = cond_lasv_below_lvsv_third & cond_rasv_below_rvsv_third

# CVP = RAP
# Use tolerance because these are floating point values.
cond_cvp_equals_rap = np.isclose(CVP, RAP, atol=1e-6, rtol=1e-6)

# ESPRV > EDPRV
cond_esprv_above_edprv = ESP_RV > EDP_RV

# ESPLV > EDPLV
cond_esplv_above_edplv = ESP_LV > EDP_LV


round2_valid = (
    cond_lasv_rasv_same_order
    & cond_lasv_rasv_difference
    & cond_asv_below_vsv_third
    & cond_cvp_equals_rap
    & cond_esprv_above_edprv
    & cond_esplv_above_edplv
)


# ============================================================
# Add diagnostics
# ============================================================

df["round2_valid"] = round2_valid

df["round2_cond_lasv_rasv_same_order"] = cond_lasv_rasv_same_order
df["round2_cond_lasv_rasv_difference_lt_1ml"] = cond_lasv_rasv_difference
df["round2_cond_lasv_below_lvsv_third"] = cond_lasv_below_lvsv_third
df["round2_cond_rasv_below_rvsv_third"] = cond_rasv_below_rvsv_third
df["round2_cond_asv_below_vsv_third"] = cond_asv_below_vsv_third
df["round2_cond_cvp_equals_rap"] = cond_cvp_equals_rap
df["round2_cond_esprv_above_edprv"] = cond_esprv_above_edprv
df["round2_cond_esplv_above_edplv"] = cond_esplv_above_edplv

df["LASV_RASV_abs_diff"] = (LASV - RASV).abs()
df["LASV_RASV_ratio"] = safe_ratio(asv_max, asv_min)
df["LASV_over_LVSV"] = safe_ratio(LASV, SV_LV)
df["RASV_over_RVSV"] = safe_ratio(RASV, SV_RV)
df["CVP_minus_RAP"] = CVP - RAP
df["ESP_RV_minus_EDP_RV"] = ESP_RV - EDP_RV
df["ESP_LV_minus_EDP_LV"] = ESP_LV - EDP_LV


# ============================================================
# Split valid / invalid
# ============================================================

valid_df = df[round2_valid].copy()
invalid_df = df[~round2_valid].copy()

print()
print(f"Patients/configs passing Round 2: {len(valid_df)} / {len(df)}")
print(f"Patients/configs failing Round 2: {len(invalid_df)} / {len(df)}")

print()
print("Condition pass counts:")
print(f"LASV and RASV same order magnitude:      {cond_lasv_rasv_same_order.sum()} / {len(df)}")
print(f"abs(LASV - RASV) < 1 ml:                 {cond_lasv_rasv_difference.sum()} / {len(df)}")
print(f"LASV < SV_LV / 3:                        {cond_lasv_below_lvsv_third.sum()} / {len(df)}")
print(f"RASV < SV_RV / 3:                        {cond_rasv_below_rvsv_third.sum()} / {len(df)}")
print(f"ASV < VSV / 3 both sides:                {cond_asv_below_vsv_third.sum()} / {len(df)}")
print(f"CVP = RAP:                               {cond_cvp_equals_rap.sum()} / {len(df)}")
print(f"ESP_RV > EDP_RV:                         {cond_esprv_above_edprv.sum()} / {len(df)}")
print(f"ESP_LV > EDP_LV:                         {cond_esplv_above_edplv.sum()} / {len(df)}")


# ============================================================
# Select exactly 100 valid patients/configs
# ============================================================

n_target = 100

if len(valid_df) < n_target:
    raise ValueError(
        f"Only {len(valid_df)} patients passed Round 2, "
        f"but you requested {n_target}."
    )

selected_100 = (
    valid_df
    .sample(n=n_target, random_state=42)
    .reset_index(drop=True)
)

# Optional: make sure selected patients have clean base IDs
selected_100["base_patient_id"] = np.arange(1, len(selected_100) + 1)


# ============================================================
# Save outputs
# ============================================================

output_path.parent.mkdir(parents=True, exist_ok=True)
valid_configs_output_path.parent.mkdir(parents=True, exist_ok=True)

selected_100.to_csv(output_path, index=False)
valid_df.to_csv(valid_configs_output_path, index=False)
invalid_df.to_csv(invalid_output_path, index=False)

print()
print("Saved selected 100 Round 2 valid patients/configs to:")
print(output_path)

print()
print("Saved all Round 2 valid full configs to:")
print(valid_configs_output_path)

print()
print("Saved Round 2 invalid full configs to:")
print(invalid_output_path)

print()
print(f"Final selected shape: {selected_100.shape}")