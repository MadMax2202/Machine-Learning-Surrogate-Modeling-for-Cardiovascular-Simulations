import subprocess
from pathlib import Path

"""
04B_run_bounds_stress_test_simulink.py

Launch MATLAB once to run the bounds stress-test simulations.
The loop over stress-test cases is done in MATLAB for speed.


43secs per sim --> 100 000 sims serial computation -> 49 days 
--> 10000 sims serial -> 5 days 
--> 10000 sims parallel (8 cores ) -> 0.6 days 
--> 100000 sims parallel (8 cores) -> 6.25 days 
"""

project_dir = Path(__file__).resolve().parent
matlab_dir = (project_dir / "../04_Matlab_&_Simulink").resolve()

matlab_script = "run_bounds_stress_test_pediatric_noVAD_linear"

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
    raise RuntimeError("MATLAB bounds stress-test script failed.")

print("MATLAB bounds stress-test finished successfully.")