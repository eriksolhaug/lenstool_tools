#!/usr/bin/env python
"""
Script to process .par files in dec19a_model_solhaug/sample_input/:
1. Create mass/ subfolder
2. Copy all .par files to mass/
3. Modify each copied file:
   - Replace "output/mass/" with "../output/mass/"
   - Remove ampli, dpl, poten runmode sections
   - Remove potentiel O6 section (from "potentiel O6" to "end" after "limit O6")
   - Decrease nlens_opt by one
"""

import re
from pathlib import Path
import shutil

# Define paths
base_dir = Path("dec28c_model_solhaug/sample_input")
mass_dir = base_dir / "mass"
sample_input_dir = base_dir

# Create mass directory
mass_dir.mkdir(parents=True, exist_ok=True)
print(f"Created directory: {mass_dir}")

# Get all .par files
par_files = sorted(sample_input_dir.glob("*.par"))
print(f"Found {len(par_files)} .par files")

for par_file in par_files:
    # Copy file to mass/ directory
    dest_file = mass_dir / par_file.name
    shutil.copy2(par_file, dest_file)
    print(f"\nProcessing: {par_file.name}")
    
    # Read the file
    with open(dest_file, 'r') as f:
        content = f.read()
    
    # 1. Remove potentiel O6 section
    # Remove from "potentiel O6" to the "end" after "limit O6"
    lines = content.split('\n')
    filtered_lines = []
    skip_until_after_limit_o6 = False
    found_limit_o6 = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        if line.strip().startswith('potentiel O6'):
            skip_until_after_limit_o6 = True
            found_limit_o6 = False
            i += 1
            continue
        
        if skip_until_after_limit_o6:
            if line.strip().startswith('limit O6'):
                found_limit_o6 = True
            elif found_limit_o6 and line.strip() == 'end':
                skip_until_after_limit_o6 = False
                found_limit_o6 = False
                i += 1
                continue
            i += 1
            continue
        
        filtered_lines.append(line)
        i += 1
    
    content = '\n'.join(filtered_lines)
    print(f"  ✓ Removed potentiel O6 section")
    
    # 2. Decrease nlens_opt by one
    def decrease_nlens_opt(match):
        prefix = match.group(1)
        value = int(match.group(2))
        new_value = value - 1
        return f"{prefix}{new_value}"
    
    content = re.sub(r'(nlens_opt\s+)(\d+)', decrease_nlens_opt, content)
    print(f"  ✓ Decreased nlens_opt by one")

    # 3. Remove ampli, dpl, poten runmode sections
    lines = content.split('\n')
    filtered_lines = []
    for line in lines:
        if line.strip().startswith('ampli'):
            continue
        if line.strip().startswith('dpl'):
            continue
        if line.strip().startswith('poten '):
            continue
        filtered_lines.append(line)

    content = '\n'.join(filtered_lines)
    print(f"  ✓ Removed ampli, dpl, poten runmode sections")

    # 4. Replace xmin, xmax, ymin, ymax by -100,100,-100,100 in champ section
    lines = content.split('\n')
    filtered_lines = []
    in_champ = False
    
    for line in lines:
        if line.strip().startswith('champ'):
            in_champ = True
            filtered_lines.append(line)
        elif line.strip() == 'end' and in_champ:
            in_champ = False
            filtered_lines.append(line)
        elif in_champ and line.strip().startswith('xmin'):
            # Replace xmin value
            filtered_lines.append(re.sub(r'(xmin\s+)(-?[\d.]+)', r'\g<1>-100.000000', line))
        elif in_champ and line.strip().startswith('xmax'):
            # Replace xmax value
            filtered_lines.append(re.sub(r'(xmax\s+)(-?[\d.]+)', r'\g<1>100.000000', line))
        elif in_champ and line.strip().startswith('ymin'):
            # Replace ymin value
            filtered_lines.append(re.sub(r'(ymin\s+)(-?[\d.]+)', r'\g<1>-100.000000', line))
        elif in_champ and line.strip().startswith('ymax'):
            # Replace ymax value
            filtered_lines.append(re.sub(r'(ymax\s+)(-?[\d.]+)', r'\g<1>100.000000', line))
        else:
            filtered_lines.append(line)
    
    content = '\n'.join(filtered_lines)
    print(f"  ✓ Replaced xmin, xmax, ymin, ymax by -100,100,-100,100")

    # Write
    with open(dest_file, 'w') as f:
        f.write(content)
    
    print(f"  → Saved to: {dest_file}")

print(f"\n✓ All files processed successfully!")
print(f"Modified files are in: {mass_dir}")
