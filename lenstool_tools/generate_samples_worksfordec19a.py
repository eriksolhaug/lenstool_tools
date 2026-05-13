#!/usr/bin/env python3
"""
Generate individual input.par files for each sample in bayes.dat
"""

import os
import re
import json
import random
import shutil
from pathlib import Path
from .parameter_mapping import load_mapping, get_bayes_param_short_name, get_input_par_param_name


def read_input_par(filepath):
    """
    Read the template input.par file and return its contents as a string.
    
    Args:
        filepath (str): Path to the input.par file
        
    Returns:
        str: Full contents of the input.par file
    """
    with open(filepath, 'r') as f:
        return f.read()


def set_inverse_to_zero(input_par_content):
    """
    Remove the inverse line from the runmode section completely.
    
    Args:
        input_par_content (str): The input.par file content
        
    Returns:
        str: Modified input.par content with inverse line removed
    """
    # Find and remove the entire inverse line in the runmode section
    pattern = r'^\t+inverse\s+.*?$\n'
    modified = re.sub(pattern, '', input_par_content, flags=re.MULTILINE)
    
    return modified


def update_file_paths_for_sample_input(input_par_content):
    """
    Update file paths to use relative paths for catalogs and arcs.
    When lenstool runs from samples/ directory, paths in sample_input/ files
    should reference ../input/ relative to sample_input/.
    This is equivalent to input/ relative to samples/.
    
    We use ../input/ which works both ways.
    
    Args:
        input_par_content (str): The input.par file content
        
    Returns:
        str: Modified input.par content with updated paths
    """
    # Update paths that reference arcs/ and cats/ directories
    # These need to be updated (but NOT with ../ since lenstool runs from samples/)
    # Instead use input/  when lenstool runs from samples/
    modified = input_par_content
    
    # Update image file paths in runmode: "image     1 arcs/..." -> "image     1 input/arcs/..."
    # Use negative lookahead to avoid double-prefixing
    modified = re.sub(r'(\bimage\s+\d+\s+)(?!input/)arcs/', r'\1input/arcs/', modified)
    
    # Update multfile paths: "multfile 7 arcs/..." -> "multfile 7 input/arcs/..."
    modified = re.sub(r'(\bmultfile\s+\d+\s+)(?!input/)arcs/', r'\1input/arcs/', modified)
    
    # Update arclet paths: "arclet 1 arcs/..." -> "arclet 1 input/arcs/..."
    modified = re.sub(r'(\barclet\s+\d+\s+)(?!input/)arcs/', r'\1input/arcs/', modified)
    
    # Update catalog paths: "cats/..." -> "input/cats/..."
    modified = re.sub(r'(?<!input/)cats/', r'input/cats/', modified)
    
    return modified


