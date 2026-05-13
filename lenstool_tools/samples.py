#!/usr/bin/env python3
"""
Parse lenstool bayes.dat output and map parameters from samples.
"""

### CONFIG ###
verbose = True
n_samples_display = 10  # Number of samples to display for each parameter
##############


def read_bayes_dat(filepath):
    """
    Read bayes.dat file and extract parameter names and data.
    Each comment line (starting with #) is a parameter name.
    Each data line is a sample row with values in the same order as the comments.
    
    Returns:
        param_names (list): List of parameter names from comments, in order
        samples (list): List of sample rows (each row is a list of floats)
    """
    param_names = []
    samples = []
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Extract parameter names from comments
            if line.startswith('#'):
                # Remove '#' and leading whitespace
                comment = line[1:].strip()
                param_names.append(comment)
            else:
                # This is a data row
                values = line.split()
                # Convert to floats
                data_row = [float(v) for v in values]
                samples.append(data_row)
    
    return param_names, samples


def print_parameter_summary(param_names, samples, n_display=10, verbose_mode=True):
    """
    Print a summary of parameters and their first n_display samples.
    """
    
    if not verbose_mode:
        return
    
    print("="*80)
    print("LENSTOOL BAYES.DAT PARAMETER SUMMARY")
    print("="*80)
    print(f"\nTotal parameters: {len(param_names)}")
    print(f"Total samples: {len(samples)}")
    print("\n" + "="*80)
    
    # For each parameter, print first n samples
    for i, param_name in enumerate(param_names):
        print(f"\n{param_name}:")
        
        # Get up to n_display values for this parameter
        for j, sample in enumerate(samples[:n_display]):
            if i < len(sample):
                print(f"  Sample {j+1}: {sample[i]}")


def main():
    """Main function for command-line usage."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: lenstool-samples <bayes.dat>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    print(f"Reading bayes.dat from: {filepath}\n")
    
    # Read the file
    param_names, samples = read_bayes_dat(filepath)
    
    # Print summary
    print_parameter_summary(param_names, samples, n_display=n_samples_display, 
                          verbose_mode=verbose)
    
    print("\n" + "="*80)
    print(f"Successfully parsed {len(samples)} samples with {len(param_names)} parameters")
    print("="*80)


if __name__ == "__main__":
    main()
