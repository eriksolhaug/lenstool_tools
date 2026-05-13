#!/usr/bin/env python3
"""
Extract magnifications from amplification FITS maps at specified object coordinates.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

try:
    from astropy.io import fits
    from astropy.wcs import WCS
    from astropy.coordinates import SkyCoord
    import astropy.units as u
except ImportError:
    raise ImportError("This module requires astropy. Install with: pip install astropy")


def load_magnification_config(config_file: str) -> Dict:
    """
    Load magnification configuration from JSON file.
    
    Args:
        config_file (str): Path to magnification_config.json
        
    Returns:
        dict: Configuration with 'amplification' and 'objects' keys
    """
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config


def sample_mu(coord: SkyCoord, data: np.ndarray, wcs_obj: WCS, use_abs: bool = True) -> float:
    """
    Extract magnification value at a given sky coordinate.
    
    Args:
        coord (SkyCoord): Sky coordinate (RA, Dec) in ICRS frame
        data (np.ndarray): 2D magnification map array
        wcs_obj (WCS): WCS object from FITS header
        use_abs (bool): If True, return absolute value of magnification
        
    Returns:
        float: Magnification value at the coordinate, or np.nan if outside image
    """
    # Convert sky coordinates to pixel coordinates
    x, y = wcs_obj.all_world2pix(coord.ra.deg, coord.dec.deg, 0)
    
    # Round to nearest pixel
    xi, yi = int(np.rint(x)), int(np.rint(y))
    
    # Check bounds
    ny, nx = data.shape
    if 0 <= xi < nx and 0 <= yi < ny:
        val = float(data[yi, xi])
        return abs(val) if use_abs else val
    return np.nan


def extract_magnifications_from_fits(
    ampli_fits_file: Path,
    objects: List[Dict],
    use_abs: bool = True
) -> Dict[str, float]:
    """
    Extract magnifications from a single amplification FITS file.
    
    Args:
        ampli_fits_file (Path): Path to amplification FITS file
        objects (List[Dict]): List of objects with 'object_id', 'ra', 'dec' keys
        use_abs (bool): If True, return absolute value of magnifications
        
    Returns:
        dict: {object_id: magnification_value} for all objects
    """
    # Load FITS file
    try:
        with fits.open(ampli_fits_file) as hdul:
            hdr = hdul[0].header
            data = hdul[0].data.astype(np.float64)
    except Exception as e:
        print(f"Error loading FITS file {ampli_fits_file}: {e}")
        raise
    
    # Extract WCS
    wcs_obj = WCS(hdr).celestial
    
    # Extract magnifications for each object
    magnifications = {}
    for obj in objects:
        coord = SkyCoord(obj['ra'] * u.deg, obj['dec'] * u.deg, frame='icrs')
        mag = sample_mu(coord, data, wcs_obj, use_abs=use_abs)
        magnifications[obj['object_id']] = mag
    
    return magnifications


def create_absolute_value_fits(ampli_dir: str) -> None:
    """
    Create absolute value magnification FITS files from original files.
    
    For each sample_<X>_z<Z>_ampli.fits file, creates a corresponding
    sample_<X>_z<Z>_absampli.fits file containing absolute values.
    
    Args:
        ampli_dir (str): Path to directory containing amplification FITS files
    """
    ampli_path = Path(ampli_dir)
    
    # Find all ampli FITS files (excluding abs variants)
    ampli_files = sorted([f for f in ampli_path.glob('*_ampli.fits') 
                         if not '_absampli.fits' in f.name])
    
    if not ampli_files:
        print("  No amplification FITS files found")
        return
    
    print(f"\nCreating absolute value magnification FITS files...")
    for ampli_file in ampli_files:
        # Generate output filename
        abs_filename = ampli_file.name.replace('_ampli.fits', '_absampli.fits')
        abs_path = ampli_file.parent / abs_filename
        
        # Load original FITS file
        with fits.open(ampli_file) as hdul:
            hdr = hdul[0].header.copy()
            data = hdul[0].data.astype(np.float64)
        
        # Compute absolute values
        abs_data = np.abs(data).astype(np.float32)
        
        # Update header
        hdr['BUNIT'] = 'magnification'
        if 'HISTORY' not in hdr:
            hdr['HISTORY'] = 'Absolute value taken: |mu|'
        else:
            hdr['HISTORY'] = 'Absolute value taken: |mu| (from ' + ampli_file.name + ')'
        
        # Write absolute value FITS file
        fits.writeto(abs_path, abs_data, hdr, overwrite=True)
    
    print(f"  Created {len(ampli_files)} absolute value FITS files")


def process_all_ampli_files(
    ampli_directory: str,
    objects: List[Dict],
    use_abs: bool = True
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Process all amplification FITS files in a directory.
    
    Args:
        ampli_directory (str): Path to directory containing ampli FITS files
        objects (List[Dict]): List of objects with 'object_id', 'ra', 'dec' keys
        use_abs (bool): If True, return absolute value of magnifications
        
    Returns:
        tuple: (DataFrame with magnifications, list of sample names)
    """
    ampli_dir = Path(ampli_directory)
    
    # Find only regular ampli FITS files (exclude absampli variants)
    fits_files = sorted([f for f in ampli_dir.glob('*.fits') 
                         if not '_absampli.fits' in f.name])
    
    if not fits_files:
        print(f"No FITS files found in {ampli_directory}")
        return pd.DataFrame(), []
    
    print(f"Processing {len(fits_files)} amplification FITS files...")
    print(f"Extracting magnifications for {len(objects)} objects...\n")
    
    # Initialize results
    data_rows = []
    sample_names = []
    
    for idx, fits_file in enumerate(fits_files, start=1):
        sample_name = fits_file.stem.split('_')[0] + '_' + fits_file.stem.split('_')[1]
        sample_names.append(sample_name)
        
        try:
            mag_dict = extract_magnifications_from_fits(fits_file, objects, use_abs=use_abs)
            mag_dict['sample'] = sample_name
            mag_dict['fits_file'] = fits_file.name
            data_rows.append(mag_dict)
            
            if idx % max(1, len(fits_files) // 10) == 0 or idx == len(fits_files):
                print(f"  Processed {idx} / {len(fits_files)} files")
        
        except Exception as e:
            print(f"  ERROR processing {fits_file.name}: {e}")
            # Create row with NaN values for failed files
            mag_dict = {obj['object_id']: np.nan for obj in objects}
            mag_dict['sample'] = sample_name
            mag_dict['fits_file'] = fits_file.name
            data_rows.append(mag_dict)
    
    # Create DataFrame
    df = pd.DataFrame(data_rows)
    
    # Reorder columns: sample, fits_file, then object IDs
    object_ids = [obj['object_id'] for obj in objects]
    cols = ['sample', 'fits_file'] + object_ids
    df = df[cols]
    
    return df, sample_names


def extract_magnifications(
    config_file: str,
    output_csv: str = None
) -> pd.DataFrame:
    """
    Main function to extract magnifications from all ampli files.
    
    Args:
        config_file (str): Path to magnification_config.json
        output_csv (str): Optional path to save CSV output
        
    Returns:
        pd.DataFrame: DataFrame with magnifications for all samples and objects
    """
    # Load configuration
    config = load_magnification_config(config_file)
    ampli_dir = config['amplification']['directory']
    objects = config['objects']
    
    # ampli_dir is relative to current working directory, not config file location
    # (config file is typically in config/ subdir, but ampli output is at root level)
    
    # Process all files (using absolute values for magnification extraction)
    df, sample_names = process_all_ampli_files(ampli_dir, objects, use_abs=True)
    
    # Save to CSV if requested
    if output_csv:
        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"\nMagnifications saved to: {output_csv}")
    
    print(f"\n{'='*60}")
    print(f"Magnification Extraction Summary")
    print(f"{'='*60}")
    print(f"Total samples processed:  {len(df)}")
    print(f"Objects extracted:        {len(objects)}")
    print(f"Configuration file:       {config_file}")
    if output_csv:
        print(f"Output CSV file:          {output_csv}")
    print(f"\nDataFrame shape: {df.shape}")
    print(f"\nFirst few rows:")
    print(df.head())
    
    return df


def main():
    """Command-line interface for magnification extraction."""
    if len(sys.argv) < 2:
        print("Usage: extract-magnifications <config_file> [output_csv]")
        print("\nRequired:")
        print("  config_file    - Path to magnification_config.json")
        print("\nOptional:")
        print("  output_csv     - Path to save results (default: statistics/magnification/magnifications.csv)")
        print("\nExample:")
        print("  extract-magnifications tests/magnification_config.json statistics/magnification/magnifications.csv")
        sys.exit(1)
    
    config_file = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) > 2 else 'statistics/magnification/magnifications.csv'
    
    df = extract_magnifications(config_file, output_csv)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