def update_runmode_for_samples(input_par_content, sample_number, lens_redshift=None, source_redshift=None):
    """
    Update the runmode section to:
    1. Remove the inverse line
    2. ADD output lines for mass, ampli, dpl, and poten if they don't exist
    3. Ensure they output to the correct sample-specific files
    4. Only include mass if lens_redshift is set
    5. Only include ampli/dpl/poten if source_redshift is set
    
    Args:
        input_par_content (str): The input.par file content
        sample_number (int or str): The sample number for naming output files, or "best" for best-fit
        lens_redshift (float): Lens redshift (if set, mass map is created)
        source_redshift (float): Source redshift (if set, ampli/dpl/poten maps are created)
        
    Returns:
        str: Modified input.par content with updated runmode
    """
    # Find the runmode section
    runmode_start = input_par_content.find('runmode')
    if runmode_start < 0:
        return input_par_content
    
    # Find the end of runmode - looking for 'end' followed by non-tab character
    search_pos = runmode_start
    runmode_end = -1
    while True:
        end_pos = input_par_content.find('end\n', search_pos)
        if end_pos < 0:
            break
        next_line_start = end_pos + 4
        if next_line_start < len(input_par_content):
            next_char = input_par_content[next_line_start]
            if next_char != '\t':
                runmode_end = end_pos + 4  # Include the 'end\n' that's after the indented end
                break
        search_pos = end_pos + 1
    
    if runmode_end < 0:
        return input_par_content
    
    runmode_section = input_par_content[runmode_start:runmode_end]
    
    # Remove inverse line
    runmode_section = re.sub(r'^\t+inverse\s+.*?$\n', '', runmode_section, flags=re.MULTILINE)
    
    # Remove any existing poten, ampli, dpl, mass lines (we'll add them fresh)
    runmode_section = re.sub(r'^\t+poten\s+.*?$\n', '', runmode_section, flags=re.MULTILINE)
    runmode_section = re.sub(r'^\t+ampli\s+.*?$\n', '', runmode_section, flags=re.MULTILINE)
    runmode_section = re.sub(r'^\t+dpl\s+.*?$\n', '', runmode_section, flags=re.MULTILINE)
    runmode_section = re.sub(r'^\t+mass\s+.*?$\n', '', runmode_section, flags=re.MULTILINE)
    
    # Determine the redshift to use for filenames
    z_for_filename = source_redshift if source_redshift is not None else (lens_redshift if lens_redshift is not None else None)
    z_str = f"_z{z_for_filename:.3f}" if z_for_filename is not None else ""
    
    # Format sample identifier (either "best" or 5-digit number)
    if isinstance(sample_number, str) and sample_number == "best":
        sample_id = "best"
    else:
        sample_id = f"{sample_number:05d}"
    
    # Build output lines to add (before the 'end' statement)
    output_lines = []
    
    # Add mass output line only if lens_redshift is set
    if lens_redshift is not None:
        mass_z_str = f"_z{lens_redshift:.4f}"
        output_lines.append(f'\tmass      3 1001 {lens_redshift} output/mass/sample_{sample_id}{mass_z_str}_mass.fits')
    
    # Add ampli output line only if source_redshift is set
    if source_redshift is not None:
        output_lines.append(f'\tampli     1 1001 {source_redshift} output/ampli/sample_{sample_id}{z_str}_ampli.fits')
    
    # Add dpl output lines only if source_redshift is set
    if source_redshift is not None:
        output_lines.append(f'\tdpl       1 1001 {source_redshift} output/dpl/sample_{sample_id}{z_str}_dplx.fits output/dpl/sample_{sample_id}{z_str}_dply.fits')
    
    # Add poten output line only if source_redshift is set
    if source_redshift is not None:
        output_lines.append(f'\tpoten     1 1001 {source_redshift} output/poten/sample_{sample_id}{z_str}_poten.fits')
    
    # Insert output lines before the indented 'end' of runmode section
    if output_lines:
        # Remove any trailing whitespace and newlines
        runmode_section = runmode_section.rstrip('\n')
        # Check if runmode_section ends with indented 'end'
        if runmode_section.endswith('\tend'):
            # Remove the trailing indented 'end'
            runmode_section = runmode_section[:-4].rstrip('\n')
        # Add output lines
        for line in output_lines:
            runmode_section += '\n' + line
        # Add back the indented 'end' and final newline
        runmode_section += '\n\tend\n'
    
    # Replace in full content
    modified_content = input_par_content[:runmode_start] + runmode_section + input_par_content[runmode_end:]
    return modified_content


def remove_potential_block(par_content, potential_name):
    """
    Remove a potential block and its limit from par file content.
    
    Args:
        par_content (str): The par file content
        potential_name (str): Name of potential to remove (e.g., 'O6')
        
    Returns:
        str: Content with potential block removed
    """
    # Pattern to match: "potentiel O6" (note: lenstool uses "potentiel" not "potential")
    # The block ends at the indented "end"
    # Also remove the corresponding limit block
    # Limit blocks can use either numeric identifiers (1-6) or named (O1-O6)
    lines = par_content.split('\n')
    filtered_lines = []
    skip_block = False
    i = 0
    
    # Extract numeric part from potential name (e.g., "O6" -> "6")
    limit_number = potential_name.lstrip('O')
    
    while i < len(lines):
        line = lines[i]
        
        # Check if we're starting a potential block to remove
        if re.match(fr'^potentiel\s+{potential_name}\b', line):
            skip_block = True
            # Skip until we find the closing "end"
            i += 1
            while i < len(lines):
                if re.match(r'^\s+end\s*$', lines[i]):
                    skip_block = False
                    i += 1
                    break
                i += 1
            continue
        
        # Check if we're starting a limit block to remove (either numeric or named)
        # Match either "limit 6" or "limit O6"
        if re.match(fr'^limit\s+({limit_number}|{potential_name})\b', line):
            # Skip until we find the closing "end"
            i += 1
            while i < len(lines):
                if re.match(r'^\s+end\s*$', lines[i]):
                    i += 1
                    break
                i += 1
            continue
        
        if not skip_block:
            filtered_lines.append(line)
        i += 1
    
    result = '\n'.join(filtered_lines)
    # Clean up any double newlines that might result
    result = re.sub(r'\n\n\n+', '\n\n', result)
    
    return result


