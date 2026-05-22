from pathlib import Path
import numpy as np
import pandas as pd


# ============================================================
# Paths
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

input_path = (
    ROOT
    / "01_Data"
    / "Conditional_Sampling_v2"
    / "patients"
    / "conditional_sampling_300_round1_valid_patients.csv"
)

output_path = (
    ROOT
    / "01_Data"
    / "Conditional_Sampling_v2"
    / "configs"
    / "conditional_sampling_300_full_scalar_configs_before_sim.csv"
)


# ============================================================
# Helpers
# ============================================================

def get_value(row: pd.Series, possible_names: list[str], default=None, required: bool = True):
    """
    Get one value from a row using several possible column names.
    """
    for name in possible_names:
        if name in row.index:
            value = row[name]
            if pd.notna(value):
                return float(value)

    if required:
        raise KeyError(
            f"Missing required variable. Tried: {possible_names}. "
            f"Available columns: {list(row.index)}"
        )

    return default


def safe_divide(num, den):
    """
    Avoid hard crash on divide by zero.
    Returns NaN if denominator is zero or invalid.
    """
    if den == 0 or pd.isna(den):
        return np.nan
    return num / den


def value_at_volume(curve: np.ndarray, vol: np.ndarray, target_volume: float) -> float:
    """
    Return curve value closest to a target volume.
    """
    idx = int(np.argmin(np.abs(vol - target_volume)))
    return float(curve[idx])


def add_curve_summaries(config: dict, name: str, curve: np.ndarray):
    """
    Save scalar summaries of an array curve.
    We do not save full arrays in CSV.
    """
    config[f"{name}_min"] = float(np.nanmin(curve))
    config[f"{name}_max"] = float(np.nanmax(curve))
    config[f"{name}_mean"] = float(np.nanmean(curve))
    config[f"{name}_last3_mean"] = float(np.nanmean(curve[-3:]))


# ============================================================
# Main config builder
# ============================================================

