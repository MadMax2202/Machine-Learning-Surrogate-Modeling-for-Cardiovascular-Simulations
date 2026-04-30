function run_parallel_expansion_stress_test_pediatric_noVAD_linear(samples_path, results_path)
%RUN_PARALLEL_EXPANSION_STRESS_TEST_PEDIATRIC_NOVAD_LINEAR
%
% Runs one chunk sequentially.
% Parallelism is handled externally by Python launching multiple MATLAB processes.
% Does NOT require Parallel Computing Toolbox.
%
% Inputs:
%   samples_path : CSV file containing one chunk of sample rows
%   results_path : CSV file where this chunk's results are saved
%
% This wrapper calls:
%   run_one_case_pediatric_noVAD_linear(sample_row, model)

    clearvars -except samples_path results_path;
    clc;

    fprintf("\nStarting sequential MATLAB chunk stress test...\n");

    %% ------------------------------------------------------------
    % 1. Model
    %% ------------------------------------------------------------

    model = 'MyComplexModel_V13R2023a';

    model_file = fullfile(pwd, [model '.slx']);

    if ~isfile(model_file)
        error("Model file not found: %s", model_file);
    end

    load_system(model);

    %% ------------------------------------------------------------
    % 2. Read samples
    %% ------------------------------------------------------------

    if ~isfile(samples_path)
        error("Samples file not found: %s", samples_path);
    end

    samples = readtable(samples_path);
    n_cases = height(samples);

    fprintf("Samples file: %s\n", samples_path);
    fprintf("Results file: %s\n", results_path);
    fprintf("Number of simulations in chunk: %d\n", n_cases);

    results_folder = fileparts(results_path);

    if ~exist(results_folder, 'dir')
        mkdir(results_folder);
    end

    %% ------------------------------------------------------------
    % 3. Run simulations
    %% ------------------------------------------------------------

    result_cells = cell(n_cases, 1);

    for i = 1:n_cases

        sample_row = samples(i, :);

        fprintf("\nRunning %d/%d | simulation_id = %d | expansion_factor = %.2f\n", ...
            i, n_cases, sample_row.simulation_id, sample_row.expansion_factor);

        try
            raw_result = run_one_case_pediatric_noVAD_linear(sample_row, model);
            result_cells{i} = normalise_success_result(sample_row, raw_result);

        catch ME
            fprintf("Wrapper-level failure for simulation_id = %d\n", sample_row.simulation_id);
            fprintf("%s\n", getReport(ME, 'extended', 'hyperlinks', 'off'));

            result_cells{i} = make_failed_result(sample_row, ME);
        end

        %% --------------------------------------------------------
        % 4. Checkpoint every 5 simulations
        %% --------------------------------------------------------

        if mod(i, 5) == 0 || i == n_cases
            partial_results = vertcat(result_cells{1:i});
            writetable(partial_results, results_path);

            n_failed_partial = sum(partial_results.simulation_status == "failed");
            n_success_partial = sum(partial_results.simulation_status == "success");

            fprintf("\nCheckpoint saved after %d/%d simulations.\n", i, n_cases);
            fprintf("Partial successes: %d\n", n_success_partial);
            fprintf("Partial failures: %d\n", n_failed_partial);
            fprintf("Checkpoint file: %s\n", results_path);
        end
    end

    %% ------------------------------------------------------------
    % 5. Final save
    %% ------------------------------------------------------------

    results = vertcat(result_cells{:});
    writetable(results, results_path);

    n_failed = sum(results.simulation_status == "failed");
    n_success = sum(results.simulation_status == "success");

    fprintf("\nFinished chunk.\n");
    fprintf("Successful simulations: %d\n", n_success);
    fprintf("Failed simulations: %d\n", n_failed);
    fprintf("Failure rate: %.2f %%\n", 100 * n_failed / height(results));
    fprintf("Results saved to: %s\n", results_path);

end


%% ========================================================================
% Helper: expected output variables
%% ========================================================================

function output_vars = get_output_vars()

    output_vars = {
        'LAP_real'
        'RAP_real'
        'SAP_real'
        'DAP_real'
        'sPAP_real'
        'dPAP_real'
        'EDV_LV_real'
        'ESV_LV_real'
        'EDV_RV_real'
        'ESV_RV_real'
        'CO_real'
    };

end


%% ========================================================================
% Helper: normalize successful one-case result
%% ========================================================================

function result_row = normalise_success_result(sample_row, raw_result)

    output_vars = get_output_vars();

    if istable(raw_result)
        result_row = raw_result;
    elseif isstruct(raw_result)
        result_row = struct2table(raw_result);
    else
        error("One-case runner returned unsupported type: %s", class(raw_result));
    end

    if height(result_row) ~= 1
        error("One-case runner must return exactly one result row.");
    end

    sample_vars = sample_row.Properties.VariableNames;

    % Add sample columns back if missing, especially expansion_factor.
    for k = 1:numel(sample_vars)
        name = sample_vars{k};

        if ~ismember(name, result_row.Properties.VariableNames)
            result_row.(name) = sample_row.(name);
        end
    end

    % Add missing output columns as NaN.
    for k = 1:numel(output_vars)
        name = output_vars{k};

        if ~ismember(name, result_row.Properties.VariableNames)
            result_row.(name) = NaN;
        end
    end

    % Do NOT overwrite simulation_status if the one-case function already set it.
    if ~ismember('simulation_status', result_row.Properties.VariableNames)
        result_row.simulation_status = "success";
    end

    if ~ismember('error_message', result_row.Properties.VariableNames)
        result_row.error_message = "";
    end

    result_row = reorder_result_columns(result_row, sample_vars, output_vars);

end


%% ========================================================================
% Helper: create failed row if wrapper itself crashes
%% ========================================================================

function result_row = make_failed_result(sample_row, ME)

    output_vars = get_output_vars();

    result_row = sample_row;

    for k = 1:numel(output_vars)
        result_row.(output_vars{k}) = NaN;
    end

    result_row.simulation_status = "failed";
    result_row.error_message = string(getReport(ME, 'extended', 'hyperlinks', 'off'));

    sample_vars = sample_row.Properties.VariableNames;

    result_row = reorder_result_columns(result_row, sample_vars, output_vars);

end


%% ========================================================================
% Helper: consistent column order
%% ========================================================================

function result_row = reorder_result_columns(result_row, sample_vars, output_vars)

    desired_order = [
        sample_vars(:)
        output_vars(:)
        {'simulation_status'}
        {'error_message'}
    ];

    result_row = result_row(:, desired_order);

end