def extract_potfile0_block(input_par_content):
    """
    Extract potfile0 block from input.par file.
    
    Args:
        input_par_content (str): The input.par file content
        
    Returns:
        dict: Dictionary mapping parameter names to their values and flags
    """
    potfile0_params = {}
    
    # Find potfile0 block
    pattern = r'potfile0(.*?)(?=cline|limit|end\s|$)'
    match = re.search(pattern, input_par_content, re.DOTALL)
    
    if match:
        potfile0_content = match.group(1)
        
        # Extract parameter lines (lines with parameter assignments)
        for line in potfile0_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Parse parameter lines like: sigma   1 115.415843 84.590184
                parts = line.split()
                if len(parts) >= 2:
                    param_name = parts[0]
                    try:
                        # Try to parse as: name flag value1 [value2]
                        flag = int(parts[1])
                        if len(parts) >= 3:
                            value1 = float(parts[2])
                            potfile0_params[param_name] = {
                                'flag': flag,
                                'value': value1,
                                'full_line': line
                            }
                    except (ValueError, IndexError):
                        pass
    
    return potfile0_params


def extract_potential_blocks(input_par_content):
    """
    Extract all potential blocks from input.par file.
    
    Args:
        input_par_content (str): The input.par file content
        
    Returns:
        dict: Dictionary mapping potential names (e.g., 'O1', 'O2') to their parameter lines
    """
    potentials = {}
    
    # Find all potentiel blocks
    pattern = r'potentiel\s+(\w+)(.*?)(?=potentiel\s+\w+|limit\s+\d+|grille|cline|source|observ|cosmologie|champ|fini|$)'
    matches = re.finditer(pattern, input_par_content, re.DOTALL)
    
    for match in matches:
        pot_name = match.group(1)
        pot_content = match.group(2)
        
        # Extract parameter lines (lines with parameter assignments)
        param_lines = {}
        for line in pot_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Parse parameter lines like: x_centre     -0.209451
                parts = line.split()
                if len(parts) >= 2:
                    param_name = parts[0]
                    try:
                        param_value = float(parts[1])
                        param_lines[param_name] = param_value
                    except (ValueError, IndexError):
                        # If not a float, store as is
                        param_lines[param_name] = ' '.join(parts[1:])
        
        potentials[pot_name] = param_lines
    
    return potentials




def fix_zero_core_radius(input_par_content, min_core_radius=0.000001):
    """
    Replace core_radius values of 0.0 with a small non-zero value to prevent NaN in poten calculations.
    
    Args:
        input_par_content (str): The input.par file content
        min_core_radius (float): Minimum core radius value to use (default: 0.000001)
        
    Returns:
        str: Modified input.par content with zero core_radius values replaced
    """
    # Find all potentiel blocks and fix any core_radius that equals 0
    # Pattern: potentiel NAME ... core_radius_kpc 0 (or 0.0) ... end
    pattern = r'(core_radius_kpc\s+)0(?:\.0+)?(\s)'
    replacement = rf'\g<1>{min_core_radius}\g<2>'
    modified_content = re.sub(pattern, replacement, input_par_content, flags=re.MULTILINE)
    
    return modified_content


def apply_arcsec_to_kpc_conversion(value, param_name, conversion_factor=None):
    """
    Apply arcsec to kpc conversion to size parameters if specified.
    
    Args:
        value (float): Parameter value
        param_name (str): The actual input.par parameter name (e.g., 'core_radius_kpc', 'cut_radius_kpc', 
                          'x_centre', 'y_centre')
        conversion_factor (float): Conversion factor (kpc_per_arcsec). If None, no conversion.
        
    Returns:
        float: Converted value if applicable, otherwise original value
    """
    if conversion_factor is None:
        return value
    
    param_lower = param_name.lower()
    
    # Do NOT convert position parameters (x, y positions)
    if 'x_centre' in param_lower or 'y_centre' in param_lower or param_lower in ['x', 'y']:
        return value
    
    # Convert radius parameters (core_radius_kpc, cut_radius_kpc, etc.)
    if 'radius' in param_lower or 'core' in param_lower or 'cut' in param_lower:
        return value * conversion_factor
    
    return value


