function result_row = run_one_case_from_config(config_row, model)
%% ========================================================================
% Run one Simulink simulation from one full scalar config row.
%
% The CSV contains scalar variables only.
% This function regenerates vector variables needed by Simulink:
%   vol
%   EDPVR_LV, ESPVR_LV, phi_a_lin_LV
%   EDPVR_RV, ESPVR_RV, phi_a_lin_RV
%   EDPVR_LA, ESPVR_LA, phi_a_lin_LA
%   EDPVR_RA, ESPVR_RA, phi_a_lin_RA
%   EDP_IS, ESP_IS
%   t, epsilon, alpha
%% ========================================================================

simulation_id = config_row.simulation_id(1);

%% ------------------------------------------------------------
% Initialize outputs
%% ------------------------------------------------------------

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
    % 1. Assign all numeric scalar config variables to base workspace
    %% ------------------------------------------------------------

    var_names = config_row.Properties.VariableNames;

    for ii = 1:numel(var_names)
        var_name = var_names{ii};
        value = config_row.(var_name);

        if istable(value)
            value = value{1, 1};
        end

        if iscell(value)
            value = value{1};
        end

        if isstring(value)
            % Metadata only, not needed by Simulink.
            continue;
        end

        if ischar(value)
            % Metadata only, not needed by Simulink.
            continue;
        end

        if isnumeric(value) || islogical(value)
            if isscalar(value)
                assignin("base", var_name, value);
            end
        end
    end

    %% ------------------------------------------------------------
    % 2. Convert config row to struct for easier access
    %% ------------------------------------------------------------

    cfg = table2struct(config_row);

    %% ------------------------------------------------------------
    % 3. Regenerate vector variables
    %% ------------------------------------------------------------

    vol = 0:0.1:300;

    % -------------------------
    % Left ventricle
    % -------------------------

    EDPVR_LV = cfg.alpha_LV .* vol.^(cfg.beta_LV) + cfg.Poffset_LV;

    ESPVR_LV = ...
        (1 - ((cfg.Vs_LV - vol) ./ (cfg.Vs_LV - cfg.Vd_LV)).^2) ...
        .* cfg.Ps_LV;

    phi_a_lin_LV = ...
        (cfg.ESP_LV - cfg.Poffset_LV) ./ (cfg.ESV_LV - cfg.V0_LV) ...
        .* vol + cfg.Poffset_LV;

    % -------------------------
    % Right ventricle
    % -------------------------

    EDPVR_RV = cfg.alpha_RV .* vol.^(cfg.beta_RV) + cfg.Poffset_RV;

    ESPVR_RV = ...
        (1 - ((cfg.Vs_RV - vol) ./ (cfg.Vs_RV - cfg.Vd_RV)).^2) ...
        .* cfg.Ps_RV;

    phi_a_lin_RV = ...
        (cfg.ESP_RV - cfg.Poffset_RV) ./ (cfg.ESV_RV - cfg.V0_RV) ...
        .* vol + cfg.Poffset_RV;

    % -------------------------
    % Left atrium
    % -------------------------

    EDPVR_LA = cfg.alpha_LA .* vol.^(cfg.beta_LA) + cfg.Poffset_LA;

    ESPVR_LA = ...
        (1 - ((cfg.Vs_LA - vol) ./ (cfg.Vs_LA - cfg.Vd_LA)).^2) ...
        .* cfg.Ps_LA;

    phi_a_lin_LA = ...
        (cfg.ESP_LA - cfg.Poffset_LA) ./ (cfg.ESV_LA - cfg.V0_LA) ...
        .* vol + cfg.Poffset_LA;

    % -------------------------
    % Right atrium
    % -------------------------

    EDPVR_RA = cfg.alpha_RA .* vol.^(cfg.beta_RA) + cfg.Poffset_RA;

    ESPVR_RA = ...
        (1 - ((cfg.Vs_RA - vol) ./ (cfg.Vs_RA - cfg.Vd_RA)).^2) ...
        .* cfg.Ps_RA;

    phi_a_lin_RA = ...
        (cfg.ESP_RA - cfg.Poffset_RA) ./ (cfg.ESV_RA - cfg.V0_RA) ...
        .* vol + cfg.Poffset_RA;

    % -------------------------
    % Interventricular septum
    % -------------------------

    EDP_IS = cfg.alpha_IS .* vol.^(cfg.beta_IS) + cfg.Poffset_IS;

    ESP_IS = ...
        (1 - ((cfg.Vs_IS - vol) ./ (cfg.Vs_IS - cfg.Vd_IS)).^2) ...
        .* cfg.Ps_IS;

    % -------------------------
    % Controller arrays
    % -------------------------

    t = linspace(0, cfg.Tresp, 1000);
    epsilon = 1 ./ cfg.Tresp .* t;
    alpha = epsilon - floor(epsilon);

    %% ------------------------------------------------------------
    % 4. Assign regenerated arrays to base workspace
    %% ------------------------------------------------------------

    vector_vars = {
        "vol", ...
        "EDPVR_LV", "ESPVR_LV", "phi_a_lin_LV", ...
        "EDPVR_RV", "ESPVR_RV", "phi_a_lin_RV", ...
        "EDPVR_LA", "ESPVR_LA", "phi_a_lin_LA", ...
        "EDPVR_RA", "ESPVR_RA", "phi_a_lin_RA", ...
        "EDP_IS", "ESP_IS", ...
        "t", "epsilon", "alpha"
    };

    for ii = 1:numel(vector_vars)
        var_name = vector_vars{ii};
        assignin("base", var_name, eval(var_name));
    end

    %% ------------------------------------------------------------
    % 5. Run Simulink
    %% ------------------------------------------------------------

    out = sim(model);

    %% ------------------------------------------------------------
    % 6. Extract outputs
    %% ------------------------------------------------------------

    [~, a] = min(abs(out.tout - 12));

    % LA pressure
    if cfg.st_a == 1
        LAP_out = out.logsout.getElement("LAP").Values.Data;
    else
        LAP_out = out.logsout.getElement("LAP_LIN").Values.Data;
    end

    LAP_real = mean(LAP_out(a:end));

    % Systemic arterial pressure
    AoP_out = out.logsout.getElement("AoP").Values.Data;
    DAP_real = min(AoP_out(a:end));
    SAP_real = max(AoP_out(a:end));

    % LV volumes
    LVV_out = out.logsout.getElement("LVV").Values.Data;
    ESV_LV_real = min(LVV_out(a:end));
    EDV_LV_real = max(LVV_out(a:end));

    % RA pressure
    if cfg.st_a == 1
        RAP_out = out.logsout.getElement("RAP").Values.Data;
    else
        RAP_out = out.logsout.getElement("RAP_LIN").Values.Data;
    end

    RAP_real = mean(RAP_out(a:end));

    % RV volumes
    RVV_out = out.logsout.getElement("RVV").Values.Data;
    ESV_RV_real = min(RVV_out(a:end));
    EDV_RV_real = max(RVV_out(a:end));

    % Pulmonary arterial pressure
    PAP_out = out.logsout.getElement("PAP").Values.Data;
    sPAP_real = max(PAP_out(a:end));
    dPAP_real = min(PAP_out(a:end));

    % CO
    CO_out = out.logsout.getElement("CO").Values.Data;
    CO_real = mean(CO_out(a:end));

    simulation_status = "success";

catch ME
    simulation_status = "failed";

    full_error = getReport(ME, "extended", "hyperlinks", "off");
    error_message = string(full_error);

    fprintf("\nSimulation failed for simulation_id=%d\n", simulation_id);
    fprintf("%s\n", full_error);
end

%% ------------------------------------------------------------
% 7. Return row
%% ------------------------------------------------------------

result_row = config_row;

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