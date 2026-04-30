clear; clc;

fprintf("Starting pediatric DCM no-VAD linear bounds stress-test simulations...\n");

%% ------------------------------------------------------------
% 1. Load model
%% ------------------------------------------------------------

model = 'MyComplexModel_V13R2023a';

model_file = fullfile(pwd, [model '.slx']);

if ~isfile(model_file)
    error("Model file not found: %s", model_file);
end

load_system(model_file);

%% ------------------------------------------------------------
% 2. Input and output paths
%% ------------------------------------------------------------

samples_path = fullfile('..', '01_Data', 'generated_samples', ...
    'pediatric_dcm_patient_01', 'bounds_stress_test', ...
    'pediatric_dcm_patient_01_bounds_stress_test_samples.csv');

results_dir = fullfile('..', '01_Data', 'simulation_results', ...
    'pediatric_dcm_patient_01', 'bounds_stress_test');

if ~exist(results_dir, 'dir')
    mkdir(results_dir);
end

% Start with factor 1.0 only.
% Later, change the filename when you test larger ranges.
results_path = fullfile(results_dir, ...
    'pediatric_dcm_patient_01_bounds_stress_test_results_factor_gt1_to_2.csv');

%% ------------------------------------------------------------
% 3. Load stress-test samples
%% ------------------------------------------------------------

samples = readtable(samples_path);

% DEBUG/STAGE 1: run only expansion factor 1.0 first
% samples = samples(samples.expansion_factor == 1.0, :);

% Later options:
% samples = samples(samples.expansion_factor <= 1.5, :);
% samples = samples(samples.expansion_factor <= 2.0, :);
% samples = samples; % run all expansion factors

samples = samples(samples.expansion_factor > 1.0 & samples.expansion_factor <= 2.0, :);

fprintf("Loaded %d stress-test simulation case(s).\n", height(samples));

%% ------------------------------------------------------------
% 4. Reset previous result file
%% ------------------------------------------------------------

if isfile(results_path)
    delete(results_path);
end

results = table();

%% ------------------------------------------------------------
% 5. Run simulations
%% ------------------------------------------------------------

for i = 1:height(samples)

    fprintf("Running stress-test case %d/%d, simulation_id=%d, expansion_factor=%.2f...\n", ...
        i, height(samples), samples.simulation_id(i), samples.expansion_factor(i));

    sample_row = samples(i, :);

    result_row = run_one_case_pediatric_noVAD_linear(sample_row, model);

    % Add expansion_factor here, without modifying run_one_case
    result_row.expansion_factor = sample_row.expansion_factor;

    % Move expansion_factor near the front
    result_row = movevars(result_row, 'expansion_factor', 'After', 'simulation_id');

    results = [results; result_row];

    % Save after each case so progress is not lost if MATLAB crashes
    writetable(results, results_path);
end

%% ------------------------------------------------------------
% 6. Finish
%% ------------------------------------------------------------

fprintf("Finished bounds stress-test simulations.\n");
fprintf("Results saved to:\n%s\n", results_path);