def update_potential_values(input_par_content, param_names, sample_data, mapping, conversion_factor=None):
    """
    Update all potential parameter values in input.par content with values from a sample.
    
    Args:
        input_par_content (str): The input.par file content
        param_names (list): List of all parameter names from bayes.dat
        sample_data (list): Single sample row from bayes.dat (list of floats)
        mapping (dict): Parameter mapping dictionary from bayes.dat to input.par
        conversion_factor (float): Conversion factor for arcsec to kpc (optional)
        
    Returns:
        str: Modified input.par content with updated parameter values
    """
    modified_content = input_par_content
    
    # For each bayes.dat parameter, find the corresponding input.par parameter and update it
    for i, bayes_param_full in enumerate(param_names):
        if i >= len(sample_data):
            break
        
        value = sample_data[i]
        
        # Extract pot_name and short param name from bayes.dat parameter
        pot_name, bayes_short_param = get_bayes_param_short_name(bayes_param_full)
        
        if pot_name is None:
            continue
        
        # Get the corresponding input.par parameter name
        input_par_param = get_input_par_param_name(pot_name, bayes_short_param, mapping)
        
        if input_par_param is None:
            # No mapping found for this parameter
            continue
        
        # Apply arcsec to kpc conversion if needed
        # Use input_par_param for the check since that's what actually appears in the file
        value = apply_arcsec_to_kpc_conversion(value, input_par_param, conversion_factor)
        
        # Replace the parameter value in the potentiel block
        # Pattern: potentiel O1 ... param_name VALUE ... end
        pattern = rf'(potentiel\s+{pot_name}.*?{input_par_param}\s+)[^\s]+'
        replacement = rf'\g<1>{value}'
        modified_content = re.sub(pattern, replacement, modified_content, 
                                flags=re.DOTALL, count=1)
    
    return modified_content


def update_potfile0_values(input_par_content, param_names, sample_data, conversion_factor=None):
    """
    Update potfile0 parameter values with values from a sample.
    
    Matches parameter names from bayes.dat like "Pot0 rcut (arcsec)" and "Pot0 sigma (km/s)"
    and updates corresponding lenstool keywords in the potfile0 block.
    
    Args:
        input_par_content (str): The input.par file content
        param_names (list): List of all parameter names from bayes.dat
        sample_data (list): Single sample row from bayes.dat (list of floats)
        conversion_factor (float): Conversion factor for arcsec to kpc (optional)
        
    Returns:
        str: Modified input.par content with updated potfile0 values
    """
    modified_content = input_par_content
    
    # Mapping from bayes.dat parameter names to lenstool keywords
    # These are the exact parameter names as they appear in bayes.dat comments
    potfile0_param_map = {
        'Pot0 rcut (arcsec)': 'cutkpc',
        'Pot0 sigma (km/s)': 'sigma',
    }
    
    # Look for Pot0 parameters in bayes.dat
    for i, param_name in enumerate(param_names):
        if i >= len(sample_data):
            break
            
        # Check if this is a Pot0 parameter we recognize
        if param_name not in potfile0_param_map:
            continue
        
        # Get the lenstool keyword for this parameter
        lenstool_keyword = potfile0_param_map[param_name]
        param_value = sample_data[i]
        
        # Apply arcsec to kpc conversion for rcut if needed
        # This is the CRITICAL FIX: always apply conversion when conversion_factor is provided
        # and it's an rcut parameter, regardless of source (bayes.dat or best-fit)
        if 'rcut' in param_name.lower() and conversion_factor is not None:
            param_value = param_value * conversion_factor
        
        # Update the corresponding line in potfile0 block
        # Pattern: match the keyword line (e.g., "\tcutkpc   3 98.208178 36.489045")
        # Replace the first float value (the actual parameter value) with converted value
        pattern = rf'(\t{lenstool_keyword}\s+\d+\s+)[0-9.eE+-]+(\s+)'
        replacement = rf'\g<1>{param_value}\g<2>'
        modified_content = re.sub(pattern, replacement, modified_content, count=1)
    
    return modified_content


def remove_image_block(input_par_content):
    """
    Remove the entire image block from input.par content.
    
    Args:
        input_par_content (str): The input.par file content
        
    Returns:
        str: Modified input.par content with image block removed
    """
    # Match image block from "image" to its corresponding "end"
    pattern = r'image\s*\n([\s\S]*?)\s*end\s*\n'
    modified = re.sub(pattern, '', input_par_content, count=1)
    return modified


