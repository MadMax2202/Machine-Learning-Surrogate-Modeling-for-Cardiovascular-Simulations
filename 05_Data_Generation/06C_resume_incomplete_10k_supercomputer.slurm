#!/bin/bash
#SBATCH --job-name=ped_dcm_10k_resume
#SBATCH --array=1-200%20
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=24G
#SBATCH --time=03:00:00
#SBATCH --output=../01_Data/simulation_results/pediatric_dcm_patient_01/stage_1_10k_supercomputer_v2/logs/resume_%A_%a.out
#SBATCH --error=../01_Data/simulation_results/pediatric_dcm_patient_01/stage_1_10k_supercomputer_v2/logs/resume_%A_%a.err

set -euo pipefail

cd "$SLURM_SUBMIT_DIR"

module purge
module load python/3.12.8-gcc-12.2.0-4y5tbpr
module load Matlab/R2024b

ROOT="$(cd .. && pwd)"
source "$ROOT/venv/bin/activate"

PATIENT_ID="pediatric_dcm_patient_01"
CAMPAIGN_NAME="stage_1_10k_supercomputer_v2"

INCOMPLETE_LIST="$ROOT/01_Data/simulation_results/$PATIENT_ID/$CAMPAIGN_NAME/incomplete_chunks.txt"
MANIFEST="$ROOT/01_Data/generated_samples/$PATIENT_ID/$CAMPAIGN_NAME/${PATIENT_ID}_${CAMPAIGN_NAME}_manifest.csv"

if [ ! -f "$INCOMPLETE_LIST" ]; then
    echo "ERROR: incomplete_chunks.txt not found: $INCOMPLETE_LIST"
    exit 1
fi

if [ ! -f "$MANIFEST" ]; then
    echo "ERROR: Manifest not found: $MANIFEST"
    exit 1
fi

N_INCOMPLETE=$(wc -l < "$INCOMPLETE_LIST")

if [ "$SLURM_ARRAY_TASK_ID" -gt "$N_INCOMPLETE" ]; then
    echo "Task $SLURM_ARRAY_TASK_ID above incomplete count $N_INCOMPLETE. Exiting."
    exit 0
fi

CHUNK_ID=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$INCOMPLETE_LIST")
LINE=$((CHUNK_ID + 1))

SAMPLES_PATH=$(awk -F',' -v line="$LINE" 'NR==line {print $2}' "$MANIFEST")
RESULTS_PATH=$(awk -F',' -v line="$LINE" 'NR==line {print $3}' "$MANIFEST")

if [ -z "$SAMPLES_PATH" ] || [ -z "$RESULTS_PATH" ]; then
    echo "ERROR: Could not read paths from manifest."
    echo "CHUNK_ID=$CHUNK_ID"
    echo "LINE=$LINE"
    exit 1
fi

if [ ! -f "$SAMPLES_PATH" ]; then
    echo "ERROR: Samples file not found: $SAMPLES_PATH"
    exit 1
fi

mkdir -p "$ROOT/01_Data/simulation_results/$PATIENT_ID/$CAMPAIGN_NAME/logs"
mkdir -p "$ROOT/01_Data/simulation_results/$PATIENT_ID/$CAMPAIGN_NAME/chunks"

echo "=================================================="
echo "RESUME JOB"
echo "SLURM_JOB_ID: $SLURM_JOB_ID"
echo "SLURM_ARRAY_TASK_ID: $SLURM_ARRAY_TASK_ID"
echo "CHUNK_ID: $CHUNK_ID"
echo "Host: $(hostname)"
echo "Start time: $(date)"
echo "Samples: $SAMPLES_PATH"
echo "Results: $RESULTS_PATH"
echo "=================================================="

cd "$ROOT/04_Matlab_&_Simulink"

matlab -singleCompThread -batch "run_10k_supercomputer_pediatric_noVAD_linear('$SAMPLES_PATH', '$RESULTS_PATH');"

echo "=================================================="
echo "Finished resumed chunk $CHUNK_ID"
echo "End time: $(date)"
echo "=================================================="
