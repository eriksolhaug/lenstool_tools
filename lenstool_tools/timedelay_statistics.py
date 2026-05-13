#!/usr/bin/env python
"""
Extract time delay statistics from time delay FITS files at specific image locations.

Computes statistics (median, mean, confidence intervals) of time delays
at image positions A1, A2, A3 for all samples, including the best-fit model.
"""

import os
import sys
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u

# Add parent directory to path for importing coord_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from single_model.coord_utils import parse_coordinate_string
from lenstool_tools.extract_timedelays import read_image_dat_coordinates


def load_config(config_path):
    """Load configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)


def sample_value_at_coord(coord_input, timedelay_data, wcs_obj):
    """
    Sample time delay value at a sky coordinate.
    
    Args:
        coord_input: Either a coordinate string (e.g., "11h53m19.410s +07d55m47.68s")
                    or a list/tuple of decimal coordinates [RA, Dec] in degrees
        timedelay_data: 2D array of time delay values
        wcs_obj: WCS object for coordinate transformation
        
    Returns:
        Float time delay value or np.nan if out of bounds
    """
    try:
        # Handle both decimal coordinates (list/tuple) and sexagesimal strings
        if isinstance(coord_input, (list, tuple)):
            # Decimal coordinates [RA, Dec] in degrees
            ra_deg, dec_deg = coord_input[0], coord_input[1]
        else:
            # Sexagesimal coordinate string
            coord = parse_coordinate_string(coord_input)
            ra_deg = coord.ra.deg
            dec_deg = coord.dec.deg
        
        x, y = wcs_obj.all_world2pix(ra_deg, dec_deg, 0)
        xi, yi = int(np.rint(x)), int(np.rint(y))
        ny, nx = timedelay_data.shape
        if 0 <= xi < nx and 0 <= yi < ny:
            return float(timedelay_data[yi, xi])
        else:
            return np.nan
    except Exception as e:
        print(f"    Warning: Could not sample at {coord_input}: {e}")
        return np.nan


def extract_timedelays_at_images(timedelay_fits_dir, config, output_dir, z_source=None):
    """
    Extract time delay values at image locations for all samples.
    
    Args:
        timedelay_fits_dir: Directory containing time delay FITS files
        config: Configuration dictionary with image locations
        output_dir: Directory to save output statistics
        z_source: Source redshift filter (e.g., 1.524)
    """
    
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get image locations from config
    image_locations = config.get('image_locations', {})
    
    # Check if we should infer image locations from image.dat
    if image_locations == "infer_from_image.dat":
        # For statistics, we need a reference timedelay file to read image.dat from
        # Use the best-fit file if available, otherwise use the first sample
        timedelay_dir = Path(timedelay_fits_dir)
        timedelay_files = sorted(timedelay_dir.glob('*_timedelay.fits'))
        
        if z_source is not None:
            z_str = f'_z{z_source:.3f}'
            timedelay_files = [f for f in timedelay_files if z_str in f.name]
        
        if not timedelay_files:
            print(f"ERROR: No time delay FITS files found to infer image.dat")
            return
        
        # Get reference file (prefer best-fit)
        ref_file = None
        for f in timedelay_files:
            if 'best' in f.name:
                ref_file = f
                break
        if ref_file is None:
            ref_file = timedelay_files[0]
        
        # Extract sample name and construct image.dat path
        poten_filename = ref_file.name.replace('_timedelay.fits', '')
        image_dat_dir = config.get('image_dat_directory', 'output/poten/selected_output')
        image_dat_path = Path(image_dat_dir) / f"{poten_filename}_image.dat"
        
        # Get ID mapping and mode from config
        image_object_ids = config.get('image_object_ids', ['A1', 'A2', 'A3'])
        id_mapping = config.get('image_dat_object_id_mapping', {oid: oid for oid in image_object_ids})
        image_dat_mode = config.get('image_dat_mode', 'true')
        
        print(f"Reading image coordinates from: {image_dat_path.name}")
        image_coords_dict = read_image_dat_coordinates(str(image_dat_path), image_object_ids, id_mapping, mode=image_dat_mode)
        
        if image_coords_dict is None:
            print(f"WARNING: Could not read image.dat, using fallback from config")
            image_locations = config.get('image_locations_default', {})
            if not image_locations:
                print("ERROR: No fallback image_locations_default in config")
                return
        else:
            image_locations = image_coords_dict
    
    if not image_locations:
        print("ERROR: No image_locations in config")
        return
    
    print(f"Extracting time delays at image positions: {list(image_locations.keys())}")
    
    # Get list of timedelay files
    timedelay_dir = Path(timedelay_fits_dir)
    timedelay_files = sorted(timedelay_dir.glob('*_timedelay.fits'))
    
    if z_source is not None:
        z_str = f'_z{z_source:.3f}'
        timedelay_files = [f for f in timedelay_files if z_str in f.name]
    
    if not timedelay_files:
        print(f"No time delay FITS files found in {timedelay_fits_dir}")
        return
    
    # Separate best-fit from regular samples
    best_fit_file = None
    sample_files = []
    for f in timedelay_files:
        if 'best' in f.name:
            best_fit_file = f
        else:
            sample_files.append(f)
    
    print(f"Found {len(sample_files)} sample files")
    if best_fit_file:
        print(f"Found best-fit file: {best_fit_file.name}")
    
    # Dictionary to store time delays for each image
    timedelays_by_image = {img_name: [] for img_name in image_locations.keys()}
    best_timedelays = {}
    
    # Process each file and extract time delays at image locations
    for i, td_file in enumerate(sample_files, 1):
        try:
            with fits.open(td_file) as hdul:
                # Use EXT2 (DAYS_REL) - time delays relative to leading image
                td_data = hdul[2].data
                td_header = hdul[2].header
                wcs_td = WCS(td_header).celestial
                
                # Extract time delays at each image location
                for img_name, img_coord in image_locations.items():
                    tau = sample_value_at_coord(img_coord, td_data, wcs_td)
                    if np.isfinite(tau):
                        timedelays_by_image[img_name].append(tau)
        except Exception as e:
            print(f"  Warning: Could not process {td_file.name}: {e}")
            continue
    
    # Process best-fit file
    if best_fit_file:
        try:
            with fits.open(best_fit_file) as hdul:
                # Use EXT2 (DAYS_REL) - time delays relative to leading image
                td_data = hdul[2].data
                td_header = hdul[2].header
                wcs_td = WCS(td_header).celestial
                
                for img_name, img_coord in image_locations.items():
                    tau = sample_value_at_coord(img_coord, td_data, wcs_td)
                    best_timedelays[img_name] = tau
        except Exception as e:
            print(f"  Warning: Could not process best-fit file: {e}")
    
    # Generate statistics and histograms for each image
    generate_statistics_and_histograms(
        timedelays_by_image, best_timedelays, image_locations, 
        output_dir, z_source
    )


def generate_statistics_and_histograms(timedelays_by_image, best_timedelays, 
                                       image_locations, output_dir, z_source):
    """
    Generate statistics CSV and histograms for time delays at each image.
    
    Args:
        timedelays_by_image: Dict mapping image names to arrays of time delays
        best_timedelays: Dict mapping image names to best-fit time delays
        image_locations: Dict with image coordinates
        output_dir: Output directory
        z_source: Source redshift (for filename)
    """
    
    output_dir = Path(output_dir)
    
    # Compute statistics
    z_str = f"_z{z_source:.3f}" if z_source else ""
    
    # Create report file
    report_path = output_dir / f"timedelay_report{z_str}.txt"
    csv_path = output_dir / f"timedelay_statistics{z_str}.csv"
    
    # Build report content in memory first
    report_lines = []
    
    with open(report_path, 'w') as f:
        header = "=" * 90 + "\n" + "TIME DELAY STATISTICS REPORT\n" + "=" * 90 + "\n\n"
        f.write(header)
        report_lines.append(header)
        
        # Create CSV file
        with open(csv_path, 'w') as csv_f:
            csv_f.write("image,statistic,value\n")
            
            for img_name, img_coord in image_locations.items():
                timedelays = np.array(timedelays_by_image[img_name])
                
                if len(timedelays) == 0:
                    print(f"Warning: No valid time delays for {img_name}")
                    continue
                
                # Compute statistics
                median_tau = np.median(timedelays)
                mean_tau = np.mean(timedelays)
                std_tau = np.std(timedelays)
                
                # 1-sigma confidence interval
                lower_68 = np.percentile(timedelays, 15.865)
                upper_68 = np.percentile(timedelays, 84.135)
                lower_err = median_tau - lower_68
                upper_err = upper_68 - median_tau
                
                best_tau = best_timedelays.get(img_name, np.nan)
                
                # Build section lines
                section = "-" * 90 + "\n"
                section += f"Image: {img_name}\n"
                section += f"Coordinate: {img_coord}\n"
                section += "-" * 90 + "\n\n"
                section += "SUMMARY STATISTICS\n"
                section += f"Best-fit time delay:      {best_tau:15.4f} days\n"
                section += f"Median time delay:        {median_tau:15.4f} days\n"
                section += f"Mean time delay:          {mean_tau:15.4f} days\n"
                section += f"Std deviation:            {std_tau:15.4f} days\n\n"
                section += "1.0σ Confidence Interval:\n"
                section += f"  Lower bound:            {lower_68:15.4f} days\n"
                section += f"  Upper bound:            {upper_68:15.4f} days\n"
                section += f"  Lower error (below median): {lower_err:11.4f} days\n"
                section += f"  Upper error (above median): {upper_err:11.4f} days\n\n"
                section += "INTERPRETATION\n"
                section += f"The time delay at image {img_name} relative to the leading image is:\n"
                section += f"  τ = {median_tau:.1f} (+{upper_err:.1f}) ({-lower_err:.1f}) days\n\n"
                
                f.write(section)
                report_lines.append(section)
                
                # Write to CSV
                csv_f.write(f"{img_name},best,{best_tau:.4f}\n")
                csv_f.write(f"{img_name},median,{median_tau:.4f}\n")
                csv_f.write(f"{img_name},mean,{mean_tau:.4f}\n")
                csv_f.write(f"{img_name},std,{std_tau:.4f}\n")
                csv_f.write(f"{img_name},lower_1sigma,{lower_68:.4f}\n")
                csv_f.write(f"{img_name},upper_1sigma,{upper_68:.4f}\n")
    
    # Create histograms for each image
    fig, axes = plt.subplots(1, len(image_locations), figsize=(5*len(image_locations), 5))
    
    if len(image_locations) == 1:
        axes = [axes]
    
    for ax, (img_name, img_coord) in zip(axes, image_locations.items()):
        timedelays = np.array(timedelays_by_image[img_name])
        best_tau = best_timedelays.get(img_name, np.nan)
        
        # Plot histogram
        ax.hist(timedelays, bins=20, alpha=0.7, color='steelblue', edgecolor='black')
        
        # Add statistics lines
        median_tau = np.median(timedelays)
        ax.axvline(median_tau, color='red', linestyle='--', linewidth=2, label=f'Median: {median_tau:.1f} d')
        
        if np.isfinite(best_tau):
            ax.axvline(best_tau, color='green', linestyle='-.', linewidth=2, label=f'Best-fit: {best_tau:.1f} d')
        
        ax.set_xlabel('Time Delay (days)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Number of Samples', fontsize=12, fontweight='bold')
        ax.set_title(f'Image {img_name}', fontsize=13, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    hist_path = output_dir / f"timedelay_distribution{z_str}.png"
    plt.savefig(hist_path, dpi=150, bbox_inches='tight')
    print(f"✓ Histogram saved to: {hist_path}")
    plt.close()
    
    # Print report to stdout
    print("\n" + "=" * 90)
    print("".join(report_lines), end="")
    print("=" * 90 + "\n")
    
    print(f"✓ Statistics CSV saved to: {csv_path}")
    print(f"✓ Report saved to: {report_path}")


def main():
    """Main entry point for time delay statistics extraction."""
    parser = argparse.ArgumentParser(
        description="Extract time delay statistics at image locations"
    )
    parser.add_argument(
        'timedelay_dir',
        help='Directory containing time delay FITS files'
    )
    parser.add_argument(
        'config_file',
        help='Configuration file (timedelay_config.json)'
    )
    parser.add_argument(
        '-output',
        default='statistics/timedelay',
        help='Output directory for statistics (default: statistics/timedelay)'
    )
    parser.add_argument(
        '-z',
        type=float,
        default=None,
        help='Source redshift filter (only process files with this redshift)'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config_file)
    
    print(f"Extracting time delay statistics from: {args.timedelay_dir}")
    
    # Extract time delays at image locations
    extract_timedelays_at_images(
        args.timedelay_dir, 
        config, 
        args.output,
        z_source=args.z
    )
    
    print(f"\n✓ Time delay statistics saved to: {args.output}")


if __name__ == '__main__':
    main()
