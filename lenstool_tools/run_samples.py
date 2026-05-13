#!/usr/bin/env python3
"""
Run lenstool on each generated sample input file
"""

import subprocess
import sys
import shutil
import json
from pathlib import Path
from tqdm import tqdm


def load_lenstool_env():
    """Load lenstool environment name from .lenstool_env file."""
    env_file = Path(__file__).parent / '.lenstool_env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            return f.read().strip()
    return 'lenstool_env8'  # Default fallback


def load_run_samples_config(config_file):
    """Load run_samples configuration from JSON file."""
    if not config_file or not Path(config_file).exists():
        return {}
    
    with open(config_file, 'r') as f:
        return json.load(f)


def run_lenstool_on_samples(samples_input_dir, samples_output_dir, working_dir=None, config_file=None, redshift=None):
    """
    Run lenstool on each sample.par file and save output.
    
    Args:
        samples_input_dir (str): Path to sample_input/ directory (relative to working_dir)
        samples_output_dir (str): Path to output/ directory (relative to working_dir)
        working_dir (str): Working directory for lenstool (should be samples/ directory)
        config_file (str): Path to run_samples configuration JSON file
        redshift (float): Optional redshift to filter samples (e.g., 1.524). If None, run all files.
        
    Returns:
        dict: Results with counts of successful and failed runs
    """
    samples_input_dir = Path(samples_input_dir)
    samples_output_dir = Path(samples_output_dir)
    working_dir = Path(working_dir) if working_dir else Path.cwd()
    
    # Load configuration
    config = load_run_samples_config(config_file)
    save_files = config.get('save_output_files', {})
    
    # Create output directory with subdirectories relative to working directory
    output_dir = working_dir / samples_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'ampli').mkdir(parents=True, exist_ok=True)
    (output_dir / 'dpl').mkdir(parents=True, exist_ok=True)
    (output_dir / 'poten').mkdir(parents=True, exist_ok=True)
    (output_dir / 'mass').mkdir(parents=True, exist_ok=True)
    
    # Create selected_output directory if saving files
    selected_output_dir = None
    if save_files:
        selected_output_dir = output_dir / 'selected_output'
        selected_output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Will save selected output files to: {selected_output_dir}")
    
    # Find all sample files relative to working directory
    input_dir = working_dir / samples_input_dir
    all_files = sorted(input_dir.glob('sample_*.par'))
    
    # Prioritize sample_best files first, then other samples in alphabetical order
    best_files = [f for f in all_files if 'sample_best' in f.name]
    other_files = [f for f in all_files if 'sample_best' not in f.name]
    sample_files = best_files + other_files
    
    # Filter by redshift if specified
    if redshift is not None:
        redshift_str = f"_z{redshift:.3f}"
        sample_files = [f for f in sample_files if redshift_str in f.name]
        if sample_files:
            print(f"Filtering for redshift z={redshift} ({len(sample_files)} files found)")
        else:
            print(f"No files found with redshift z={redshift}")
    
    if not sample_files:
        print(f"No sample files found in {input_dir}")
        return {'total': 0, 'success': 0, 'failed': 0}
    
    print(f"Running lenstool on {len(sample_files)} sample files...")
    print(f"Input directory: {samples_input_dir}")
    print(f"Output directory: {samples_output_dir}\n")
    
    success_count = 0
    failed_count = 0
    failed_samples = []
    
    # Load lenstool environment name
    lenstool_env = load_lenstool_env()
    print(f"Using conda environment: {lenstool_env}\n")
    
    # Use tqdm for progress bar with time information
    for idx, sample_file in enumerate(tqdm(sample_files, desc="Running lenstool samples", unit="sample"), start=1):
        sample_name = sample_file.stem  # e.g., "sample_00014_z1.524"
        output_file = samples_output_dir / f"{sample_name}_output.txt"
        
        try:
            # Build relative path from working directory to sample file
            # The sample_input directory should be relative to the working directory
            rel_path = sample_file.relative_to(working_dir)
            
            # Run lenstool with -n flag from the working directory
            # Use conda run to activate lenstool environment
            result = subprocess.run(
                ['conda', 'run', '-n', lenstool_env, 'lenstool', str(rel_path), '-n'],
                cwd=str(working_dir),
                capture_output=True
            )
            
            if result.returncode == 0:
                success_count += 1
                # Only print success message in postfix to avoid cluttering progress bar
                tqdm.write(f"  ✓ {sample_name} completed successfully")
                
                # Save selected output files if configured
                if save_files and selected_output_dir:
                    files_to_save = save_files.get('poten', [])
                    for filename in files_to_save:
                        src = working_dir / filename
                        if src.exists():
                            # Create output filename with sample prefix
                            dst = selected_output_dir / f"{sample_name}_{filename}"
                            shutil.copy2(src, dst)
                            tqdm.write(f"      → Saved {filename} as {dst.name}")
                        else:
                            tqdm.write(f"      ⚠ Warning: {filename} not found in working directory")
            else:
                failed_count += 1
                failed_samples.append(sample_name)
                tqdm.write(f"  ✗ {sample_name} failed with return code {result.returncode}")
        
        except Exception as e:
            failed_count += 1
            failed_samples.append(f"{sample_name} ({str(e)})")
            output_file.write_text(f"ERROR: {str(e)}\n")
            tqdm.write(f"  ✗ {sample_name}: ERROR - {str(e)}")
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Lenstool Execution Summary")
    print(f"{'='*60}")
    print(f"Total samples:  {len(sample_files)}")
    print(f"Successful:     {success_count}")
    print(f"Failed:         {failed_count}")
    
    if failed_samples:
        print(f"\nFailed samples:")
        for sample in failed_samples[:10]:  # Show first 10
            print(f"  - {sample}")
        if len(failed_samples) > 10:
            print(f"  ... and {len(failed_samples) - 10} more")
    
    return {
        'total': len(sample_files),
        'success': success_count,
        'failed': failed_count,
        'output_dir': str(samples_output_dir)
    }


