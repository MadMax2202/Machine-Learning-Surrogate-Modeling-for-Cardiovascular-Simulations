from pathlib import Path
import pandas as pd
import subprocess
import scipy.io
import numpy as np

# ============================================================
# ROOT
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

MATLAB_DIR = ROOT / "04_Matlab_&_Simulink"

OUTPUT_DIR = (
    ROOT
    / "01_Data"
    / "Conditional_Sampling"
    / "patients"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# FILES
# ============================================================

MATLAB_SCRIPT = "conditional_sampling_generate_patients"

MAT_FILE = MATLAB_DIR / "DCM_patients.mat"

CSV_OUTPUT = (
    OUTPUT_DIR
    / "conditional_sampling_100_patients.csv"
)

# ============================================================
# RUN MATLAB
# ============================================================

print("=" * 60)
print("RUNNING MATLAB CONDITIONAL SAMPLING")
print("=" * 60)

matlab_command = (
    f"{MATLAB_SCRIPT}; exit;"
)

subprocess.run(
    [
        "matlab",
        "-batch",
        matlab_command
    ],
    cwd=MATLAB_DIR,
    check=True
)

print("\nMATLAB generation complete.")

# ============================================================
# LOAD .MAT FILE
# ============================================================

print("\nLoading generated patients...")

mat_data = scipy.io.loadmat(
    MAT_FILE,
    squeeze_me=True,
    struct_as_record=False
)

patients = mat_data["patients"]

# ============================================================
# CONVERT MATLAB STRUCT -> PYTHON
# ============================================================

rows = []

for i, p in enumerate(np.atleast_1d(patients)):

    row = {
        "patient_id": i + 1,

        "EDVLV": getattr(p, "EDVLV", np.nan),
        "ESVLV": getattr(p, "ESVLV", np.nan),
        "LVSV": getattr(p, "LVSV", np.nan),
        "LVEF": getattr(p, "LVEF", np.nan),

        "EDVRV": getattr(p, "EDVRV", np.nan),
        "ESVRV": getattr(p, "ESVRV", np.nan),
        "RVSV": getattr(p, "RVSV", np.nan),
        "RVEF": getattr(p, "RVEF", np.nan),

        "hr": getattr(p, "hr", np.nan),

        "COLV": getattr(p, "COLV", np.nan),

        "SVR": getattr(p, "SVR", np.nan),
        "PVR": getattr(p, "PVR", np.nan),

        "CVP": getattr(p, "CVP", np.nan),
        "LAP": getattr(p, "LAP", np.nan),

        "MAP": getattr(p, "MAP", np.nan),

        "SAP": getattr(p, "SAP", np.nan),
        "DAP": getattr(p, "DAP", np.nan),

        "mPAP": getattr(p, "mPAP", np.nan),
        "sPAP": getattr(p, "sPAP", np.nan),
        "dPAP": getattr(p, "dPAP", np.nan),

        "weight": getattr(p, "weight", np.nan),

        "Rsysven": getattr(p, "Rsysven", np.nan),

        "mcfp": getattr(p, "mcfp", np.nan),

        "graft_length": getattr(p, "l", np.nan),
    }

    rows.append(row)

# ============================================================
# DATAFRAME
# ============================================================

df = pd.DataFrame(rows)

# ============================================================
# DERIVED VARIABLES
# ============================================================

df["BSA"] = np.sqrt(
    (df["weight"] * 100 * 121) / 3600
)

# ============================================================
# SAVE
# ============================================================

df.to_csv(CSV_OUTPUT, index=False)

print("\nSaved patient dataset:")
print(CSV_OUTPUT)

print("\nDataset shape:")
print(df.shape)

print("\nFirst patients:")
print(df.head())

print("\nGeneration complete.")