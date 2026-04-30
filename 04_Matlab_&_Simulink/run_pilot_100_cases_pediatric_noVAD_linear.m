clear; clc;

fprintf("Starting pediatric DCM no-VAD linear pilot simulations...\n");

model = 'MyComplexModel_V13R2023a';
load_system(model);

samples_path = fullfile('..', '01_Data', 'generated_samples', ...
    'pediatric_dcm_patient_01', ...
    'pediatric_dcm_patient_01_stage_1_samples_pilot_100.csv');

results_dir = fullfile('..', '01_Data', 'simulation_results', ...
    'pediatric_dcm_patient_01');

if ~exist(results_dir, 'dir')
    mkdir(results_dir);
end

results_path = fullfile(results_dir, ...
    'pediatric_dcm_patient_01_stage_1_results_pilot_100.csv');

samples = readtable(samples_path);

% DEBUG MODE: run only baseline simulation_id = 0
samples = samples(samples.simulation_id <= 20, :); 
% modify 20 to 1 or 'x' if we want different number of simulations 

fprintf("Loaded %d simulation case(s).\n", height(samples));

results = table();

for i = 1:height(samples)
    fprintf("Running case %d/%d, simulation_id=%d...\n", ...
        i, height(samples), samples.simulation_id(i));

    sample_row = samples(i, :);

    result_row = run_one_case_pediatric_noVAD_linear(sample_row, model);

    results = [results; result_row];

    % Save after each case so progress is not lost if MATLAB crashes.
    writetable(results, results_path);
end

fprintf("Finished pilot simulations.\n");
fprintf("Results saved to:\n%s\n", results_path);