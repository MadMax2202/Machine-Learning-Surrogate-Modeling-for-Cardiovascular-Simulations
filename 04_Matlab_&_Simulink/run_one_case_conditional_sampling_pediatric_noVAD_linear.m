function result_row = run_one_case_conditional_sampling_pediatric_noVAD_linear(sample_row, model)

simulation_id = sample_row.simulation_id;

% Initialize outputs as NaN in case the simulation fails
LAP_real = NaN;
RAP_real = NaN;
SAP_real = NaN;
DAP_real = NaN;
sPAP_real = NaN;
dPAP_real = NaN;
EDV_LV_real = NaN;
ESV_LV_real = NaN;
EDV_RV_real = NaN;
ESV_RV_real = NaN;
CO_real = NaN;

simulation_status = "failed";
error_message = "";

try
    %% ------------------------------------------------------------
    % 1. Patient-specific targets from conditional sampling
    %% ------------------------------------------------------------

    age = 5;

    weight = get_required_scalar(sample_row, {'weight'});
    hr = get_required_scalar(sample_row, {'hr'});

    if has_var(sample_row, 'BSA')
        BSA = get_required_scalar(sample_row, {'BSA'});
    else
        % Approximate pediatric BSA if not provided.
        % Assumes height ≈ 121 cm for current pediatric preset.
        BSA = sqrt((weight * 100 * 121) / 3600);
    end

    SAP = get_required_scalar(sample_row, {'SAP'});
    DAP = get_required_scalar(sample_row, {'DAP'});
    CVP = get_required_scalar(sample_row, {'CVP'});
    LAP = get_required_scalar(sample_row, {'LAP'});

    sPAP = get_required_scalar(sample_row, {'sPAP'});
    dPAP = get_required_scalar(sample_row, {'dPAP'});

    EDV_LV = get_required_scalar(sample_row, {'EDVLV', 'EDV_LV'});
    ESV_LV = get_required_scalar(sample_row, {'ESVLV', 'ESV_LV'});
    EDV_RV = get_required_scalar(sample_row, {'EDVRV', 'EDV_RV'});
    ESV_RV = get_required_scalar(sample_row, {'ESVRV', 'ESV_RV'});

    %% ------------------------------------------------------------
    % 2. Tunable coefficients from sample row
    %% ------------------------------------------------------------

    k_Vtot = sample_row.k_Vtot;
    k_Vsys = sample_row.k_Vsys;
    k_Vusv_sys = sample_row.k_Vusv_sys;
    k_Vusv_sys_ven = sample_row.k_Vusv_sys_ven;
    k_Vusv_pulm_ven = sample_row.k_Vusv_pulm_ven;

    k_Ctot = sample_row.k_Ctot;
    k_Csys = sample_row.k_Csys;

    k_Rsysven = sample_row.k_Rsysven;
    k_Rpulmart = sample_row.k_Rpulmart;

    k_ESP_LV = sample_row.k_ESP_LV;
    k_ESP_RV = sample_row.k_ESP_RV;

    %% ------------------------------------------------------------
    % 3. Scenario switches
    %% ------------------------------------------------------------

    st_a = 0;      % 0 = linear atria
    st_v = 0;      % 0 = linear ventricles
    st_VAD = 0;    % 0 = VAD off
    st_VADtype = 0;

    % Avoid Inf in inactive VAD/graft branch if Simulink still compiles it
    L = 1e-6;
    R = 1e-6;
    rpm = 5500;
    C_can_H = 5e-6;

    %% ------------------------------------------------------------
    % 4. Derived physiological variables
    %% ------------------------------------------------------------

    if has_var(sample_row, 'MAP')
        MAP = get_required_scalar(sample_row, {'MAP'});
    else
        MAP = DAP + (SAP - DAP) / 3;
    end

    if has_var(sample_row, 'mPAP')
        mPAP = get_required_scalar(sample_row, {'mPAP'});
    else
        mPAP = mean([sPAP dPAP]);
    end

    SV_LV = EDV_LV - ESV_LV;
    SV_RV = EDV_RV - ESV_RV;

    if has_var(sample_row, 'COLV')
        CO = get_required_scalar(sample_row, {'COLV'});
    elseif has_var(sample_row, 'CO')
        CO = get_required_scalar(sample_row, {'CO'});
    else
        CO = SV_LV * hr;
    end

    CO0 = 5000; % Adult reference value used for Rsysven scaling in original pediatric script

    EF_LV = SV_LV / EDV_LV * 100;
    EF_RV = SV_RV / EDV_RV * 100;

    if has_var(sample_row, 'SVR')
        SVR = get_required_scalar(sample_row, {'SVR'});
    else
        SVR = (MAP - CVP) / (CO / 60);
    end

    if has_var(sample_row, 'PVR')
        PVR = get_required_scalar(sample_row, {'PVR'});
    else
        PVR = (mPAP - LAP) / (CO / 60);
    end

    T = 60 / hr;
    Tdia = 0.5 * (exp((-0.01207) * (hr - 40)) + exp((-0.038 * (hr - 40))));
    Tsys = T - Tdia;
    tau = Tdia;

    %% ------------------------------------------------------------
    % 5. Compliance and resistance variables
    %% ------------------------------------------------------------

    Ctot = k_Ctot * weight;
    Csys = k_Csys * Ctot;
    Cpulm = Ctot - Csys;

    Csysart = SV_LV / (SAP - DAP);
    Csysven = Csys - Csysart;

    % Pediatric original script uses a 0.65 factor here
    Cpulmart = SV_RV / (sPAP - dPAP) * 0.65;
    Cpulmven = Cpulm - Cpulmart;

    Rtotsys = SVR;
    Rtotpulm = PVR;

    % Use conditional sampled Rsysven if available, otherwise compute using k_Rsysven.
    if has_var(sample_row, 'Rsysven')
        Rsysven = get_required_scalar(sample_row, {'Rsysven'});
    else
        Rsysven = k_Rsysven * CO0 / CO;
    end

    Rsysart = Rtotsys - Rsysven;

    Rpulmart = k_Rpulmart * Rtotpulm;
    Rpulmven = Rtotpulm - Rpulmart;

    if has_var(sample_row, 'mcfp')
        mcfp = get_required_scalar(sample_row, {'mcfp'});
    else
        mcfp = CO / 60 * Rsysven + CVP;
    end

    %% ------------------------------------------------------------
    % 6. Blood volume variables
    %% ------------------------------------------------------------

    Vtot = k_Vtot * weight;
    Vsys = k_Vsys * Vtot;
    Vpulm = Vtot - Vsys;

    Vsv_tot = Ctot * mcfp;
    Vusv_tot = Vtot - Vsv_tot;

    Vusv_sys = k_Vusv_sys * Vusv_tot;
    Vusv_pulm = Vusv_tot - Vusv_sys;

    Vusv_sys_ven = k_Vusv_sys_ven * Vusv_sys;
    Vusv_pulm_ven = k_Vusv_pulm_ven * Vusv_pulm;

    %% ------------------------------------------------------------
    % 7. Heart variables: ventricles
    %% ------------------------------------------------------------

    An = 27.78;
    Bn = 2.76;

    vol = 0:0.1:300;

    % -------------------------
    % Left ventricle
    % -------------------------

    Pm_LV = LAP;
    Vm_LV = EDV_LV;

    Vs_LV = EDV_LV + 15;
    ESP_LV = k_ESP_LV * SAP;

    Ps_LV = ESP_LV;
    V0_LV = 0;
    Vd_LV = 0;
    Poffset_LV = 0;

    V30_LV = V0_LV + ((Vm_LV - V0_LV) / ((Pm_LV / An)^(1 / Bn)));
    beta_LV = (log(Pm_LV / 30)) / (log(Vm_LV / V30_LV));
    alpha_LV = 30 / (V30_LV.^beta_LV);

    phi_p_LV = alpha_LV * vol.^(beta_LV) + Poffset_LV;
    EDPVR_LV = phi_p_LV;

    phi_a_LV = (1 - ((Vs_LV - vol) / (Vs_LV - Vd_LV)).^2) * Ps_LV;
    ESPVR_LV = phi_a_LV;

    phi_a_lin_LV = (ESP_LV - Poffset_LV) / (ESV_LV - V0_LV) .* vol + Poffset_LV;

    % -------------------------
    % Right ventricle
    % -------------------------

    Pm_RV = CVP;
    Vm_RV = EDV_RV;

    Vs_RV = EDV_RV + 15;
    ESP_RV = k_ESP_RV * sPAP;

    Ps_RV = ESP_RV;
    V0_RV = 0;
    Vd_RV = 0;
    Poffset_RV = 0;

    V30_RV = V0_RV + ((Vm_RV - V0_RV) / ((Pm_RV / An)^(1 / Bn)));
    beta_RV = (log(Pm_RV / 30)) / (log(Vm_RV / V30_RV));
    alpha_RV = 30 / (V30_RV.^beta_RV);

    phi_p_RV = alpha_RV * vol.^(beta_RV) + Poffset_RV;
    EDPVR_RV = phi_p_RV;

    phi_a_RV = (1 - ((Vs_RV - vol) / (Vs_RV - Vd_RV)).^2) * Ps_RV;
    ESPVR_RV = phi_a_RV;

    phi_a_lin_RV = (ESP_RV - Poffset_RV) / (ESV_RV - V0_RV) .* vol + Poffset_RV;

    %% ------------------------------------------------------------
    % 8. Heart variables: atria
    %% ------------------------------------------------------------

    % -------------------------
    % Left atrium
    % -------------------------

    ESP_LA = LAP * 1.2;
    EDV_LA = 0.65 * EDV_LV;
    SV_LA = 1 / 5 * SV_LV;
    ESV_LA = EDV_LA - SV_LA;
    EF_LA = SV_LA / EDV_LA * 100;

    Pm_LA = LAP;
    Vm_LA = EDV_LA;
    Vs_LA = EDV_LA + 5;
    Ps_LA = ESP_LA;
    V0_LA = 0;
    Vd_LA = 0;
    Poffset_LA = 0;

    V30_LA = V0_LA + ((Vm_LA - V0_LA) / ((Pm_LA / An)^(1 / Bn)));
    beta_LA = (log(Pm_LA / 30)) / (log(Vm_LA / V30_LA));
    alpha_LA = 30 / (V30_LA.^beta_LA);

    phi_p_LA = alpha_LA * vol.^(beta_LA) + Poffset_LA;
    EDPVR_LA = phi_p_LA;

    phi_a_LA = (1 - ((Vs_LA - vol) / (Vs_LA - Vd_LA)).^2) * Ps_LA;
    ESPVR_LA = phi_a_LA;

    phi_a_lin_LA = (ESP_LA - Poffset_LA) / (ESV_LA - V0_LA) .* vol + Poffset_LA;

    % -------------------------
    % Right atrium
    % -------------------------

    ESP_RA = CVP * 1.2;
    EDV_RA = 0.55 * EDV_RV;
    SV_RA = 1 / 5 * SV_RV;
    ESV_RA = EDV_RA - SV_RA;
    EF_RA = SV_RA / EDV_RA * 100;

    Pm_RA = CVP;
    Vm_RA = EDV_RA;
    Vs_RA = EDV_RA + 5;
    Ps_RA = ESP_RA;
    V0_RA = 0;
    Vd_RA = 0;
    Poffset_RA = 0;

    V30_RA = V0_RA + ((Vm_RA - V0_RA) / ((Pm_RA / An)^(1 / Bn)));
    beta_RA = (log(Pm_RA / 30)) / (log(Vm_RA / V30_RA));
    alpha_RA = 30 / (V30_RA.^beta_RA);

    phi_p_RA = alpha_RA * vol.^(beta_RA) + Poffset_RA;
    EDPVR_RA = phi_p_RA;

    phi_a_RA = (1 - ((Vs_RA - vol) / (Vs_RA - Vd_RA)).^2) * Ps_RA;
    ESPVR_RA = phi_a_RA;

    phi_a_lin_RA = (ESP_RA - Poffset_RA) / (ESV_RA - V0_RA) .* vol + Poffset_RA;

    % Linearized atria: passive compliances
    Cra = 4.2 * 2;
    Cla = 1.6 * 2;

    %% ------------------------------------------------------------
    % 9. Valve constants
    %% ------------------------------------------------------------

    rho = 1060;
    fct = 10;

    % Mitral Valve
    Rdir_MV = 0.0075;
    Rinv_MV = 50;
    l_MV = 0.003;
    r_MV = (31.1 / 2) * 10^-3;
    Lmv = rho * (l_MV / (r_MV^2 * pi));
    Lmv = Lmv * (1 / 133.322) * (1 / 10^6);
    Lmv = Lmv / fct;

    % Tricuspid Valve
    Rdir_TV = 0.00375;
    Rinv_TV = 50;
    l_TV = 0.003;
    r_TV = (36.4 / 2) * 10^-3;
    Ltv = rho * (l_TV / (r_TV^2 * pi));
    Ltv = Ltv * (1 / 133.322) * (1 / 10^6);
    Ltv = Ltv / fct;

    % Aortic Valve
    Rdir_AV = 0.00375;
    Rinv_AV = 50;
    l_AV = 0.003;
    r_AV = (23.2 / 2) * 10^-3;
    Lav = rho * (l_AV / (r_AV^2 * pi));
    Lav = Lav * (1 / 133.322) * (1 / 10^6);
    Lav = Lav / fct;

    % Pulmonary Valve
    Rdir_PV = 0.00375;
    Rinv_PV = 50;
    l_PV = 0.003;
    r_PV = (24.3 / 2) * 10^-3;
    Lpv = rho * (l_PV / (r_PV^2 * pi));
    Lpv = Lpv * (1 / 133.322) * (1 / 10^6);
    Lpv = Lpv / fct;

    %% ------------------------------------------------------------
    % 10. Interventricular septum variables
    %% ------------------------------------------------------------

    Vs_IS = Vs_LV * 0.1;
    Ps_IS = Ps_LV;
    Vd_IS = Vd_LV * 0.1;
    V0_IS = V0_LV * 0.1;
    Vm_IS = Vm_LV * 0.1;
    Pm_IS = Vm_LV;
    V30_IS = V0_IS + ((Vm_IS - V0_IS) / ((Pm_IS / An)^(1 / Bn)));
    Poffset_IS = Poffset_LV;

    beta_IS = (log(Pm_IS / 30)) / (log(Vm_IS / V30_IS));
    alpha_IS = 30 / (V30_IS.^beta_IS);

    phi_p_IS = alpha_IS * vol.^(beta_IS) + Poffset_IS;
    EDP_IS = phi_p_IS;

    phi_a_IS = (1 - ((Vs_IS - vol) / (Vs_IS - Vd_IS)).^2) * Ps_IS;
    ESP_IS = phi_a_IS;

    %% ------------------------------------------------------------
    % 11. Controller constants
    %% ------------------------------------------------------------

    Tresp = 5;
    Ti = 2;
    Te = Tresp - Ti;

    t = linspace(0, Tresp, 1000);
    epsilon = 1 / Tresp * t;
    alpha = epsilon - floor(epsilon);

    GaR = 0.1;
    GpR = 0.33;
    DR = 3 * 0;
    TauR = 1.5;
    Rsp_max = 4.5;
    Rsp_min = 2.12;
    Rep_max = 1.9;
    Rep_min = 0.91;
    Rmax = (Rsp_max * Rep_max) / (Rsp_max + Rep_max);
    Rmin = (Rsp_min * Rep_min) / (Rsp_min + Rep_min);
    SR0 = 1;
    kR = (Rmax - Rmin) / (4 * SR0);

    GaV = 9.29;
    GpV = 0;
    DV = 5 * 0;
    TauV = 10;
    Vusv_min = 871;
    Vusv_max = 1371;
    Vuev_min = 1275;
    Vuev_max = 1475;
    Vmax = Vusv_max + Vuev_max;
    Vmin = Vusv_min + Vuev_min;
    SV0 = 1;
    kV = (Vmax - Vmin) / (4 * SV0) / 100;

    GaE = 0.012;
    GpE = 0;
    DE = 2 * 0;
    TauE = 1.5;
    Emin_LV = -0.5;
    Emax_LV = 0.5;
    Emin_RV = -0.5;
    Emax_RV = 0.5;
    SE0 = 1;
    kELV = (Emax_LV - Emin_LV) / (4 * SE0);
    kERV = (Emax_RV - Emin_RV) / (4 * SE0);

    GaTv = 0.028;
    GpTv = 0.25;
    GaTs = 0.015;
    GpTs = 0;
    DTv = 0.5 * 0;
    TauTv = 0.8;
    DTs = 3 * 0;
    TauTs = 1.8;
    Tmin = 0.3;
    Tmax = 1.308;
    ST0 = 1;
    kT = (Tmax - Tmin) / (4 * ST0);

    %% ------------------------------------------------------------
    % 12. Push variables to base workspace for Simulink
    %% ------------------------------------------------------------

    vars_to_base = {
        'age', 'weight', 'BSA', 'hr', ...
        'SAP', 'DAP', 'MAP', 'CVP', 'LAP', 'sPAP', 'dPAP', 'mPAP', ...
        'EDV_LV', 'ESV_LV', 'EDV_RV', 'ESV_RV', ...
        'SV_LV', 'SV_RV', 'CO', 'CO0', 'EF_LV', 'EF_RV', ...
        'SVR', 'PVR', ...
        'T', 'Tdia', 'Tsys', 'tau', ...
        'Ctot', 'Csys', 'Cpulm', 'Csysart', 'Csysven', 'Cpulmart', 'Cpulmven', ...
        'Rtotsys', 'Rtotpulm', 'Rsysven', 'Rsysart', 'Rpulmart', 'Rpulmven', ...
        'mcfp', ...
        'Vtot', 'Vsys', 'Vpulm', 'Vsv_tot', 'Vusv_tot', ...
        'Vusv_sys', 'Vusv_pulm', 'Vusv_sys_ven', 'Vusv_pulm_ven', ...
        'An', 'Bn', 'vol', ...
        'Pm_LV', 'Vm_LV', 'Vs_LV', 'ESP_LV', 'Ps_LV', ...
        'V0_LV', 'Vd_LV', 'Poffset_LV', ...
        'alpha_LV', 'beta_LV', 'EDPVR_LV', 'ESPVR_LV', 'phi_a_lin_LV', ...
        'Pm_RV', 'Vm_RV', 'Vs_RV', 'ESP_RV', 'Ps_RV', ...
        'V0_RV', 'Vd_RV', 'Poffset_RV', ...
        'alpha_RV', 'beta_RV', 'EDPVR_RV', 'ESPVR_RV', 'phi_a_lin_RV', ...
        'ESP_LA', 'EDV_LA', 'SV_LA', 'ESV_LA', 'EF_LA', ...
        'Pm_LA', 'Vm_LA', 'Vs_LA', 'Ps_LA', ...
        'V0_LA', 'Vd_LA', 'Poffset_LA', ...
        'alpha_LA', 'beta_LA', 'EDPVR_LA', 'ESPVR_LA', 'phi_a_lin_LA', ...
        'ESP_RA', 'EDV_RA', 'SV_RA', 'ESV_RA', 'EF_RA', ...
        'Pm_RA', 'Vm_RA', 'Vs_RA', 'Ps_RA', ...
        'V0_RA', 'Vd_RA', 'Poffset_RA', ...
        'alpha_RA', 'beta_RA', 'EDPVR_RA', 'ESPVR_RA', 'phi_a_lin_RA', ...
        'Cra', 'Cla', ...
        'rho', 'fct', ...
        'Rdir_MV', 'Rinv_MV', 'Lmv', ...
        'Rdir_TV', 'Rinv_TV', 'Ltv', ...
        'Rdir_AV', 'Rinv_AV', 'Lav', ...
        'Rdir_PV', 'Rinv_PV', 'Lpv', ...
        'Vs_IS', 'Ps_IS', 'Vd_IS', 'V0_IS', 'Vm_IS', 'Pm_IS', ...
        'Poffset_IS', 'alpha_IS', 'beta_IS', 'EDP_IS', 'ESP_IS', ...
        'Tresp', 'Ti', 'Te', 't', 'epsilon', 'alpha', ...
        'GaR', 'GpR', 'DR', 'TauR', 'Rsp_max', 'Rsp_min', 'Rep_max', 'Rep_min', ...
        'Rmax', 'Rmin', 'SR0', 'kR', ...
        'GaV', 'GpV', 'DV', 'TauV', ...
        'Vusv_min', 'Vusv_max', 'Vuev_min', 'Vuev_max', ...
        'Vmax', 'Vmin', 'SV0', 'kV', ...
        'GaE', 'GpE', 'DE', 'TauE', ...
        'Emin_LV', 'Emax_LV', 'Emin_RV', 'Emax_RV', ...
        'SE0', 'kELV', 'kERV', ...
        'GaTv', 'GpTv', 'GaTs', 'GpTs', ...
        'DTv', 'TauTv', 'DTs', 'TauTs', ...
        'Tmin', 'Tmax', 'ST0', 'kT', ...
        'C_can_H', 'rpm', 'L', 'R', ...
        'st_a', 'st_v', 'st_VAD', 'st_VADtype'
    };

    for ii = 1:numel(vars_to_base)
        var_name = vars_to_base{ii};
        assignin('base', var_name, eval(var_name));
    end

    out = sim(model);

    %% ------------------------------------------------------------
    % 13. Extract outputs
    %% ------------------------------------------------------------

    [~, a] = min(abs(out.tout - 12));

    % LA
    if st_a == 1
        LAP_out = out.logsout.getElement('LAP').Values.Data;
    else
        LAP_out = out.logsout.getElement('LAP_LIN').Values.Data;
    end

    LAP_real = mean(LAP_out(a:end));

    % Systemic arterial pressure
    AoP_out = out.logsout.getElement('AoP').Values.Data;
    DAP_real = min(AoP_out(a:end));
    SAP_real = max(AoP_out(a:end));

    % LV volumes
    LVV_out = out.logsout.getElement('LVV').Values.Data;
    ESV_LV_real = min(LVV_out(a:end));
    EDV_LV_real = max(LVV_out(a:end));

    % RA
    if st_a == 1
        RAP_out = out.logsout.getElement('RAP').Values.Data;
    else
        RAP_out = out.logsout.getElement('RAP_LIN').Values.Data;
    end

    RAP_real = mean(RAP_out(a:end));

    % RV volumes
    RVV_out = out.logsout.getElement('RVV').Values.Data;
    ESV_RV_real = min(RVV_out(a:end));
    EDV_RV_real = max(RVV_out(a:end));

    % Pulmonary arterial pressure
    PAP_out = out.logsout.getElement('PAP').Values.Data;
    sPAP_real = max(PAP_out(a:end));
    dPAP_real = min(PAP_out(a:end));

    % CO
    CO_out = out.logsout.getElement('CO').Values.Data;
    CO_real = mean(CO_out(a:end));

    simulation_status = "success";

