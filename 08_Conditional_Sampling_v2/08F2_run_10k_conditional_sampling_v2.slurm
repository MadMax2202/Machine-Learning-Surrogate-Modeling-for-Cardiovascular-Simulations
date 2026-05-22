#!/bin/bash
#SBATCH --job-name=ped_dcm_cond_v2_10k
#SBATCH --array=1-198%50
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=24G
#SBATCH --time=08:00:00
#SBATCH --output=../01_Data/Conditional_Sampling_v2/simulation_results/conditional_sampling_100_patients_100_variations_v2/logs/slurm_%A_%a.out
#SBATCH --error=../01_Data/Conditional_Sampling_v2/simulation_results/conditional_sampling_100_patients_100_variations_v2/logs/slurm_%A_%a.err

set -euo pipefail

# This assumes you submit from:
# MAIN_PROJECT/08_Conditional_Sampling_v2
cd "$SLURM_SUBMIT_DIR"

module purge
module load python/3.12.8-gcc-12.2.0-4y5tbpr
module load Matlab/R2024b

ROOT="$(cd .. && pwd)"

if [ -f "$ROOT/venv/bin/activate" ]; then
    source "$ROOT/venv/bin/activate"
else
    echo "WARNING: venv not found at $ROOT/venv/bin/activate"
    echo "Continuing without activating venv."
fi

CAMPAIGN_NAME="conditional_sampling_100_patients_100_variations_v2"

MANIFEST="$ROOT/01_Data/Conditional_Sampling_v2/generated_samples/$CAMPAIGN_NAME/${CAMPAIGN_NAME}_manifest.csv"

RESULTS_DIR="$ROOT/01_Data/Conditional_Sampling_v2/simulation_results/$CAMPAIGN_NAME"
LOGS_DIR="$RESULTS_DIR/logs"
CHUNKS_RESULTS_DIR="$RESULTS_DIR/chunks"

if [ ! -f "$MANIFEST" ]; then
    echo "ERROR: Manifest not found:"
    echo "$MANIFEST"
    exit 1
fi

mkdir -p "$LOGS_DIR"
mkdir -p "$CHUNKS_RESULTS_DIR"

LINE=$((SLURM_ARRAY_TASK_ID + 1))

SAMPLES_PATH=$(awk -F',' -v line="$LINE" 'NR==line {print $2}' "$MANIFEST")
RESULTS_PATH=$(awk -F',' -v line="$LINE" 'NR==line {print $3}' "$MANIFEST")

if [ -z "$SAMPLES_PATH" ] || [ -z "$RESULTS_PATH" ]; then
    echo "ERROR: Could not read paths from manifest."
    echo "SLURM_ARRAY_TASK_ID=$SLURM_ARRAY_TASK_ID"
    echo "LINE=$LINE"
    exit 1
fi

if [ ! -f "$SAMPLES_PATH" ]; then
    echo "ERROR: Samples file not found:"
    echo "$SAMPLES_PATH"
    exit 1
fi

echo "=================================================="
echo "CONDITIONAL SAMPLING V2 10K CLUSTER RUN"
echo "SLURM_JOB_ID: $SLURM_JOB_ID"
echo "SLURM_ARRAY_JOB_ID: ${SLURM_ARRAY_JOB_ID:-none}"
echo "SLURM_ARRAY_TASK_ID: $SLURM_ARRAY_TASK_ID"
echo "Host: $(hostname)"
echo "Start time: $(date)"
echo "ROOT: $ROOT"
echo "Manifest: $MANIFEST"
echo "Samples: $SAMPLES_PATH"
echo "Results: $RESULTS_PATH"
echo "MATLAB folder: $ROOT/04_Matlab_&_Simulink/conditional_sampling_v2"
echo "=================================================="

cd "$ROOT/04_Matlab_&_Simulink/conditional_sampling_v2"

# The manifest-based MATLAB function reads SLURM_ARRAY_TASK_ID itself.
matlab -singleCompThread -batch "run_chunk_conditional_sampling_from_manifest;"

echo "=================================================="
echo "Finished conditional sampling V2 task $SLURM_ARRAY_TASK_ID"
echo "End time: $(date)"
echo "=================================================="