def build_full_scalar_config(row: pd.Series) -> dict:
    config = {}

    # ------------------------------------------------------------
    # 1. IDs
    # ------------------------------------------------------------

    if "simulation_id" in row.index:
        simulation_id = int(row["simulation_id"])
    elif "patient_id" in row.index:
        simulation_id = int(row["patient_id"])
    else:
        simulation_id = int(row.name)

    config["simulation_id"] = simulation_id

    if "patient_id" in row.index:
        config["patient_id"] = int(row["patient_id"])
    else:
        config["patient_id"] = simulation_id

    # ------------------------------------------------------------
    # 2. Patient-specific targets
    # ------------------------------------------------------------

    age = 5.0

    weight = get_value(row, ["weight"])
    hr = get_value(row, ["hr"])

    BSA = get_value(row, ["BSA"], required=False)
    if BSA is None or pd.isna(BSA):
        # Same approximation as your MATLAB script.
        BSA = np.sqrt((weight * 100 * 121) / 3600)

    SAP = get_value(row, ["SAP"])
    DAP = get_value(row, ["DAP"])
    CVP = get_value(row, ["CVP"])
    LAP = get_value(row, ["LAP"])

    sPAP = get_value(row, ["sPAP"])
    dPAP = get_value(row, ["dPAP", "dPAPA"])

    EDV_LV = get_value(row, ["EDVLV", "EDV_LV"])
    ESV_LV = get_value(row, ["ESVLV", "ESV_LV"])
    EDV_RV = get_value(row, ["EDVRV", "EDV_RV"])
    ESV_RV = get_value(row, ["ESVRV", "ESV_RV"])

    # ------------------------------------------------------------
    # 3. Tunable coefficients
    # Defaults are baseline values if not present yet.
    # ------------------------------------------------------------

    k_Vtot = get_value(row, ["k_Vtot"], default=67.5, required=False)
    k_Vsys = get_value(row, ["k_Vsys"], default=0.84, required=False)
    k_Vusv_sys = get_value(row, ["k_Vusv_sys"], default=0.84, required=False)
    k_Vusv_sys_ven = get_value(row, ["k_Vusv_sys_ven"], default=0.95, required=False)
    k_Vusv_pulm_ven = get_value(row, ["k_Vusv_pulm_ven"], default=0.80, required=False)

    k_Ctot = get_value(row, ["k_Ctot"], default=2.15, required=False)
    k_Csys = get_value(row, ["k_Csys"], default=0.85, required=False)

    k_Rsysven = get_value(row, ["k_Rsysven"], default=60 / 1000, required=False)
    k_Rpulmart = get_value(row, ["k_Rpulmart"], default=2 / 3, required=False)

    k_ESP_LV = get_value(row, ["k_ESP_LV"], default=1.0, required=False)
    k_ESP_RV = get_value(row, ["k_ESP_RV"], default=1.0, required=False)

    # ------------------------------------------------------------
    # 4. Scenario switches and inactive VAD values
    # ------------------------------------------------------------

    st_a = 0
    st_v = 0
    st_VAD = 0
    st_VADtype = 0

    L = 1e-6
    R = 1e-6
    rpm = 5500
    C_can_H = 5e-6

    # ------------------------------------------------------------
    # 5. Derived physiological variables
    # ------------------------------------------------------------

    MAP = get_value(row, ["MAP"], default=np.nan, required=False)
    if pd.isna(MAP):
        MAP = DAP + (SAP - DAP) / 3

    mPAP = get_value(row, ["mPAP"], default=np.nan, required=False)
    if pd.isna(mPAP):
        mPAP = np.mean([sPAP, dPAP])

    SV_LV = EDV_LV - ESV_LV
    SV_RV = EDV_RV - ESV_RV

    CO = get_value(row, ["COLV", "CO"], default=np.nan, required=False)
    if pd.isna(CO):
        CO = SV_LV * hr

    CO0 = 5000.0

    EF_LV = safe_divide(SV_LV, EDV_LV) * 100
    EF_RV = safe_divide(SV_RV, EDV_RV) * 100

    SVR = get_value(row, ["SVR"], default=np.nan, required=False)
    if pd.isna(SVR):
        SVR = safe_divide(MAP - CVP, CO / 60)

    PVR = get_value(row, ["PVR"], default=np.nan, required=False)
    if pd.isna(PVR):
        PVR = safe_divide(mPAP - LAP, CO / 60)

    T = 60 / hr
    Tdia = 0.5 * (
        np.exp((-0.01207) * (hr - 40))
        + np.exp((-0.038) * (hr - 40))
    )
    Tsys = T - Tdia
    tau = Tdia

    # ------------------------------------------------------------
    # 6. Compliance and resistance variables
    # ------------------------------------------------------------

    Ctot = k_Ctot * weight
    Csys = k_Csys * Ctot
    Cpulm = Ctot - Csys

    Csysart = safe_divide(SV_LV, SAP - DAP)
    Csysven = Csys - Csysart

    Cpulmart = safe_divide(SV_RV, sPAP - dPAP) * 0.65
    Cpulmven = Cpulm - Cpulmart

    Rtotsys = SVR
    Rtotpulm = PVR

    Rsysven = get_value(row, ["Rsysven"], default=np.nan, required=False)
    if pd.isna(Rsysven):
        Rsysven = safe_divide(k_Rsysven * CO0, CO)

    Rsysart = Rtotsys - Rsysven

    Rpulmart = k_Rpulmart * Rtotpulm
    Rpulmven = Rtotpulm - Rpulmart

    mcfp = get_value(row, ["mcfp"], default=np.nan, required=False)
    if pd.isna(mcfp):
        mcfp = CO / 60 * Rsysven + CVP

    # ------------------------------------------------------------
    # 7. Blood volume variables
    # ------------------------------------------------------------

    Vtot = k_Vtot * weight
    Vsys = k_Vsys * Vtot
    Vpulm = Vtot - Vsys

    Vsv_tot = Ctot * mcfp
    Vusv_tot = Vtot - Vsv_tot

    Vusv_sys = k_Vusv_sys * Vusv_tot
    Vusv_pulm = Vusv_tot - Vusv_sys

    Vusv_sys_ven = k_Vusv_sys_ven * Vusv_sys
    Vusv_pulm_ven = k_Vusv_pulm_ven * Vusv_pulm

    # ------------------------------------------------------------
    # 8. Heart variables: ventricles
    # ------------------------------------------------------------

    An = 27.78
    Bn = 2.76

    vol = np.arange(0, 300.0 + 0.1, 0.1)

    # Left ventricle
    Pm_LV = LAP
    Vm_LV = EDV_LV

    Vs_LV = EDV_LV + 15
    ESP_LV = k_ESP_LV * SAP

    Ps_LV = ESP_LV
    V0_LV = 0.0
    Vd_LV = 0.0
    Poffset_LV = 0.0

    V30_LV = V0_LV + ((Vm_LV - V0_LV) / ((Pm_LV / An) ** (1 / Bn)))
    beta_LV = np.log(Pm_LV / 30) / np.log(Vm_LV / V30_LV)
    alpha_LV = 30 / (V30_LV ** beta_LV)

    EDPVR_LV = alpha_LV * (vol ** beta_LV) + Poffset_LV
    ESPVR_LV = (1 - ((Vs_LV - vol) / (Vs_LV - Vd_LV)) ** 2) * Ps_LV
    phi_a_lin_LV = (ESP_LV - Poffset_LV) / (ESV_LV - V0_LV) * vol + Poffset_LV

    EDP_LV = LAP

    # Right ventricle
    Pm_RV = CVP
    Vm_RV = EDV_RV

    Vs_RV = EDV_RV + 15
    ESP_RV = k_ESP_RV * sPAP

    Ps_RV = ESP_RV
    V0_RV = 0.0
    Vd_RV = 0.0
    Poffset_RV = 0.0

    V30_RV = V0_RV + ((Vm_RV - V0_RV) / ((Pm_RV / An) ** (1 / Bn)))
    beta_RV = np.log(Pm_RV / 30) / np.log(Vm_RV / V30_RV)
    alpha_RV = 30 / (V30_RV ** beta_RV)

    EDPVR_RV = alpha_RV * (vol ** beta_RV) + Poffset_RV
    ESPVR_RV = (1 - ((Vs_RV - vol) / (Vs_RV - Vd_RV)) ** 2) * Ps_RV
    phi_a_lin_RV = (ESP_RV - Poffset_RV) / (ESV_RV - V0_RV) * vol + Poffset_RV

    EDP_RV = CVP

    # ------------------------------------------------------------
    # 9. Heart variables: atria
    # ------------------------------------------------------------

    ESP_LA = LAP * 1.2
    EDV_LA = 0.65 * EDV_LV
    SV_LA = 1 / 5 * SV_LV
    ESV_LA = EDV_LA - SV_LA
    EF_LA = safe_divide(SV_LA, EDV_LA) * 100
    LASV = SV_LA

    Pm_LA = LAP
    Vm_LA = EDV_LA
    Vs_LA = EDV_LA + 5
    Ps_LA = ESP_LA
    V0_LA = 0.0
    Vd_LA = 0.0
    Poffset_LA = 0.0

    V30_LA = V0_LA + ((Vm_LA - V0_LA) / ((Pm_LA / An) ** (1 / Bn)))
    beta_LA = np.log(Pm_LA / 30) / np.log(Vm_LA / V30_LA)
    alpha_LA = 30 / (V30_LA ** beta_LA)

    EDPVR_LA = alpha_LA * (vol ** beta_LA) + Poffset_LA
    ESPVR_LA = (1 - ((Vs_LA - vol) / (Vs_LA - Vd_LA)) ** 2) * Ps_LA
    phi_a_lin_LA = (ESP_LA - Poffset_LA) / (ESV_LA - V0_LA) * vol + Poffset_LA

    ESP_RA = CVP * 1.2
    EDV_RA = 0.55 * EDV_RV
    SV_RA = 1 / 5 * SV_RV
    ESV_RA = EDV_RA - SV_RA
    EF_RA = safe_divide(SV_RA, EDV_RA) * 100
    RASV = SV_RA

    Pm_RA = CVP
    Vm_RA = EDV_RA
    Vs_RA = EDV_RA + 5
    Ps_RA = ESP_RA
    V0_RA = 0.0
    Vd_RA = 0.0
    Poffset_RA = 0.0

    V30_RA = V0_RA + ((Vm_RA - V0_RA) / ((Pm_RA / An) ** (1 / Bn)))
    beta_RA = np.log(Pm_RA / 30) / np.log(Vm_RA / V30_RA)
    alpha_RA = 30 / (V30_RA ** beta_RA)

    EDPVR_RA = alpha_RA * (vol ** beta_RA) + Poffset_RA
    ESPVR_RA = (1 - ((Vs_RA - vol) / (Vs_RA - Vd_RA)) ** 2) * Ps_RA
    phi_a_lin_RA = (ESP_RA - Poffset_RA) / (ESV_RA - V0_RA) * vol + Poffset_RA

    Cra = 4.2 * 2
    Cla = 1.6 * 2

    # ------------------------------------------------------------
    # 10. Valve constants
    # ------------------------------------------------------------

    rho = 1060.0
    fct = 10.0

    Rdir_MV = 0.0075
    Rinv_MV = 50.0
    l_MV = 0.003
    r_MV = (31.1 / 2) * 10 ** -3
    Lmv = rho * (l_MV / (r_MV ** 2 * np.pi))
    Lmv = Lmv * (1 / 133.322) * (1 / 10 ** 6)
    Lmv = Lmv / fct

    Rdir_TV = 0.00375
    Rinv_TV = 50.0
    l_TV = 0.003
    r_TV = (36.4 / 2) * 10 ** -3
    Ltv = rho * (l_TV / (r_TV ** 2 * np.pi))
    Ltv = Ltv * (1 / 133.322) * (1 / 10 ** 6)
    Ltv = Ltv / fct

    Rdir_AV = 0.00375
    Rinv_AV = 50.0
    l_AV = 0.003
    r_AV = (23.2 / 2) * 10 ** -3
    Lav = rho * (l_AV / (r_AV ** 2 * np.pi))
    Lav = Lav * (1 / 133.322) * (1 / 10 ** 6)
    Lav = Lav / fct

    Rdir_PV = 0.00375
    Rinv_PV = 50.0
    l_PV = 0.003
    r_PV = (24.3 / 2) * 10 ** -3
    Lpv = rho * (l_PV / (r_PV ** 2 * np.pi))
    Lpv = Lpv * (1 / 133.322) * (1 / 10 ** 6)
    Lpv = Lpv / fct

    # ------------------------------------------------------------
    # 11. Interventricular septum variables
    # ------------------------------------------------------------

    Vs_IS = Vs_LV * 0.1
    Ps_IS = Ps_LV
    Vd_IS = Vd_LV * 0.1
    V0_IS = V0_LV * 0.1
    Vm_IS = Vm_LV * 0.1
    Pm_IS = Vm_LV
    Poffset_IS = Poffset_LV

    V30_IS = V0_IS + ((Vm_IS - V0_IS) / ((Pm_IS / An) ** (1 / Bn)))
    beta_IS = np.log(Pm_IS / 30) / np.log(Vm_IS / V30_IS)
    alpha_IS = 30 / (V30_IS ** beta_IS)

    EDP_IS = alpha_IS * (vol ** beta_IS) + Poffset_IS
    ESP_IS = (1 - ((Vs_IS - vol) / (Vs_IS - Vd_IS)) ** 2) * Ps_IS

    # ------------------------------------------------------------
    # 12. Controller constants
    # ------------------------------------------------------------

    Tresp = 5.0
    Ti = 2.0
    Te = Tresp - Ti

    # t, epsilon, alpha are arrays. Do not save full arrays.

    GaR = 0.1
    GpR = 0.33
    DR = 3 * 0
    TauR = 1.5
    Rsp_max = 4.5
    Rsp_min = 2.12
    Rep_max = 1.9
    Rep_min = 0.91
    Rmax = (Rsp_max * Rep_max) / (Rsp_max + Rep_max)
    Rmin = (Rsp_min * Rep_min) / (Rsp_min + Rep_min)
    SR0 = 1.0
    kR = (Rmax - Rmin) / (4 * SR0)

    GaV = 9.29
    GpV = 0.0
    DV = 5 * 0
    TauV = 10.0
    Vusv_min = 871.0
    Vusv_max = 1371.0
    Vuev_min = 1275.0
    Vuev_max = 1475.0
    Vmax = Vusv_max + Vuev_max
    Vmin = Vusv_min + Vuev_min
    SV0 = 1.0
    kV = (Vmax - Vmin) / (4 * SV0) / 100

    GaE = 0.012
    GpE = 0.0
    DE = 2 * 0
    TauE = 1.5
    Emin_LV = -0.5
    Emax_LV = 0.5
    Emin_RV = -0.5
    Emax_RV = 0.5
    SE0 = 1.0
    kELV = (Emax_LV - Emin_LV) / (4 * SE0)
    kERV = (Emax_RV - Emin_RV) / (4 * SE0)

    GaTv = 0.028
    GpTv = 0.25
    GaTs = 0.015
    GpTs = 0.0
    DTv = 0.5 * 0
    TauTv = 0.8
    DTs = 3 * 0
    TauTs = 1.8
    Tmin = 0.3
    Tmax = 1.308
    ST0 = 1.0
    kT = (Tmax - Tmin) / (4 * ST0)

    # ------------------------------------------------------------
    # 13. Save scalar variables
    # ------------------------------------------------------------

    scalar_vars = {
        # IDs
        "simulation_id": simulation_id,
        "patient_id": config["patient_id"],

        # patient targets
        "age": age,
        "weight": weight,
        "BSA": BSA,
        "hr": hr,
        "SAP": SAP,
        "DAP": DAP,
        "MAP": MAP,
        "CVP": CVP,
        "LAP": LAP,
        "sPAP": sPAP,
        "dPAP": dPAP,
        "mPAP": mPAP,
        "EDV_LV": EDV_LV,
        "ESV_LV": ESV_LV,
        "EDV_RV": EDV_RV,
        "ESV_RV": ESV_RV,

        # k parameters
        "k_Vtot": k_Vtot,
        "k_Vsys": k_Vsys,
        "k_Vusv_sys": k_Vusv_sys,
        "k_Vusv_sys_ven": k_Vusv_sys_ven,
        "k_Vusv_pulm_ven": k_Vusv_pulm_ven,
        "k_Ctot": k_Ctot,
        "k_Csys": k_Csys,
        "k_Rsysven": k_Rsysven,
        "k_Rpulmart": k_Rpulmart,
        "k_ESP_LV": k_ESP_LV,
        "k_ESP_RV": k_ESP_RV,

        # switches
        "st_a": st_a,
        "st_v": st_v,
        "st_VAD": st_VAD,
        "st_VADtype": st_VADtype,
        "L": L,
        "R": R,
        "rpm": rpm,
        "C_can_H": C_can_H,

        # derived physio
        "SV_LV": SV_LV,
        "SV_RV": SV_RV,
        "LVSV": SV_LV,
        "RVSV": SV_RV,
        "CO": CO,
        "CO0": CO0,
        "EF_LV": EF_LV,
        "EF_RV": EF_RV,
        "SVR": SVR,
        "PVR": PVR,
        "T": T,
        "Tdia": Tdia,
        "Tsys": Tsys,
        "tau": tau,

        # compliances and resistances
        "Ctot": Ctot,
        "Csys": Csys,
        "Cpulm": Cpulm,
        "Csysart": Csysart,
        "Csysven": Csysven,
        "Cpulmart": Cpulmart,
        "Cpulmven": Cpulmven,
        "Rtotsys": Rtotsys,
        "Rtotpulm": Rtotpulm,
        "Rsysven": Rsysven,
        "Rsysart": Rsysart,
        "Rpulmart": Rpulmart,
        "Rpulmven": Rpulmven,
        "mcfp": mcfp,

        # volumes
        "Vtot": Vtot,
        "Vsys": Vsys,
        "Vpulm": Vpulm,
        "Vsv_tot": Vsv_tot,
        "Vusv_tot": Vusv_tot,
        "Vusv_sys": Vusv_sys,
        "Vusv_pulm": Vusv_pulm,
        "Vusv_sys_ven": Vusv_sys_ven,
        "Vusv_pulm_ven": Vusv_pulm_ven,

        # generic heart constants
        "An": An,
        "Bn": Bn,

        # LV scalars
        "Pm_LV": Pm_LV,
        "Vm_LV": Vm_LV,
        "Vs_LV": Vs_LV,
        "ESP_LV": ESP_LV,
        "EDP_LV": EDP_LV,
        "Ps_LV": Ps_LV,
        "V0_LV": V0_LV,
        "Vd_LV": Vd_LV,
        "Poffset_LV": Poffset_LV,
        "V30_LV": V30_LV,
        "alpha_LV": alpha_LV,
        "beta_LV": beta_LV,

        # RV scalars
        "Pm_RV": Pm_RV,
        "Vm_RV": Vm_RV,
        "Vs_RV": Vs_RV,
        "ESP_RV": ESP_RV,
        "EDP_RV": EDP_RV,
        "Ps_RV": Ps_RV,
        "V0_RV": V0_RV,
        "Vd_RV": Vd_RV,
        "Poffset_RV": Poffset_RV,
        "V30_RV": V30_RV,
        "alpha_RV": alpha_RV,
        "beta_RV": beta_RV,

        # LA scalars
        "ESP_LA": ESP_LA,
        "EDV_LA": EDV_LA,
        "SV_LA": SV_LA,
        "LASV": LASV,
        "ESV_LA": ESV_LA,
        "EF_LA": EF_LA,
        "Pm_LA": Pm_LA,
        "Vm_LA": Vm_LA,
        "Vs_LA": Vs_LA,
        "Ps_LA": Ps_LA,
        "V0_LA": V0_LA,
        "Vd_LA": Vd_LA,
        "Poffset_LA": Poffset_LA,
        "V30_LA": V30_LA,
        "alpha_LA": alpha_LA,
        "beta_LA": beta_LA,

        # RA scalars
        "ESP_RA": ESP_RA,
        "EDV_RA": EDV_RA,
        "SV_RA": SV_RA,
        "RASV": RASV,
        "ESV_RA": ESV_RA,
        "EF_RA": EF_RA,
        "Pm_RA": Pm_RA,
        "Vm_RA": Vm_RA,
        "Vs_RA": Vs_RA,
        "Ps_RA": Ps_RA,
        "V0_RA": V0_RA,
        "Vd_RA": Vd_RA,
        "Poffset_RA": Poffset_RA,
        "V30_RA": V30_RA,
        "alpha_RA": alpha_RA,
        "beta_RA": beta_RA,

        "Cra": Cra,
        "Cla": Cla,

        # valves
        "rho": rho,
        "fct": fct,
        "Rdir_MV": Rdir_MV,
        "Rinv_MV": Rinv_MV,
        "Lmv": Lmv,
        "Rdir_TV": Rdir_TV,
        "Rinv_TV": Rinv_TV,
        "Ltv": Ltv,
        "Rdir_AV": Rdir_AV,
        "Rinv_AV": Rinv_AV,
        "Lav": Lav,
        "Rdir_PV": Rdir_PV,
        "Rinv_PV": Rinv_PV,
        "Lpv": Lpv,

        # septum
        "Vs_IS": Vs_IS,
        "Ps_IS": Ps_IS,
        "Vd_IS": Vd_IS,
        "V0_IS": V0_IS,
        "Vm_IS": Vm_IS,
        "Pm_IS": Pm_IS,
        "Poffset_IS": Poffset_IS,
        "V30_IS": V30_IS,
        "alpha_IS": alpha_IS,
        "beta_IS": beta_IS,

        # controller
        "Tresp": Tresp,
        "Ti": Ti,
        "Te": Te,
        "GaR": GaR,
        "GpR": GpR,
        "DR": DR,
        "TauR": TauR,
        "Rsp_max": Rsp_max,
        "Rsp_min": Rsp_min,
        "Rep_max": Rep_max,
        "Rep_min": Rep_min,
        "Rmax": Rmax,
        "Rmin": Rmin,
        "SR0": SR0,
        "kR": kR,
        "GaV": GaV,
        "GpV": GpV,
        "DV": DV,
        "TauV": TauV,
        "Vusv_min": Vusv_min,
        "Vusv_max": Vusv_max,
        "Vuev_min": Vuev_min,
        "Vuev_max": Vuev_max,
        "Vmax": Vmax,
        "Vmin": Vmin,
        "SV0": SV0,
        "kV": kV,
        "GaE": GaE,
        "GpE": GpE,
        "DE": DE,
        "TauE": TauE,
        "Emin_LV": Emin_LV,
        "Emax_LV": Emax_LV,
        "Emin_RV": Emin_RV,
        "Emax_RV": Emax_RV,
        "SE0": SE0,
        "kELV": kELV,
        "kERV": kERV,
        "GaTv": GaTv,
        "GpTv": GpTv,
        "GaTs": GaTs,
        "GpTs": GpTs,
        "DTv": DTv,
        "TauTv": TauTv,
        "DTs": DTs,
        "TauTs": TauTs,
        "Tmin": Tmin,
        "Tmax": Tmax,
        "ST0": ST0,
        "kT": kT,
    }

    config.update(scalar_vars)

    # ------------------------------------------------------------
    # 14. Save useful summaries of array variables
    # ------------------------------------------------------------

    add_curve_summaries(config, "EDPVR_LV", EDPVR_LV)
    add_curve_summaries(config, "ESPVR_LV", ESPVR_LV)
    add_curve_summaries(config, "phi_a_lin_LV", phi_a_lin_LV)

    add_curve_summaries(config, "EDPVR_RV", EDPVR_RV)
    add_curve_summaries(config, "ESPVR_RV", ESPVR_RV)
    add_curve_summaries(config, "phi_a_lin_RV", phi_a_lin_RV)

    add_curve_summaries(config, "EDPVR_LA", EDPVR_LA)
    add_curve_summaries(config, "ESPVR_LA", ESPVR_LA)
    add_curve_summaries(config, "phi_a_lin_LA", phi_a_lin_LA)

    add_curve_summaries(config, "EDPVR_RA", EDPVR_RA)
    add_curve_summaries(config, "ESPVR_RA", ESPVR_RA)
    add_curve_summaries(config, "phi_a_lin_RA", phi_a_lin_RA)

    add_curve_summaries(config, "EDP_IS", EDP_IS)
    add_curve_summaries(config, "ESP_IS", ESP_IS)

    # Physiologically meaningful values at patient-specific volumes
    config["EDPVR_LV_at_EDV_LV"] = value_at_volume(EDPVR_LV, vol, EDV_LV)
    config["ESPVR_LV_at_ESV_LV"] = value_at_volume(ESPVR_LV, vol, ESV_LV)
    config["phi_a_lin_LV_at_ESV_LV"] = value_at_volume(phi_a_lin_LV, vol, ESV_LV)

    config["EDPVR_RV_at_EDV_RV"] = value_at_volume(EDPVR_RV, vol, EDV_RV)
    config["ESPVR_RV_at_ESV_RV"] = value_at_volume(ESPVR_RV, vol, ESV_RV)
    config["phi_a_lin_RV_at_ESV_RV"] = value_at_volume(phi_a_lin_RV, vol, ESV_RV)

    config["EDPVR_LA_at_EDV_LA"] = value_at_volume(EDPVR_LA, vol, EDV_LA)
    config["ESPVR_LA_at_ESV_LA"] = value_at_volume(ESPVR_LA, vol, ESV_LA)
    config["phi_a_lin_LA_at_ESV_LA"] = value_at_volume(phi_a_lin_LA, vol, ESV_LA)

    config["EDPVR_RA_at_EDV_RA"] = value_at_volume(EDPVR_RA, vol, EDV_RA)
    config["ESPVR_RA_at_ESV_RA"] = value_at_volume(ESPVR_RA, vol, ESV_RA)
    config["phi_a_lin_RA_at_ESV_RA"] = value_at_volume(phi_a_lin_RA, vol, ESV_RA)

    return config


# ============================================================
# Run script
# ============================================================

def main():
    patients = pd.read_csv(input_path)

    print("Loaded Round 1 valid patients:")
    print(input_path)
    print(f"Input shape: {patients.shape}")

    configs = []

    for idx, row in patients.iterrows():
        try:
            config = build_full_scalar_config(row)
            config["config_status"] = "success"
            config["config_error"] = ""
        except Exception as exc:
            config = {
                "simulation_id": row.get("simulation_id", idx),
                "patient_id": row.get("patient_id", idx),
                "config_status": "failed",
                "config_error": str(exc),
            }

        configs.append(config)

    configs_df = pd.DataFrame(configs)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    configs_df.to_csv(output_path, index=False)

    print()
    print("Saved full scalar configs before simulation:")
    print(output_path)
    print(f"Output shape: {configs_df.shape}")

    print()
    print("Config status counts:")
    print(configs_df["config_status"].value_counts(dropna=False))

    if "config_status" in configs_df.columns:
        failed = configs_df[configs_df["config_status"] == "failed"]
        if len(failed) > 0:
            print()
            print("Some configs failed. First errors:")
            print(failed[["simulation_id", "patient_id", "config_error"]].head(10))


if __name__ == "__main__":
    main()