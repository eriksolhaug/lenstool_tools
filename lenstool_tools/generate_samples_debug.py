"""Debug version to understand parameter mapping"""

from lenstool_tools.samples import read_bayes_dat
from lenstool_tools.generate_samples import read_input_par, extract_potential_blocks

bayes_file = "bayes.dat"
input_file = "input.par"

# Read data
param_names, samples = read_bayes_dat(bayes_file)
input_content = read_input_par(input_file)
potential_blocks = extract_potential_blocks(input_content)

print("=== BAYES.DAT PARAMETERS ===")
for i, pname in enumerate(param_names[:20]):
    print(f"  {i}: {pname}")

print("\n=== INPUT.PAR POTENTIAL PARAMETERS ===")
for pot_name in ['O1', 'O2']:
    if pot_name in potential_blocks:
        print(f"\n{pot_name}:")
        for param_name in potential_blocks[pot_name].keys():
            print(f"  - {param_name}")
