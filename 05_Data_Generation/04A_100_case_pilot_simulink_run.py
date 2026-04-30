import subprocess
from pathlib import Path

"""
Runs MATLAB once. The loop over simulation cases is inside MATLAB,
because starting MATLAB separately for each case would be too slow.
"""

project_dir = Path(__file__).resolve().parent
matlab_dir = (project_dir / "../04_Matlab_&_Simulink").resolve()

matlab_script = "run_pilot_100_cases_pediatric_noVAD_linear"

matlab_command = (
    f"cd('{matlab_dir.as_posix()}'); "
    f"addpath('{matlab_dir.as_posix()}'); "
    f"{matlab_script};"
)

cmd = [
    "matlab",
    "-batch",
    matlab_command
]

result = subprocess.run(
    cmd,
    cwd=project_dir,
    capture_output=True,
    text=True
)

print("MATLAB STDOUT:")
print(result.stdout)

print("MATLAB STDERR:")
print(result.stderr)

if result.returncode != 0:
    raise RuntimeError("MATLAB simulation script failed.")

print("MATLAB finished successfully.")