#!/usr/bin/env python
import re
import sys
sys.path.insert(0, '/Users/eriksolhaug/Research/Tools/lenstool_tools')
from lenstool_tools.samples import read_bayes_dat

# Load bayes.dat using the same method as generate_samples
param_names, samples = read_bayes_dat('dec19a_model_solhaug/input/bayes.dat')

# Check a few samples
samples_to_check = ['sample_00001_z1.524.par', 'sample_00027_z1.524.par', 'sample_00100_z1.524.par', 'sample_03986_z1.524.par']

for sample_file in samples_to_check:
    sample_num = int(sample_file.split('_')[1])
    bayes_row = samples[sample_num - 1]  # 0-indexed
    
    with open(f'dec19a_model_solhaug/sample_input/{sample_file}') as f:
        content = f.read()
        
    # Extract O1 parameters from sample file
    x_match = re.search(r'potentiel\s+O1.*?x\s+([\d.-]+)', content, re.DOTALL)
    y_match = re.search(r'potentiel\s+O1.*?y\s+([\d.-]+)', content, re.DOTALL)
    emass_match = re.search(r'potentiel\s+O1.*?emass\s+([\d.-]+)', content, re.DOTALL)
    
    if x_match and y_match and emass_match:
        sample_x = float(x_match.group(1))
        sample_y = float(y_match.group(1))
        sample_emass = float(emass_match.group(1))
        
        # From bayes.dat: column 0=Nsample, 1=lhood, 2=x, 3=y, 4=emass
        bayes_x = bayes_row[2]
        bayes_y = bayes_row[3]
        bayes_emass = bayes_row[4]
        
        x_check = 'OK' if abs(sample_x - bayes_x) < 0.0001 else 'FAIL'
        y_check = 'OK' if abs(sample_y - bayes_y) < 0.0001 else 'FAIL'
        e_check = 'OK' if abs(sample_emass - bayes_emass) < 0.0001 else 'FAIL'
        
        print(f'{sample_file} (row {sample_num}):')
        print(f'  x:     {sample_x:.6f} vs {bayes_x:.6f} {x_check}')
        print(f'  y:     {sample_y:.6f} vs {bayes_y:.6f} {y_check}')
        print(f'  emass: {sample_emass:.6f} vs {bayes_emass:.6f} {e_check}')
        print()
