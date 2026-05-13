#!/usr/bin/env python3
"""
Parameter mapping between bayes.dat and input.par formats.

This module handles the correspondence between parameter names in bayes.dat output
and the parameter names used in input.par files.
"""

import json
from pathlib import Path


DEFAULT_MAPPING = {
    "O1": {
        "x (arcsec)": "x_centre",
        "y (arcsec)": "y_centre",
        "emass": "ellipticite",
        "theta (deg)": "angle_pos",
        "rc (arcsec)": "core_radius_kpc",
        "rcut (arcsec)": "cut_radius_kpc",
        "sigma (km/s)": "v_disp"
    },
    "O2": {
        "emass": "ellipticite",
        "theta (deg)": "angle_pos",
        "rc (arcsec)": "core_radius_kpc",
        "rcut (arcsec)": "cut_radius_kpc",
        "sigma (km/s)": "v_disp"
    },
    "O3": {
        "emass": "ellipticite",
        "rc (arcsec)": "core_radius_kpc",
        "rcut (arcsec)": "cut_radius_kpc",
        "sigma (km/s)": "v_disp"
    },
    "O4": {
        "emass": "ellipticite",
        "theta (deg)": "angle_pos",
        "rc (arcsec)": "core_radius_kpc",
        "rcut (arcsec)": "cut_radius_kpc",
        "sigma (km/s)": "v_disp"
    },
    "O5": {
        "emass": "ellipticite",
        "theta (deg)": "angle_pos",
        "rc (arcsec)": "core_radius_kpc",
        "rcut (arcsec)": "cut_radius_kpc",
        "sigma (km/s)": "v_disp"
    },
    "O6": {
        "emass": "ellipticite",
        "theta (deg)": "angle_pos",
        "rc (arcsec)": "core_radius_kpc",
        "rcut (arcsec)": "cut_radius_kpc",
        "sigma (km/s)": "v_disp"
    },
    "O7": {
        "rc (arcsec)": "core_radius_kpc",
        "rcut (arcsec)": "cut_radius_kpc",
        "sigma (km/s)": "v_disp"
    },
    "O8": {
        "rc (arcsec)": "core_radius_kpc",
        "rcut (arcsec)": "cut_radius_kpc",
        "sigma (km/s)": "v_disp"
    },
    "O9": {
        "emass": "ellipticite",
        "rc (arcsec)": "core_radius_kpc",
        "sigma (km/s)": "v_disp"
    },
    "Pot0": {
        "rcut (arcsec)": "cutkpc",
        "sigma (km/s)": "sigma"
    }
}


def load_mapping(mapping_file=None):
    """
    Load parameter mapping from a JSON file.
    
    If no file is provided, returns the default mapping.
    
    Args:
        mapping_file (str): Path to JSON mapping file
        
    Returns:
        dict: Parameter mapping dictionary
    """
    if mapping_file is None:
        return DEFAULT_MAPPING
    
    with open(mapping_file, 'r') as f:
        mapping = json.load(f)
    
    return mapping


def save_default_mapping(output_file):
    """
    Save the default mapping to a JSON file for user inspection/modification.
    
    Args:
        output_file (str): Path where to save the mapping file
    """
    with open(output_file, 'w') as f:
        json.dump(DEFAULT_MAPPING, f, indent=2)
    
    print(f"Default parameter mapping saved to: {output_file}")


def get_bayes_param_short_name(bayes_param_full):
    """
    Extract the short parameter name from a bayes.dat parameter name.
    
    Example: "O1 : x (arcsec)" → ("O1", "x (arcsec)")
    Example: "Pot0 sigma (km/s)" → ("Pot0", "sigma (km/s)")
    
    Args:
        bayes_param_full (str): Full parameter name from bayes.dat comment
        
    Returns:
        tuple: (pot_name, param_short_name) e.g., ("O1", "x (arcsec)") or ("Pot0", "sigma (km/s)")
    """
    # Handle "O# : param" format
    if ' : ' in bayes_param_full:
        parts = bayes_param_full.split(':')
        if len(parts) >= 2:
            pot_name = parts[0].strip()
            param_name = parts[1].strip()
            return pot_name, param_name
    
    # Handle "Pot0 sigma (km/s)" format
    if bayes_param_full.startswith('Pot0'):
        # Extract parameter name after "Pot0 "
        rest = bayes_param_full[5:].strip()  # Remove "Pot0 "
        return 'Pot0', rest
    
    return None, None


def get_input_par_param_name(pot_name, bayes_short_param, mapping):
    """
    Get the corresponding input.par parameter name for a bayes.dat parameter.
    
    Args:
        pot_name (str): Potential name (e.g., "O1")
        bayes_short_param (str): Short parameter name from bayes.dat (e.g., "x (arcsec)")
        mapping (dict): Parameter mapping dictionary
        
    Returns:
        str: Corresponding input.par parameter name, or None if not found
    """
    if pot_name not in mapping:
        return None
    
    return mapping[pot_name].get(bayes_short_param, None)


if __name__ == "__main__":
    # Save default mapping for inspection
    save_default_mapping("parameter_mapping.json")
