#!/usr/bin/env python
import re
import random
import sys
sys.path.insert(0, '/Users/eriksolhaug/Research/Tools/lenstool_tools')
from lenstool_tools.samples import read_bayes_dat

# Load bayes.dat
param_names, samples = read_bayes_dat('dec19a_model_solhaug/input/bayes.dat')

# Get the selected indices with seed 42 (same as config)
random.seed(42)
selected_indices = sorted(random.sample(range(4020), 100))

print(f"First 10 selected indices: {selected_indices[:10]}")
print()

# Check a few from the selected samples
check_positions = [0, 1, 5, 49, 99]

for pos in check_positions:
    bayes_idx = selected_indices[pos]
    sample_num = bayes_idx + 1  # Sample file numbering is 1-based
    sample_file = f'sample_{sample_num:05d}_z1.524.par'
    
    bayes_row = samples[bayes_idx]
    
    try:
        with open(f'dec19a_model_solhaug/sample_input/{sample_file}') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"File not found: {sample_file}")
        continue
        
    # Extract O1 parameters
    x_match = re.search(r'potentiel\s+O1.*?x\s+([\d.-]+)', content, re.DOTALL)
    y_match = re.search(r'potentiel\s+O1.*?y\s+([\d.-]+)', content, re.DOTALL)
    emass_match = re.search(r'potentiel\s+O1.*?emass\s+([\d.-]+)', content, re.DOTALL)
    
    if x_match and y_match and emass_match:
        sample_x = float(x_match.group(1))
        sample_y = float(y_match.group(1))
        sample_emass = float(emass_match.group(1))
        
        bayes_x = bayes_row[2]
        bayes_y = bayes_row[3]
        bayes_emass = bayes_row[4]
        
        x_check = 'OK' if abs(sample_x - bayes_x) < 0.0001 else 'FAIL'
        y_check = 'OK' if abs(sample_y - bayes_y) < 0.0001 else 'FAIL'
        e_check = 'OK' if abs(sample_emass - bayes_emass) < 0.0001 else 'FAIL'
        
        print(f'Position {pos} → bayes row {bayes_idx} → {sample_file}:')
        print(f'  x:     {sample_x:.6f} vs {bayes_x:.6f} {x_check}')
        print(f'  y:     {sample_y:.6f} vs {bayes_y:.6f} {y_check}')
        print(f'  emass: {sample_emass:.6f} vs {bayes_emass:.6f} {e_check}')
        print()
