#!/bin/bash
#SBATCH --job-name=ped_dcm_10k_v2
#SBATCH --array=1-200%50
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=../01_Data/simulation_results/pediatric_dcm_patient_01/stage_1_10k_supercomputer_v2/logs/slurm_%A_%a.out
#SBATCH --error=../01_Data/simulation_results/pediatric_dcm_patient_01/stage_1_10k_supercomputer_v2/logs/slurm_%A_%a.err

cd "$SLURM_SUBMIT_DIR"

module purge
module load matlab

ROOT="$(cd .. && pwd)"

PATIENT_ID="pediatric_dcm_patient_01"
CAMPAIGN_NAME="stage_1_10k_supercomputer_v2"

MANIFEST="$ROOT/01_Data/generated_samples/$PATIENT_ID/$CAMPAIGN_NAME/${PATIENT_ID}_${CAMPAIGN_NAME}_manifest.csv"

LINE=$((SLURM_ARRAY_TASK_ID + 1))

SAMPLES_PATH=$(awk -F',' -v line="$LINE" 'NR==line {print $2}' "$MANIFEST")
RESULTS_PATH=$(awk -F',' -v line="$LINE" 'NR==line {print $3}' "$MANIFEST")

echo "SLURM_JOB_ID: $SLURM_JOB_ID"
echo "SLURM_ARRAY_TASK_ID: $SLURM_ARRAY_TASK_ID"
echo "Samples: $SAMPLES_PATH"
echo "Results: $RESULTS_PATH"

cd "$ROOT/04_Matlab_&_Simulink"

matlab -batch "run_10k_supercomputer_pediatric_noVAD_linear('$SAMPLES_PATH', '$RESULTS_PATH');"