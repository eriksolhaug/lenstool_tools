#!/usr/bin/env python3
"""
Calculate spherical mean coordinates from lensmodel source positions.
Groups objects by base ID (e.g., 1A, 1B, 1C -> object 1).
"""

import re
import numpy as np
from pathlib import Path


def extract_base_id(obj_id):
    """
    Extract base object ID from full ID.
    Examples: '1A' -> '1', '5.1' -> '5', 'A3a' -> 'A3'
    """
    # For numeric.number (e.g., 5.1, 5.2, 6.3), extract just the integer part
    match = re.match(r'^(\d+)\.\d+$', obj_id)
    if match:
        return match.group(1)
    
    # For uppercase letter patterns (1A, 1B, 1C, 2A, 2B, 2C)
    match = re.match(r'^(\d+)[A-C]$', obj_id)
    if match:
        return match.group(1)
    
    # For lowercase letter patterns (A3a, A3b, A3c, B7a, B7b, B7c)
    match = re.match(r'^([A-Za-z0-9]+)[a-c]$', obj_id)
    if match:
        return match.group(1)
    
    return obj_id


def ra_dec_to_xyz(ra, dec):
    """
    Convert RA/DEC (in degrees) to unit sphere Cartesian coordinates.
    """
    ra_rad = np.radians(ra)
    dec_rad = np.radians(dec)
    x = np.cos(dec_rad) * np.cos(ra_rad)
    y = np.cos(dec_rad) * np.sin(ra_rad)
    z = np.sin(dec_rad)
    return np.array([x, y, z])


def xyz_to_ra_dec(x, y, z):
    """
    Convert Cartesian coordinates back to RA/DEC (in degrees).
    """
    ra_rad = np.arctan2(y, x)
    dec_rad = np.arcsin(z / np.sqrt(x**2 + y**2 + z**2))
    ra = np.degrees(ra_rad)
    dec = np.degrees(dec_rad)
    # Normalize RA to [0, 360)
    if ra < 0:
        ra += 360
    return ra, dec


def spherical_mean(coords_list):
    """
    Calculate spherical mean of a list of (ra, dec) coordinates.
    """
    xyz_coords = np.array([ra_dec_to_xyz(ra, dec) for ra, dec in coords_list])
    mean_xyz = np.mean(xyz_coords, axis=0)
    # Normalize to unit sphere
    mean_xyz = mean_xyz / np.linalg.norm(mean_xyz)
    return xyz_to_ra_dec(mean_xyz[0], mean_xyz[1], mean_xyz[2])


def main():
    data_file = Path.home() / "Research/Tools/lenstool_tools/dec19a_model_solhaug/output/selected_output/sample_best_z1.524_source.dat"
    
    if not data_file.exists():
        raise FileNotFoundError(f"Data file not found: {data_file}")
    
    # Dictionary to group coordinates by base object ID
    objects = {}
    
    with open(data_file, "r") as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            
            parts = line.split()
            obj_id = parts[0]
            
            try:
                ra = float(parts[1])
                dec = float(parts[2])
            except (ValueError, IndexError):
                continue
            
            # Extract base ID
            base_id = extract_base_id(obj_id)
            
            if base_id not in objects:
                objects[base_id] = []
            objects[base_id].append((ra, dec))
    
    # Calculate and print spherical means
    print(f"{'Object ID':<10} {'RA (offset)':<20} {'DEC (offset)':<20}")
    print("-" * 50)
    
    # Sort by base ID (numerical first, then alphabetical)
    def sort_key(base_id):
        # Try to extract numeric part for sorting
        match = re.match(r'^(\d+)', base_id)
        if match:
            return (0, int(match.group(1)), base_id)
        else:
            return (1, 0, base_id)
    
    sorted_ids = sorted(objects.keys(), key=sort_key)
    
    for base_id in sorted_ids:
        coords = objects[base_id]
        ra_mean, dec_mean = spherical_mean(coords)
        print(f"{base_id:<10} {ra_mean:<20.7f} {dec_mean:<20.7f}")


if __name__ == "__main__":
    main()