def main():
    """Command-line interface for running lenstool on samples."""
    if len(sys.argv) < 2:
        print("Usage: lenstool-run-samples <samples_input_dir> [samples_output_dir] [OPTIONS]")
        print("\nRequired:")
        print("  samples_input_dir   - Path to samples/input/ directory")
        print("\nOptional Arguments:")
        print("  samples_output_dir  - Path to samples/output/ directory (default: samples/output/)")
        print("\nOptional Flags:")
        print("  -workdir DIR        - Working directory for lenstool (default: current directory)")
        print("  -config FILE        - Configuration file for output file saving (JSON)")
        print("  -redshift FLOAT     - Filter samples by redshift (e.g., 1.524). If not specified, run all files.")
        print("\nExamples:")
        print("  lenstool-run-samples samples/input")
        print("  lenstool-run-samples samples/input samples/output")
        print("  lenstool-run-samples samples/input samples/output -config run_samples_config.json")
        print("  lenstool-run-samples samples/input samples/output -redshift 1.939")
        print("  lenstool-run-samples samples/input samples/output -workdir /path/to/data -redshift 1.524")
        sys.exit(1)
    
    samples_input_dir = sys.argv[1]
    samples_output_dir = 'output'
    working_dir = 'samples'
    config_file = None
    redshift = None
    
    # Parse remaining arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '-workdir' and i + 1 < len(sys.argv):
            working_dir = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '-config' and i + 1 < len(sys.argv):
            config_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '-redshift' and i + 1 < len(sys.argv):
            try:
                redshift = float(sys.argv[i + 1])
            except ValueError:
                print(f"Error: -redshift requires a float value")
                sys.exit(1)
            i += 2
        elif not sys.argv[i].startswith('-'):
            # Positional argument for output directory
            samples_output_dir = sys.argv[i]
            i += 1
        else:
            print(f"Unknown option: {sys.argv[i]}")
            sys.exit(1)
    
    # Ensure working_dir is absolute path
    working_dir = Path(working_dir).resolve()
    
    result = run_lenstool_on_samples(samples_input_dir, samples_output_dir, working_dir, config_file, redshift)
    
    if result['failed'] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