catch ME
    simulation_status = "failed";

    full_error = getReport(ME, 'extended', 'hyperlinks', 'off');
    error_message = string(full_error);

    fprintf("\nSimulation failed for simulation_id=%d\n", simulation_id);
    fprintf("%s\n", full_error);

    error_dir = fullfile('..', '01_Data', 'Conditional_Sampling', ...
        'simulation_results', 'conditional_sampling_100_patients_100_variations_v1', 'errors');

    if ~exist(error_dir, 'dir')
        mkdir(error_dir);
    end

    error_file = fullfile(error_dir, ...
        sprintf('simulation_%d_error.txt', simulation_id));

    fid = fopen(error_file, 'w');
    fprintf(fid, '%s', full_error);
    fclose(fid);
end

%% ------------------------------------------------------------
% 14. Return one result row
%% ------------------------------------------------------------

result_row = sample_row;

result_row.LAP_real = LAP_real;
result_row.RAP_real = RAP_real;
result_row.SAP_real = SAP_real;
result_row.DAP_real = DAP_real;
result_row.sPAP_real = sPAP_real;
result_row.dPAP_real = dPAP_real;
result_row.EDV_LV_real = EDV_LV_real;
result_row.ESV_LV_real = ESV_LV_real;
result_row.EDV_RV_real = EDV_RV_real;
result_row.ESV_RV_real = ESV_RV_real;
result_row.CO_real = CO_real;

result_row.simulation_status = simulation_status;
result_row.error_message = error_message;

end


%% ========================================================================
% Helper: check if a sample row contains a variable
%% ========================================================================

function tf = has_var(sample_row, variable_name)

    tf = ismember(variable_name, sample_row.Properties.VariableNames);

end


%% ========================================================================
% Helper: get scalar from one-row table using possible names
%% ========================================================================

function value = get_required_scalar(sample_row, possible_names)

    value = NaN;

    for i = 1:numel(possible_names)
        name = possible_names{i};

        if ismember(name, sample_row.Properties.VariableNames)
            value = sample_row.(name);

            if istable(value)
                value = value{1, 1};
            end

            if iscell(value)
                value = value{1};
            end

            if numel(value) ~= 1
                error("Variable %s is not scalar.", name);
            end

            return;
        end
    end

    error("Missing required variable. Tried: %s", strjoin(possible_names, ", "));

end