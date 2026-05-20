07_Conditional_Sampling_Strategy

07_Conditional_Sampling_Strategy/
├── 07A_generate_100_patients.py
├── 07B_generate_10k_conditional_tunable_dataset.py
├── 07C_run_10k_conditional_sampling_cluster.slurm
├── 07D_merge_conditional_sampling_chunks.py
├── 07E_analyse_conditional_sampling_physiology.ipynb
└── 07F_baseline_models_conditional_sampling.ipynb

The logic is good:

100 conditional patients
× 100 tunable variations
= 10,000 simulations

The key advantages:

You stop overfitting to one patient.
The dataset becomes population-level.
Your tightened bounds are reused as physiologically informed priors.
You can test whether the current single-patient bounds generalize.
The 10k run becomes a pilot before the real 100k/1M-scale run.

Two important safeguards I’d add:

Patient-level split later
Do not randomly split the 10k rows. Since each patient has 100 variations, random split creates leakage.

Use:

train patients ≠ validation patients ≠ test patients

Example:

70 patients train
15 patients validation
15 patients test
Keep both full and filtered datasets
Do not only save physiologically realistic rows. Save:
FULL_10k.csv
PHYSIOLOGICAL_ONLY.csv
NON_PHYSIOLOGICAL.csv

The failed/non-physiological rows are still useful for:

classification,
boundary detection,
failure prediction,
tree-based rule extraction.

I’d also add one extra file:

07E2_update_population_tunable_bounds.py

This would use the physiological subset from the conditional sampling run to generate:

01_Data/patient_configs/pediatric_dcm_patient_01/stage_2_population_tunable_bounds.csv

Overall: yes, this is the right direction. It turns the project from “single-patient parameter search” into a proper population-conditioned surrogate modeling pipeline.