function run_10k_supercomputer_pediatric_noVAD_linear(samples_path, results_path)

    clearvars -except samples_path results_path;
    clc;

    fprintf("\nStarting 10k supercomputer MATLAB chunk with resume support...\n");

    model = 'MyComplexModel_V13R2023a';
    model_file = fullfile(pwd, [model '.slx']);

    if ~isfile(model_file)
        error("Model file not found: %s", model_file);
    end

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

    if isfile(results_path)
        try
            existing_results = readtable(results_path);

            if ismember("simulation_id", existing_results.Properties.VariableNames)
                completed_ids = existing_results.simulation_id;
                fprintf("Existing result file found with %d rows.\n", height(existing_results));
            else
                warning("Existing result file has no simulation_id column. Ignoring it.");
                existing_results = table();
                completed_ids = [];
            end
        catch ME
            warning("Could not read existing results file. Starting empty. Error: %s", ME.message);
            existing_results = table();
            completed_ids = [];
        end
    else
        existing_results = table();
        completed_ids = [];
        fprintf("No existing result file found. Starting new chunk.\n");
    end

    remaining_mask = ~ismember(samples.simulation_id, completed_ids);
    remaining_samples = samples(remaining_mask, :);
    n_remaining = height(remaining_samples);

    fprintf("Already completed simulations: %d/%d\n", n_cases - n_remaining, n_cases);
    fprintf("Remaining simulations to run: %d/%d\n", n_remaining, n_cases);

    if n_remaining == 0
        fprintf("Chunk already complete. Nothing to do.\n");
        return;
    end

    load_system(model);

    new_result_cells = cell(n_remaining, 1);

    for i = 1:n_remaining

        sample_row = remaining_samples(i, :);

        fprintf("\nRunning remaining %d/%d | simulation_id = %d\n", ...
            i, n_remaining, sample_row.simulation_id);

        try
            raw_result = run_one_case_pediatric_noVAD_linear(sample_row, model);
            new_result_cells{i} = normalise_success_result(sample_row, raw_result);

        catch ME
            fprintf("Wrapper-level failure for simulation_id = %d\n", sample_row.simulation_id);
            fprintf("%s\n", getReport(ME, 'extended', 'hyperlinks', 'off'));

            new_result_cells{i} = make_failed_result(sample_row, ME);
        end

        current_new_results = vertcat(new_result_cells{1:i});

        if isempty(existing_results)
            combined_results = current_new_results;
        else
            combined_results = [existing_results; current_new_results];
        end

        combined_results = sortrows(combined_results, "simulation_id");

        writetable(combined_results, results_path);

        if mod(i, 5) == 0 || i == n_remaining
            n_failed_partial = sum(combined_results.simulation_status == "failed");
            n_success_partial = sum(combined_results.simulation_status == "success");

            fprintf("\nCheckpoint saved.\n");
            fprintf("Total rows now: %d/%d\n", height(combined_results), n_cases);
            fprintf("Partial successes: %d\n", n_success_partial);
            fprintf("Partial failures: %d\n", n_failed_partial);
            fprintf("Checkpoint file: %s\n", results_path);
        end
    end

    final_results = readtable(results_path);
    final_results = sortrows(final_results, "simulation_id");
    writetable(final_results, results_path);

    n_failed = sum(final_results.simulation_status == "failed");
    n_success = sum(final_results.simulation_status == "success");

    fprintf("\nFinished/resumed 10k supercomputer chunk.\n");
    fprintf("Rows in final chunk file: %d/%d\n", height(final_results), n_cases);
    fprintf("Successful simulations: %d\n", n_success);
    fprintf("Failed simulations: %d\n", n_failed);
    fprintf("Failure rate: %.2f %%\n", 100 * n_failed / height(final_results));
    fprintf("Results saved to: %s\n", results_path);

end


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

    for k = 1:numel(sample_vars)
        name = sample_vars{k};

        if ~ismember(name, result_row.Properties.VariableNames)
            result_row.(name) = sample_row.(name);
        end
    end

    for k = 1:numel(output_vars)
        name = output_vars{k};

        if ~ismember(name, result_row.Properties.VariableNames)
            result_row.(name) = NaN;
        end
    end

    if ~ismember('simulation_status', result_row.Properties.VariableNames)
        result_row.simulation_status = "success";
    end

    if ~ismember('error_message', result_row.Properties.VariableNames)
        result_row.error_message = "";
    end

    result_row = reorder_result_columns(result_row, sample_vars, output_vars);

end


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


function result_row = reorder_result_columns(result_row, sample_vars, output_vars)

    desired_order = [
        sample_vars(:)
        output_vars(:)
        {'simulation_status'}
        {'error_message'}
    ];

    existing_order = desired_order(ismember(desired_order, result_row.Properties.VariableNames));

    result_row = result_row(:, existing_order);

end
