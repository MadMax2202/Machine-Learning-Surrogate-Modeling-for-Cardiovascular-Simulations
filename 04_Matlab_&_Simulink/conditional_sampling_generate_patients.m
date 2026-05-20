%% 1. Base Settings
% a) Model
mdl = 'MyComplexModel_V12R2023a';
%load_system('MyComplexModel_V12R2023a.slx');
% run('VT_Parameter_ComplexModel_compr_Pediatric_DCM_LVAD.m');
% b) Patients
n_simulations = 100; % number of patients
rpm_values = 0;
n_rpm = numel(rpm_values);
% later: age, atm preset for 5yo
% c) States
st_a = 0; % Linear ESPVR for atria and ventricles
st_v = 0;
st_VAD = 0; % VAD off
%% 2. Ranges DCM (Pre-VAD)
n = 2;
mu_hr = 121; sd_hr = 29;
range_hr = [mu_hr - n*sd_hr, mu_hr + n*sd_hr];
pd_hr = makedist('Normal', 'mu', mu_hr, 'sigma', sd_hr);
tpd_hr = truncate(pd_hr, range_hr(1), range_hr(2));
mu_weight = 15.42; sd_weight = 3.70; 
range_weight = [mu_weight - n*sd_weight, mu_weight + n*sd_weight];
% range_weight = [14, 24]; % WHO weight-age curves, 95th percentile
pd_weight = makedist('Normal', 'mu', mu_weight, 'sigma', sd_weight);
tpd_weight = truncate(pd_weight, range_weight(1), range_weight(2));
mu_EDVLV = 131; sd_EDVLV = 49; 
range_EDVLV = [mu_EDVLV - n*sd_EDVLV, mu_EDVLV + n*sd_EDVLV];
pd_EDVLV = makedist('Normal', 'mu', mu_EDVLV, 'sigma', sd_EDVLV);
tpd_EDVLV = truncate(pd_EDVLV, range_EDVLV(1), range_EDVLV(2));
mu_ESVLV = 102; sd_ESVLV = 52; lb_ESVLV = 10;
range_ESVLV = [mu_ESVLV - n*sd_ESVLV, mu_ESVLV + n*sd_ESVLV];
pd_ESVLV = makedist('Normal', 'mu', mu_ESVLV, 'sigma', sd_ESVLV);
tpd_ESVLV = truncate(pd_ESVLV, range_ESVLV(1), range_ESVLV(2));
mu_LVSV = 22; sd_LVSV = 8; ub_LVSV = 35;
range_LVSV = [mu_LVSV - n*sd_LVSV, mu_LVSV + n*sd_LVSV];
pd_LVSV = makedist('Normal', 'mu', mu_LVSV, 'sigma', sd_LVSV);
tpd_LVSV = truncate(pd_LVSV, 7, 35);
mu_EDVRV = 54; sd_EDVRV = 16; % Healthy data; no data available
range_EDVRV = [mu_EDVRV - n*sd_EDVRV, mu_EDVRV + n*sd_EDVRV];
pd_EDVRV = makedist('Normal', 'mu', mu_EDVRV, 'sigma', sd_EDVRV);
tpd_EDVRV = truncate(pd_EDVRV, range_EDVRV(1), range_EDVRV(2));
mu_ESVRV = 22; sd_ESVRV = 14; lb_ESVRV = 10; % Healthy data; no data available
range_ESVRV = [mu_ESVRV - n*sd_ESVRV, mu_ESVRV + n*sd_ESVRV];
pd_ESVRV = makedist('Normal', 'mu', mu_ESVRV, 'sigma', sd_ESVRV);
tpd_ESVRV = truncate(pd_ESVRV, range_ESVRV(1), range_ESVRV(2));
mu_RVSV = mu_LVSV; sd_RVSV = sd_LVSV; % No data available; like LV
range_RVSV = [mu_RVSV - n*sd_RVSV, mu_RVSV + n*sd_RVSV];
pd_RVSV = makedist('Normal', 'mu', mu_RVSV, 'sigma', sd_RVSV);
tpd_RVSV = truncate(pd_RVSV, range_RVSV(1), range_RVSV(2));
mu_MAP = 63; sd_MAP = 12; lb_MAP = 40;
range_MAP = [mu_MAP - n*sd_MAP, mu_MAP + n*sd_MAP]; 
pd_MAP = makedist('Normal', 'mu', mu_MAP, 'sigma', sd_MAP);
tpd_MAP = truncate(pd_MAP, range_MAP(1), 100);
mu_SAP = 83; sd_SAP = 15; lb_SAP = 65;
range_SAP = [mu_SAP - n*sd_SAP, mu_SAP + n*sd_SAP]; 
pd_SAP = makedist('Normal', 'mu', mu_SAP, 'sigma', sd_SAP);
tpd_SAP = truncate(pd_SAP, lb_SAP, range_SAP(2));
mu_DAP = (3 * mu_MAP - mu_SAP)/2; sd_DAP = 15; ub_DAP = 60; % no data available
range_DAP = [mu_DAP - n*sd_DAP, mu_DAP + n*sd_DAP]; 
pd_DAP = makedist('Normal', 'mu', mu_DAP, 'sigma', sd_DAP);
tpd_DAP = truncate(pd_DAP, range_DAP(1), ub_DAP);
mu_LAP = 22; sd_LAP = 6.27; lb_LAP = 10;
range_LAP = [mu_LAP	- n*sd_LAP, mu_LAP + n*sd_LAP]; 
pd_LAP = makedist('Normal', 'mu', mu_LAP, 'sigma', sd_LAP);
tpd_LAP = truncate(pd_LAP, range_LAP(1), range_LAP(2));
mu_CVP = 13; sd_CVP = 5.76; lb_CVP = 5; 
range_CVP = [mu_CVP - n*sd_CVP, mu_CVP + n*sd_CVP];
pd_CVP = makedist('Normal', 'mu', mu_CVP, 'sigma', sd_CVP);
tpd_CVP = truncate(pd_CVP, range_CVP(1), range_CVP(2));
mu_mPAP = 39; sd_mPAP = 17.5; lb_mPAP = 15; ub_mPAP = 60;
range_mPAP = [mu_mPAP - n*sd_mPAP, mu_mPAP + n*sd_mPAP];
pd_mPAP = makedist('Normal', 'mu', mu_mPAP, 'sigma', sd_mPAP);
tpd_mPAP = truncate(pd_mPAP, range_mPAP(1), ub_mPAP);
mu_sPAP = mu_mPAP + 8.5; sd_sPAP = 15; lb_sPAP = 20; ub_sPAP = 60; % 79 (orig data) seems very high
range_sPAP = [mu_sPAP - n*sd_sPAP, mu_sPAP + n*sd_sPAP];
pd_sPAP = makedist('Normal', 'mu', mu_sPAP, 'sigma', sd_sPAP);
tpd_sPAP = truncate(pd_sPAP, lb_sPAP, ub_sPAP);
mu_dPAP = mu_mPAP - 8.5; sd_dPAP = 15; lb_dPAP = 5; ub_dPAP = 40; % no data available
range_dPAP = [mu_dPAP - n*sd_dPAP, mu_dPAP + n*sd_dPAP];
pd_dPAP = makedist('Normal', 'mu', mu_dPAP, 'sigma', sd_dPAP);
tpd_dPAP = truncate(pd_dPAP, lb_dPAP, ub_dPAP);
mu_LVEF = 19.85; sd_LVEF = 9.34; lb_LVEF = 5; ub_LVEF = 45;
range_LVEF = [mu_LVEF - n*sd_LVEF, mu_LVEF + n*sd_LVEF];
pd_LVEF = makedist('Normal', 'mu', mu_LVEF, 'sigma', sd_LVEF);
tpd_LVEF = truncate(pd_LVEF, lb_LVEF, ub_LVEF);
mu_RVEF = 58; sd_RVEF = 8; lb_RVEF = 40; % Healthy data; no data available
range_RVEF = [mu_RVEF - n*sd_RVEF, mu_RVEF + n*sd_RVEF]; 
pd_RVEF = makedist('Normal', 'mu', mu_RVEF, 'sigma', sd_RVEF);
tpd_RVEF = truncate(pd_RVEF, lb_RVEF, range_RVEF(2)+10);
mu_COLV = 2910*0.72; sd_COLV = 1000*0.72; lb_COLV = 1000; ub_COLV = 4500;
range_COLV = [mu_COLV - n*sd_COLV, mu_COLV + n*sd_COLV];
pd_COLV = makedist('Normal', 'mu', mu_COLV, 'sigma', sd_COLV);
tpd_COLV = truncate(pd_COLV, lb_COLV, ub_COLV);
mu_SVR = (mu_MAP - mu_CVP)/(mu_COLV/60); sd_SVR = mu_SVR/2; %lb_SVR = mu_SVR - 1*sd_SVR;
range_SVR = [mu_SVR - n*sd_SVR, mu_SVR + n*sd_SVR];
pd_SVR = makedist('Normal', 'mu', mu_SVR, 'sigma', sd_SVR);
tpd_SVR = truncate(pd_SVR, range_SVR(1), range_SVR(2));
mu_PVR = (mu_mPAP - mu_LAP)/(mu_COLV/60); sd_PVR = mu_PVR/2; lb_PVR = 0;
range_PVR = [mu_PVR - n*sd_PVR, mu_PVR + n*sd_PVR];
pd_PVR = makedist('Normal', 'mu', mu_PVR, 'sigma', sd_PVR);
tpd_PVR = truncate(pd_PVR, range_PVR(1), range_PVR(2));
range_fct = [0.5, 2.5];
pd_fct = makedist('Normal', 'mu', 1, 'sigma', 0.5);
range_l = [0.12, 0.23];
pd_l = makedist('Normal', 'mu', (0.12 + 0.23)/2, 'sigma', (0.12 + 0.23)/4);
tpd_l = truncate(pd_l, range_l(1), range_l(2));
%% 4. Sampling
max_passes = 15; % Rounds
failed = true(1, n_simulations);
patients = struct(); % Generated Patients
tic;
for pass = 1:max_passes
    todo = find(failed);
    if isempty(todo)
        break;
    end
    failed(:) = false;
    for i = todo
        try
            ok = true;
            attempts = 0;
            max_attempts = 1e3;
            % Draw EDVLV from range
            patients(i).EDVLV = random(tpd_EDVLV);
            % Draw LVEF from range
            patients(i).LVEF = random(tpd_LVEF);
            % Compute LVSV
            patients(i).LVSV = patients(i).LVEF/100 * patients(i).EDVLV;
            % Check if LVSV is in range
            attempts = 0;
            while (patients(i).LVSV < tpd_LVSV.Truncation(1) || patients(i).LVSV > tpd_LVSV.Truncation(2))
                patients(i).LVEF = random(tpd_LVEF); % Re-draw LVEF
                patients(i).LVSV = patients(i).LVEF/100 * patients(i).EDVLV; % Re-compute LVSV
                attempts = attempts + 1; % Safety against infinite loop
                if attempts > max_attempts
                    ok = false;
                    break;
                end
            end
            if ~ok, error('Abort: CO not satisfied'); end
            % Compute ESVLV
            patients(i).ESVLV = patients(i).EDVLV - patients(i).LVSV;
            % Draw hr from range
            patients(i).hr = round(random(tpd_hr));
        
            % Compute CO
            patients(i).COLV = patients(i).hr * patients(i).LVSV;
        
            % Draw RVEF
            patients(i).RVEF = random(tpd_RVEF);
            % Compute EDVRV
            patients(i).EDVRV = patients(i).LVSV / (patients(i).RVEF/100);
            % Compute ESVRV
            patients(i).ESVRV = patients(i).EDVRV - patients(i).LVSV;
            % Compute RVSV
            patients(i).RVSV = patients(i).EDVRV - patients(i).ESVRV;
            
            % Draw SVR
            patients(i).SVR = random(tpd_SVR);
        
            % Draw CVP
            patients(i).CVP = random(tpd_CVP);
        
            % Compute MAP
            patients(i).MAP = patients(i).CVP + (patients(i).SVR * ((patients(i).COLV)/60));
            % Draw SAP
            patients(i).SAP = random(tpd_SAP);
            % Check Pulsatility
            attempts = 0;
            while (patients(i).SAP - patients(i).MAP < 16 || patients(i).SAP - patients(i).MAP > 25)
                patients(i).SAP = random(tpd_SAP);
        
                attempts = attempts + 1; % Safety against infinite loop
                if attempts > max_attempts         
                    ok = false;
                    break;
                end
            end
            if ~ok, error('Abort: SAP not satisifed'); end
            % Compute DAP
            patients(i).DAP = (3 * patients(i).MAP - patients(i).SAP)/2;
        
            % Draw PVR
            patients(i).PVR = random(tpd_PVR);
        
            % Draw LAP
            patients(i).LAP = random(tpd_LAP);
        
            % Compute mPAP
            patients(i).mPAP = patients(i).LAP + (patients(i).PVR * (patients(i).COLV))/60;
        
            % Check if mPAP in range
            attempts = 0;
            while (patients(i).mPAP < tpd_mPAP.Truncation(1) || patients(i).mPAP > tpd_mPAP.Truncation(2))
                patients(i).LAP = random(tpd_LAP);
                patients(i).mPAP = patients(i).LAP + (patients(i).PVR * (patients(i).COLV))/60;
                attempts = attempts + 1; % Safety against infinite loop
                if attempts > max_attempts         
                    ok = false;
                    break;
                end
            end
            if ~ok, error('Abort: mPAP not satisfied'); end
            % Compute sPAP and dPAP -> Pulsatility dP =~ 20
            c = randi([7 10]);
            patients(i).sPAP = patients(i).mPAP + c;
            patients(i).dPAP = patients(i).mPAP - c;
            % Draw weight for total Compliance
            patients(i).weight = random(tpd_weight);
            % Compute Rven
            CO0 = 5000; % [mL/min]
            patients(i).Rsysven = 60/1000 * (CO0 / patients(i).COLV) * random(pd_fct);
            % Compute mcfp
            patients(i).mcfp = patients(i).COLV/60 * patients(i).Rsysven + patients(i).CVP;
            % Draw graft length
            patients(i).l = random(tpd_l);
        catch ME
            failed(i) = true;
        end
    end
end
if any(failed)
    warning('%d Patienten konnten nach %d Runden nicht erzeugt werden.', sum(failed), max_passes);
    fail_reason(i) = string(ME.message);
end
toc;
save('DCM_patients.mat', 'patients');