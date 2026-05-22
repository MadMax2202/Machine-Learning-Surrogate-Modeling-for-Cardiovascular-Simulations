function run_chunk_conditional_sampling_from_manifest(array_id)
%% ========================================================================
% Run one SLURM array chunk for conditional sampling v2.
%
% Location:
%   MAIN_PROJECT/04_Matlab_&_Simulink/conditional_sampling_v2/
%
% Usage from MATLAB:
%   run_chunk_conditional_sampling_from_manifest(1)
%
% Usage from SLURM:
%   matlab -singleCompThread -batch "run_chunk_conditional_sampling_from_manifest;"
%
% If array_id is not provided, the function reads SLURM_ARRAY_TASK_ID.
%% ========================================================================

clc;

fprintf("============================================================\n");
fprintf("CONDITIONAL SAMPLING V2 - CHUNK RUNNER\n");
fprintf("Start time: %s\n", string(datetime("now")));
fprintf("============================================================\n");

%% ------------------------------------------------------------
% 0. Resolve array ID
%% ------------------------------------------------------------

if nargin < 1 || isempty(array_id)

    array_id_str = getenv("SLURM_ARRAY_TASK_ID");

    if strlength(array_id_str) == 0
        error("No array_id provided and SLURM_ARRAY_TASK_ID is empty.");
    end

    array_id = str2double(array_id_str);

    if isnan(array_id)
        error("SLURM_ARRAY_TASK_ID is not numeric: %s", array_id_str);
    end
end

fprintf("Running SLURM array_id = %d\n", array_id);

%% ------------------------------------------------------------
% 1. Resolve project root
%% ------------------------------------------------------------

this_file = mfilename("fullpath");
matlab_dir = fileparts(this_file);

% File is located in:
% MAIN_PROJECT/04_Matlab_&_Simulink/conditional_sampling_v2
%
% So:
% fileparts(matlab_dir)            -> MAIN_PROJECT/04_Matlab_&_Simulink
% fileparts(fileparts(matlab_dir)) -> MAIN_PROJECT

ROOT = fileparts(fileparts(matlab_dir));

fprintf("MATLAB runner directory:\n%s\n", matlab_dir);
fprintf("Project root:\n%s\n", ROOT);

%% ------------------------------------------------------------
% 2. Campaign paths
%% ------------------------------------------------------------

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

%% ------------------------------------------------------------
% 3. Read manifest robustly
%% ------------------------------------------------------------

% Important:
% MATLAB sometimes changes CSV header names.
% So we do NOT rely on manifest.array_id, manifest.samples_path, etc.
% We read by column position:
%   column 1 = array_id
%   column 2 = samples_path
%   column 3 = results_path

manifest = readtable(manifest_path, ...
    "TextType", "string", ...
    "VariableNamingRule", "preserve");

fprintf("Manifest variable names detected by MATLAB:\n");
disp(manifest.Properties.VariableNames);

if width(manifest) < 3
    error("Manifest must have at least 3 columns: array_id, samples_path, results_path.");
end

manifest_array_ids = manifest{:, 1};

% If MATLAB reads array_id as string/cell, convert it.
if iscell(manifest_array_ids)
    manifest_array_ids = str2double(string(manifest_array_ids));
elseif isstring(manifest_array_ids)
    manifest_array_ids = str2double(manifest_array_ids);
elseif ischar(manifest_array_ids)
    manifest_array_ids = str2double(string(manifest_array_ids));
end

idx = find(manifest_array_ids == array_id, 1);

