function run_chunk_conditional_sampling_from_manifest(array_id)
%% ========================================================================
% Run one SLURM array chunk for conditional sampling v2.
%
% Usage from MATLAB:
%   run_chunk_conditional_sampling_from_manifest(1)
%
% Usage from SLURM:
%   matlab -batch "run_chunk_conditional_sampling_from_manifest"
%
% If array_id is not provided, the function reads SLURM_ARRAY_TASK_ID.
%% ========================================================================

clc;

%% ------------------------------------------------------------
% 0. Resolve array ID
%% ------------------------------------------------------------

if nargin < 1 || isempty(array_id)
    array_id_str = getenv("SLURM_ARRAY_TASK_ID");

    if strlength(array_id_str) == 0
        error("No array_id provided and SLURM_ARRAY_TASK_ID is empty.");
    end

    array_id = str2double(array_id_str);
end

fprintf("Running SLURM array_id = %d\n", array_id);

%% ------------------------------------------------------------
% 1. Paths
%% ------------------------------------------------------------

this_file = mfilename("fullpath");
matlab_dir = fileparts(this_file);
ROOT = fileparts(fileparts(matlab_dir));

CAMPAIGN_NAME = "conditional_sampling_100_patients_100_variations_v2";

manifest_path = fullfile( ...
    ROOT, ...
    "01_Data", ...
    "Conditional_Sampling_v2", ...
    "generated_samples", ...
    CAMPAIGN_NAME, ...
    CAMPAIGN_NAME + "_manifest.csv" ...
);

fprintf("Manifest path:\n%s\n", manifest_path);

if ~isfile(manifest_path)
    error("Manifest file not found: %s", manifest_path);
end

manifest = readtable(manifest_path);

idx = find(manifest.array_id == array_id, 1);

if isempty(idx)
    error("array_id=%d not found in manifest.", array_id);
end

samples_path = string(manifest.samples_path(idx));
results_path = string(manifest.results_path(idx));

fprintf("Samples chunk:\n%s\n", samples_path);
fprintf("Results chunk:\n%s\n", results_path);

if ~isfile(samples_path)
    error("Samples chunk not found: %s", samples_path);
end

results_dir = fileparts(results_path);

if ~exist(results_dir, "dir")
    mkdir(results_dir);
end

%% ------------------------------------------------------------
% 2. Load chunk
%% ------------------------------------------------------------

samples = readtable(samples_path);

fprintf("Loaded chunk with %d rows and %d columns.\n", height(samples), width(samples));

%% ------------------------------------------------------------
% 3. Load Simulink model
%% ------------------------------------------------------------

model = "MyComplexModel_V13R2023a";

fprintf("Loading Simulink model: %s\n", model);
load_system(model);

%% ------------------------------------------------------------
% 4. Run rows
%% ------------------------------------------------------------

all_results = table();

for i = 1:height(samples)

    simulation_id = samples.simulation_id(i);

    fprintf("\n------------------------------------------------------------\n");
    fprintf("Chunk array_id=%d | row %d/%d | simulation_id=%d\n", ...
        array_id, i, height(samples), simulation_id);
    fprintf("------------------------------------------------------------\n");

    sample_row = samples(i, :);

    result_row = run_one_case_from_config(sample_row, model);

    all_results = [all_results; result_row];

    % Save partial progress every 5 simulations.
    if mod(i, 5) == 0 || i == height(samples)
        writetable(all_results, results_path);
        fprintf("Partial results saved: %s\n", results_path);
    end
end

%% ------------------------------------------------------------
% 5. Final save
%% ------------------------------------------------------------

writetable(all_results, results_path);

fprintf("\n============================================================\n");
fprintf("Finished chunk array_id=%d\n", array_id);
fprintf("Results saved to:\n%s\n", results_path);
fprintf("============================================================\n");

end