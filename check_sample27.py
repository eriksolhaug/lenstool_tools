#!/usr/bin/env python3
"""
Check if sample_00027 corresponds correctly to bayes.dat row 27
"""

from pathlib import Path
import re

# Read sample 27 from bayes.dat
bayes_file = Path('/Users/eriksolhaug/Research/Tools/lenstool_tools/dec19a_model_solhaug/input/bayes.dat')
with open(bayes_file, 'r') as f:
    lines = f.readlines()

# Get param names from comments
param_names = []
for line in lines:
    if line.startswith('#'):
        param_names.append(line[1:].strip())
    else:
        break

print("Parameter mapping from bayes.dat:")
for i, name in enumerate(param_names):
    print(f"  [{i:2d}] {name}")

# Get row 27 (sample number 3 in the printout, which is 3rd data row)
# But we need to count - the printout showed "3" as first column
# Let me count properly: header is 30 lines, then data starts
data_rows = [l for l in lines if not l.startswith('#')]
print(f"\nTotal data rows: {len(data_rows)}")

# Row 27 should be index 26 (0-indexed)
row_27 = data_rows[26].strip().split()
print(f"\nBayes.dat row 27 (sample index 26):")
print(f"  Sample number: {row_27[0]}")
print(f"  Values: {len(row_27)-1} values")

row_27_values = [float(x) for x in row_27[1:]]

# Now show the O1 parameters
print("\nO1 parameters from row 27:")
print(f"  [0] {param_names[0]}: {row_27_values[0]}")  # x
print(f"  [1] {param_names[1]}: {row_27_values[1]}")  # y  
print(f"  [2] {param_names[2]}: {row_27_values[2]}")  # emass
print(f"  [3] {param_names[3]}: {row_27_values[3]}")  # theta
print(f"  [4] {param_names[4]}: {row_27_values[4]}")  # rc
print(f"  [5] {param_names[5]}: {row_27_values[5]}")  # sigma

# Read sample_00027_z1.524.par
sample_file = Path('/Users/eriksolhaug/Research/Tools/lenstool_tools/dec19a_model_solhaug/sample_input/sample_00027_z1.524.par')
with open(sample_file, 'r') as f:
    sample_content = f.read()

# Extract O1 parameters
o1_x = re.search(r'potentiel O1.*?x_centre\s+([-\d.]+)', sample_content, re.DOTALL)
o1_y = re.search(r'potentiel O1.*?y_centre\s+([-\d.]+)', sample_content, re.DOTALL)
o1_ellip = re.search(r'potentiel O1.*?ellipticite\s+([-\d.]+)', sample_content, re.DOTALL)
o1_angle = re.search(r'potentiel O1.*?angle_pos\s+([-\d.]+)', sample_content, re.DOTALL)
o1_rc = re.search(r'potentiel O1.*?core_radius_kpc\s+([-\d.]+)', sample_content, re.DOTALL)
o1_sigma = re.search(r'potentiel O1.*?v_disp\s+([-\d.]+)', sample_content, re.DOTALL)

print("\nValues in sample_00027_z1.524.par O1:")
if o1_x: print(f"  x_centre: {o1_x.group(1)}")
if o1_y: print(f"  y_centre: {o1_y.group(1)}")
if o1_ellip: print(f"  ellipticite: {o1_ellip.group(1)}")
if o1_angle: print(f"  angle_pos: {o1_angle.group(1)}")
if o1_rc: print(f"  core_radius_kpc: {o1_rc.group(1)}")
if o1_sigma: print(f"  v_disp: {o1_sigma.group(1)}")

print("\n" + "="*80)
print("COMPARISON:")
print("="*80)
if o1_x:
    expected_x = row_27_values[0]
    actual_x = float(o1_x.group(1))
    match_x = "✓ MATCH" if abs(expected_x - actual_x) < 0.001 else "✗ MISMATCH"
    print(f"x_centre: expected {expected_x:12.6f}, got {actual_x:12.6f} {match_x}")

if o1_y:
    expected_y = row_27_values[1]
    actual_y = float(o1_y.group(1))
    match_y = "✓ MATCH" if abs(expected_y - actual_y) < 0.001 else "✗ MISMATCH"
    print(f"y_centre: expected {expected_y:12.6f}, got {actual_y:12.6f} {match_y}")

if o1_rc:
    expected_rc = row_27_values[4] * 0.00155  # Convert arcsec to kpc
    actual_rc = float(o1_rc.group(1))
    match_rc = "✓ MATCH" if abs(expected_rc - actual_rc) < 0.001 else "✗ MISMATCH"
    print(f"rc (kpc): expected {expected_rc:12.6f}, got {actual_rc:12.6f} {match_rc}")

if o1_sigma:
    expected_sigma = row_27_values[5]
    actual_sigma = float(o1_sigma.group(1))
    match_sigma = "✓ MATCH" if abs(expected_sigma - actual_sigma) < 0.01 else "✗ MISMATCH"
    print(f"sigma: expected {expected_sigma:12.6f}, got {actual_sigma:12.6f} {match_sigma}")