def remove_runmode_lines(input_par_content, lines_to_remove=None):
    """
    Remove specific lines from the runmode section.
    
    Args:
        input_par_content (str): The input.par file content
        lines_to_remove (list): List of parameter names to remove (e.g., ['arclet', 'sigposArcsec', 'sigpos'])
        
    Returns:
        str: Modified input.par content with lines removed from runmode
    """
    if lines_to_remove is None:
        lines_to_remove = ['arclet', 'sigposArcsec', 'sigpos']
    
    # Find runmode section
    runmode_start = input_par_content.find('runmode')
    if runmode_start < 0:
        return input_par_content
    
    # Find the end of runmode section (look for "end\n")
    search_pos = runmode_start
    runmode_end = -1
    while True:
        end_pos = input_par_content.find('end\n', search_pos)
        if end_pos < 0:
            break
        # Check if next line is not indented (top-level section)
        next_line_start = end_pos + 4
        if next_line_start < len(input_par_content):
            next_char = input_par_content[next_line_start]
            if next_char != '\t':
                runmode_end = end_pos
                break
        search_pos = end_pos + 1
    
    if runmode_end < 0:
        return input_par_content
    
    runmode_section = input_par_content[runmode_start:runmode_end]
    
    # Remove each line
    for param_name in lines_to_remove:
        # Pattern: line starting with tab, then parameter name, then any content until newline
        # Replace entire line including newline
        pattern = rf'^\t{param_name}\s+.*?$\n'
        runmode_section = re.sub(pattern, '', runmode_section, flags=re.MULTILINE)
    
    # Replace in full content
    modified_content = input_par_content[:runmode_start] + runmode_section + input_par_content[runmode_end:]
    return modified_content


def add_runmode_output_specs(input_par_content, sample_number, config_dict):
    """
    Add output file specifications to runmode section based on config.
    
    Args:
        input_par_content (str): The input.par file content
        sample_number (int): The sample number (for naming output files)
        config_dict (dict): Configuration dictionary with output_files list
        
    Returns:
        str: Modified input.par content with output specs added to runmode
    """
    if not config_dict or 'output_files' not in config_dict:
        return input_par_content
    
    # Find runmode section - look for "runmode" and find the "end\n" that closes it
    runmode_start = input_par_content.find('runmode')
    if runmode_start < 0:
        return input_par_content
    
    # Find the end line within runmode (e.g., "\t   end\n" or "\tend\n")
    # First, find "end\n" after runmode
    search_pos = runmode_start
    runmode_end = -1
    while True:
        end_pos = input_par_content.find('end\n', search_pos)
        if end_pos < 0:
            break
        # Check if this is the runmode's end by making sure next section is not indented
        # (e.g., "image" or other top-level sections)
        next_line_start = end_pos + 4  # After "end\n"
        if next_line_start < len(input_par_content):
            next_char = input_par_content[next_line_start]
            if next_char != '\t':  # Next line is not indented, so this is the section end
                runmode_end = end_pos
                break
        search_pos = end_pos + 1
    
    if runmode_end < 0:
        return input_par_content
    
    # Build output specification lines
    output_specs = []
    for output_file_spec in config_dict['output_files']:
        param_name = output_file_spec['name']
        float1 = output_file_spec['float1']
        
        # Build the output filename with directory if specified
        output_filename = f"sample_{sample_number:05d}_{float1}_{param_name}.fits"
        if 'directory' in output_file_spec and output_file_spec['directory']:
            output_filename = f"{output_file_spec['directory']}/{output_filename}"
        
        # Create the output line: "param_name   1 1001 1.524 output_filename"
        output_line = f"\t{param_name}\t1 1001 {float1} {output_filename}"
        output_specs.append(output_line)
    
    # Insert before the "end" of runmode
    output_specs_text = '\n'.join(output_specs) + '\n'
    
    # Insert at the end of runmode (before "end")
    modified_content = (input_par_content[:runmode_end] + 
                       output_specs_text + 
                       input_par_content[runmode_end:])
    
    return modified_content