if isempty(idx)
    fprintf("Available manifest array IDs:\n");
    disp(manifest_array_ids(:)');
    error("array_id=%d not found in manifest.", array_id);
end

samples_path = manifest{idx, 2};
results_path = manifest{idx, 3};

% Convert paths safely to char
if iscell(samples_path)
    samples_path = samples_path{1};
end

if iscell(results_path)
    results_path = results_path{1};
end

samples_path = char(string(samples_path));
results_path = char(string(results_path));

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
% 4. Load chunk
%% ------------------------------------------------------------

samples = readtable(samples_path, ...
    "TextType", "string", ...
    "VariableNamingRule", "preserve");

fprintf("Loaded chunk with %d rows and %d columns.\n", ...
    height(samples), width(samples));

if height(samples) == 0
    warning("Samples chunk is empty. Writing empty result table.");
    writetable(samples, results_path);
    return;
end

% Validate simulation_id robustly
sample_var_names = string(samples.Properties.VariableNames);

if ~ismember("simulation_id", sample_var_names)
    fprintf("Sample variable names detected by MATLAB:\n");
    disp(samples.Properties.VariableNames);
    error("Samples chunk is missing required column: simulation_id");
end

%% ------------------------------------------------------------
% 5. Load Simulink model
%% ------------------------------------------------------------

model = "MyComplexModel_V13R2023a";

fprintf("Loading Simulink model: %s\n", model);

try
    load_system(model);
catch ME
    fprintf("Failed to load model: %s\n", model);
    rethrow(ME);
end

%% ------------------------------------------------------------
% 6. Run rows
%% ------------------------------------------------------------

all_results = table();

chunk_start_time = tic;

for i = 1:height(samples)

    row_start_time = tic;

    simulation_id = samples.simulation_id(i);

    % Convert if MATLAB reads it strangely
    if iscell(simulation_id)
        simulation_id = simulation_id{1};
    end

    simulation_id_num = str2double(string(simulation_id));

    if isnan(simulation_id_num)
        simulation_id_num = i;
    end

    fprintf("\n------------------------------------------------------------\n");
    fprintf("Chunk array_id=%d | row %d/%d | simulation_id=%d\n", ...
        array_id, i, height(samples), simulation_id_num);
    fprintf("------------------------------------------------------------\n");

    sample_row = samples(i, :);

    try
        result_row = run_one_case_from_config(sample_row, model);
    catch ME
        % Safety net. Ideally run_one_case_from_config already catches sim errors.
        fprintf("Unexpected error outside run_one_case_from_config for simulation_id=%d\n", ...
            simulation_id_num);

        full_error = getReport(ME, "extended", "hyperlinks", "off");
        fprintf("%s\n", full_error);

        result_row = sample_row;
        result_row.LAP_real = NaN;
        result_row.RAP_real = NaN;
        result_row.SAP_real = NaN;
        result_row.DAP_real = NaN;
        result_row.sPAP_real = NaN;
        result_row.dPAP_real = NaN;
        result_row.EDV_LV_real = NaN;
        result_row.ESV_LV_real = NaN;
        result_row.EDV_RV_real = NaN;
        result_row.ESV_RV_real = NaN;
        result_row.CO_real = NaN;
        result_row.simulation_status = "failed_outer_trycatch";
        result_row.error_message = string(full_error);
    end

    all_results = [all_results; result_row];

    elapsed_row = toc(row_start_time);

    fprintf("Finished simulation_id=%d in %.2f seconds.\n", ...
        simulation_id_num, elapsed_row);

    % Save partial progress every 5 simulations and at the end.
    if mod(i, 5) == 0 || i == height(samples)
        writetable(all_results, results_path);
        fprintf("Partial results saved to:\n%s\n", results_path);
    end
end

%% ------------------------------------------------------------
% 7. Final save
%% ------------------------------------------------------------

writetable(all_results, results_path);

elapsed_chunk = toc(chunk_start_time);

%% ------------------------------------------------------------
% 8. Summary
%% ------------------------------------------------------------

fprintf("\n============================================================\n");
fprintf("Finished chunk array_id=%d\n", array_id);
fprintf("Rows processed: %d\n", height(samples));
fprintf("Elapsed chunk time: %.2f seconds / %.2f minutes\n", ...
    elapsed_chunk, elapsed_chunk / 60);
fprintf("Results saved to:\n%s\n", results_path);

if ismember("simulation_status", string(all_results.Properties.VariableNames))
    fprintf("\nSimulation status counts:\n");

    statuses = string(all_results.simulation_status);
    unique_statuses = unique(statuses);

    for s = 1:numel(unique_statuses)
        status = unique_statuses(s);
        count = sum(statuses == status);
        fprintf("  %s: %d\n", status, count);
    end
end

fprintf("End time: %s\n", string(datetime("now")));
fprintf("============================================================\n");

end