def load_runmode_config(config_file=None):
    """
    Load runmode configuration from JSON file.
    
    Args:
        config_file (str): Path to runmode_config.json file
        
    Returns:
        dict: Configuration dictionary
    """
    if config_file is None:
        # Look for default config in tests directory
        config_file = Path(__file__).parent / 'tests' / 'runmode_config.json'
    
    if not Path(config_file).exists():
        # Return default config if file doesn't exist
        return {
            'output_files': [
                {'name': 'ampli', 'float1': 1.524},
                {'name': 'poten', 'float1': 1.524}
            ]
        }
    
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def load_sample_selection_config(config_file=None):
    """
    Load sample selection configuration from a JSON file.
    
    The config file should have the following structure:
    {
        "num_samples": 100,
        "random_seed": 42
    }
    
    Args:
        config_file (str): Path to the sample selection config JSON file (optional)
        
    Returns:
        dict: Configuration with 'num_samples' and optional 'random_seed'
              Returns None if file doesn't exist or is invalid
    """
    if config_file is None or not Path(config_file).exists():
        return None
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            # Validate required fields
            if 'num_samples' not in config:
                print(f"Warning: 'num_samples' not found in {config_file}")
                return None
            return config
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load sample selection config: {e}")
        return None


def select_sample_indices(total_samples, config):
    """
    Select sample indices based on configuration.
    
    Args:
        total_samples (int): Total number of samples available
        config (dict): Configuration with 'num_samples' and optional 'random_seed'
        
    Returns:
        list: Sorted list of selected sample indices (0-based)
    """
    num_to_select = config.get('num_samples', total_samples)
    
    # Ensure num_to_select doesn't exceed total_samples
    if num_to_select > total_samples:
        print(f"Warning: Requested {num_to_select} samples but only {total_samples} available. Using all {total_samples}.")
        num_to_select = total_samples
    
    # Set random seed if provided
    if 'random_seed' in config:
        random.seed(config['random_seed'])
    
    # Select random indices
    selected_indices = sorted(random.sample(range(total_samples), num_to_select))
    return selected_indices


def generate_sample_input_files(bayes_dat_path, template_input_par_path, mapping_file=None, output_base_dir='samples', runmode_config_file=None, sample_selection_config_file=None, bestopt_par_path=None, lens_redshift=None, source_redshift=None, size_arcsec_to_kpc=None):
    """
    Generate individual input.par files for each sample in bayes.dat
    
    Args:
        bayes_dat_path (str): Path to the bayes.dat file
        template_input_par_path (str): Path to the template input.par file
        mapping_file (str): Path to parameter mapping JSON file (optional, uses default if not provided)
        output_base_dir (str): Base directory to create samples/ subdirectory
        runmode_config_file (str): Path to runmode configuration JSON file (optional)
        sample_selection_config_file (str): Path to sample selection config JSON file (optional)
        bestopt_par_path (str): Path to bestopt.par file for creating sample_best.par (optional)
        lens_redshift (float): Lens redshift (if set, mass map is created)
        source_redshift (float): Source redshift (if set, ampli/dpl/poten maps are created)
        size_arcsec_to_kpc (float): Conversion factor to convert arcsec to kpc for size parameters (optional)
        
    Returns:
        str: Path to the created samples directory
    """
    # Import from samples module
    from .samples import read_bayes_dat
    
    # Load the parameter mapping
    mapping = load_mapping(mapping_file)
    
    # Load runmode configuration
    runmode_config = load_runmode_config(runmode_config_file)
    
    # Extract size_arcsec_to_kpc conversion factor from config if not provided as parameter
    if size_arcsec_to_kpc is None and 'bayes_file' in runmode_config:
        size_arcsec_to_kpc = runmode_config['bayes_file'].get('size_arcsec_to_kpc', None)
    
    if size_arcsec_to_kpc is not None:
        print(f"Using arcsec to kpc conversion factor: {size_arcsec_to_kpc}")
    
    # Create output directories
    # Create sample_input and output directories directly in the output_base_dir
    # without creating an intermediate samples/ subdirectory
    output_path = Path(output_base_dir)
    
    samples_dir = output_path / 'sample_input'
    samples_output_dir = output_path / 'output'
    
    samples_dir.mkdir(parents=True, exist_ok=True)
    samples_output_dir.mkdir(parents=True, exist_ok=True)
    
    if 'output_base_directories' in runmode_config:
        for output_type, output_path in runmode_config['output_base_directories'].items():
            (samples_output_dir / output_path).mkdir(parents=True, exist_ok=True)
    
    print(f"Creating sample input files in: {samples_dir}")
    
    # Read bayes.dat
    param_names, samples = read_bayes_dat(bayes_dat_path)
    
    # Read template input.par
    template_content = read_input_par(template_input_par_path)
    
    # Prepare template: set inverse to 0 (remove inverse line)
    template_content = set_inverse_to_zero(template_content)
    
    # Extract potential blocks to understand structure
    potential_blocks = extract_potential_blocks(template_content)
    potfile0_params = extract_potfile0_block(template_content)
    
    print(f"Found {len(potential_blocks)} potential blocks: {list(potential_blocks.keys())}")
    print(f"Found potfile0 block with {len(potfile0_params)} parameters")
    print(f"Using parameter mapping from: {mapping_file if mapping_file else 'built-in default'}")
    
    # Load sample selection config if provided
    sample_selection_config = load_sample_selection_config(sample_selection_config_file)
    
    # Also check if sample_selection is embedded in runmode_config
    if sample_selection_config is None and 'sample_selection' in runmode_config:
        sample_selection_config = runmode_config['sample_selection']
    
    # Determine which samples to process
    if sample_selection_config is not None:
        selected_indices = select_sample_indices(len(samples), sample_selection_config)
        print(f"Processing {len(selected_indices)} randomly selected samples (seed: {sample_selection_config.get('random_seed', 'random')})...")
    else:
        selected_indices = list(range(len(samples)))
        print(f"Processing all {len(samples)} samples...")
    
    # For each selected sample, create an input.par file
    for output_number, sample_idx in enumerate(selected_indices, start=1):
        sample_data = samples[sample_idx]
        # Update potential values using the mapping
        updated_content = update_potential_values(template_content, param_names, 
                                                 sample_data, mapping, size_arcsec_to_kpc)
        
        # Update potfile0 values
        updated_content = update_potfile0_values(updated_content, param_names, sample_data, size_arcsec_to_kpc)
        
        # Fix any zero core_radius values to avoid NaN in poten output
        updated_content = fix_zero_core_radius(updated_content)
        
        # Update file paths for sample input (relative paths to ../input/)
        updated_content = update_file_paths_for_sample_input(updated_content)
        
        # Update runmode for samples (remove inverse, add all output specs)
        # Now includes poten output directly in main file
        updated_content = update_runmode_for_samples(updated_content, sample_idx + 1, lens_redshift, source_redshift)
        
        # Determine filename based on redshift
        z_for_filename = source_redshift if source_redshift is not None else (lens_redshift if lens_redshift is not None else None)
        z_str = f"_z{z_for_filename:.3f}" if z_for_filename is not None else ""
        
        # Write main sample file (if either lens_redshift or source_redshift is set)
        # This now includes all outputs: mass, ampli, dpl, AND poten
        if lens_redshift is not None or source_redshift is not None:
            output_file = samples_dir / f'sample_{sample_idx+1:05d}{z_str}.par'
            with open(output_file, 'w') as f:
                f.write(updated_content)
        
        if output_number % max(1, len(selected_indices) // 10) == 0:
            print(f"  Created {output_number} / {len(selected_indices)} files")
    
    print(f"Successfully created {len(selected_indices)} input.par files in {samples_dir}")
    
    # Create sample_best.par from the bestopt file if provided, otherwise use template
    if bestopt_par_path is not None:
        bestopt_content = read_input_par(bestopt_par_path)
    else:
        bestopt_content = template_content
    
    # Update file paths for sample input to use input/arcs/ and input/cats/ conventions
    bestopt_content = update_file_paths_for_sample_input(bestopt_content)
    
    # Remove inverse line from bestopt
    bestopt_content = set_inverse_to_zero(bestopt_content)
    
    # Fix any zero core_radius values to avoid NaN in poten output
    bestopt_content = fix_zero_core_radius(bestopt_content)
    
    # Update runmode with redshifts using "best" as sample identifier
    # Now includes poten output directly in main file
    bestopt_content = update_runmode_for_samples(bestopt_content, "best", lens_redshift, source_redshift)
    
    # Ensure mass line is present (it should be added by update_runmode_for_samples, but add it explicitly if missing)
    if lens_redshift is not None:
        if 'mass      3 1001' not in bestopt_content:
            # Find the runmode section and add the mass line
            runmode_match = re.search(r'runmode\n(.*?)(\t+end\n)', bestopt_content, re.DOTALL)
            if runmode_match:
                runmode_content = runmode_match.group(1)
                if 'mass' not in runmode_content:
                    mass_z_str = f"_z{lens_redshift:.4f}"
                    mass_line = f'\tmass      3 1001 {lens_redshift} output/mass/sample_best{mass_z_str}_mass.fits\n'
                    # Insert before the 'end' line
                    insert_pos = runmode_match.start(2)
                    bestopt_content = bestopt_content[:insert_pos] + mass_line + bestopt_content[insert_pos:]
    
    # Determine filename based on redshift
    z_for_filename = source_redshift if source_redshift is not None else (lens_redshift if lens_redshift is not None else None)
    z_str = f"_z{z_for_filename:.3f}" if z_for_filename is not None else ""
    
    # Write the updated version as sample_best.par (with redshift in name if applicable)
    # This now includes all outputs: mass, ampli, dpl, AND poten
    sample_best_path = samples_dir / f'sample_best{z_str}.par'
    with open(sample_best_path, 'w') as f:
        f.write(bestopt_content)
    print(f"Created {sample_best_path} with updated paths")
    
    return str(samples_dir)


def main():
    """Command-line interface for generate_samples."""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: lenstool-generate-samples <bayes.dat> <input.par> [OPTIONS]")
        print("\nRequired:")
        print("  bayes.dat            - Output from lenstool Bayesian optimization")
        print("  input.par            - Template input.par file")
        print("\nOptional Flags:")
        print("  -mapping FILE        - Parameter mapping file")
        print("  -runmode FILE        - Sample generation config file (runmode outputs + sample selection)")
        print("  -config FILE         - Sample selection config file (legacy, overridden by -runmode)")
        print("  -bestopt FILE        - Best-fit parameter file (creates sample_best.par)")
        print("  -zlens FLOAT         - Lens redshift (for mass maps)")
        print("  -zsource FLOAT       - Source redshift (for ampli/dpl/poten maps)")
        print("  -output DIR          - Output directory for samples/ subdirectory (default: current dir)")
        print("\nNote: size_arcsec_to_kpc conversion factor is set in the config file")
        print("under bayes_file.size_arcsec_to_kpc (optional, e.g., 5.611 for z=0.4301)")
        print("\nExamples:")
        print("  lenstool-generate-samples bayes.dat input.par -zlens 0.4301 -zsource 1.524")
        print("  lenstool-generate-samples bayes.dat input.par -runmode sample_generation_config.json -bestopt bestopt.par -zlens 0.4301 -zsource 1.524")
        print("\nSample generation config format (JSON):")
        print("  {\"sample_selection\": {\"num_samples\": 100, \"random_seed\": 42},")
        print("   \"output_files\": [...],")
        print("   \"bayes_file\": {\"size_arcsec_to_kpc\": 5.611}}")
        sys.exit(1)
    
    bayes_dat = sys.argv[1]
    input_par = sys.argv[2]
    
    # Parse optional flags
    mapping_file = None
    runmode_config_file = None
    sample_selection_config_file = None
    bestopt_par_file = None
    output_dir = '.'
    lens_redshift = None
    source_redshift = None
    
    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == '-mapping' and i + 1 < len(sys.argv):
            mapping_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '-runmode' and i + 1 < len(sys.argv):
            runmode_config_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '-config' and i + 1 < len(sys.argv):
            sample_selection_config_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '-bestopt' and i + 1 < len(sys.argv):
            bestopt_par_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '-zlens' and i + 1 < len(sys.argv):
            try:
                lens_redshift = float(sys.argv[i + 1])
            except ValueError:
                print(f"Error: -zlens requires a float value")
                sys.exit(1)
            i += 2
        elif sys.argv[i] == '-zsource' and i + 1 < len(sys.argv):
            try:
                source_redshift = float(sys.argv[i + 1])
            except ValueError:
                print(f"Error: -zsource requires a float value")
                sys.exit(1)
            i += 2
        elif sys.argv[i] == '-output' and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]
            i += 2
        else:
            print(f"Unknown option: {sys.argv[i]}")
            sys.exit(1)
    
    generate_sample_input_files(bayes_dat, input_par, mapping_file, output_dir, 
                               runmode_config_file, sample_selection_config_file, bestopt_par_file, 
                               lens_redshift, source_redshift)


if __name__ == "__main__":
    main()
