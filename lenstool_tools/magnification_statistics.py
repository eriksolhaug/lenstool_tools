#!/usr/bin/env python3
"""
Generate magnification statistics and confidence intervals from extracted magnifications.
Creates histograms and summary statistics for each object, including best-fit values.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    from matplotlib.ticker import FuncFormatter
except ImportError:
    raise ImportError("This module requires matplotlib. Install with: pip install matplotlib")

try:
    from astropy.io import fits
    from astropy.wcs import WCS
    from astropy.visualization import ZScaleInterval
    from astropy.coordinates import SkyCoord
    import astropy.units as u
except ImportError:
    raise ImportError("This module requires astropy. Install with: pip install astropy")


def calculate_confidence_interval(data: np.ndarray, sigma: float = 1.0) -> Tuple[float, float, float]:
    """
    Calculate asymmetric confidence interval for a given sigma level using percentiles.
    
    Args:
        data (np.ndarray): Array of values (excluding NaN)
        sigma (float): Number of standard deviations (default 1.0 = 68.3%)
        
    Returns:
        tuple: (median, error_negative, error_positive)
            - median: The median value
            - error_negative: Distance below median to lower percentile (positive value)
            - error_positive: Distance above median to upper percentile (positive value)
    
    For sigma=1.0, uses 68.3% confidence interval (lower=15.85%, upper=84.15% percentiles)
    For sigma=2.0, uses 95.4% confidence interval (lower=2.3%, upper=97.7% percentiles)
    """
    median = np.nanmedian(data)
    
    # Convert sigma to percentile bounds
    # 1 sigma = 68.3% CI → use 15.85% and 84.15% percentiles
    # 2 sigma = 95.4% CI → use 2.3% and 97.7% percentiles
    confidence_level = {
        1.0: (15.85, 84.15),
        2.0: (2.3, 97.7),
        3.0: (0.135, 99.865),
    }
    
    # Default to symmetric std-based interval if sigma not in lookup
    if sigma in confidence_level:
        lower_percentile, upper_percentile = confidence_level[sigma]
        lower_bound = np.nanpercentile(data, lower_percentile)
        upper_bound = np.nanpercentile(data, upper_percentile)
    else:
        # Fallback to std-based symmetric interval
        std = np.nanstd(data)
        lower_bound = median - sigma * std
        upper_bound = median + sigma * std
    
    error_negative = median - lower_bound
    error_positive = upper_bound - median
    
    return median, error_negative, error_positive



def compute_statistics(
    magnifications_csv: str,
    sigma: float = 1.0,
    best_magnifications: Optional[Dict[str, float]] = None,
    clip_sigma: Optional[float] = None
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Compute statistics (median, mean, confidence intervals, best values) for all objects.
    
    Args:
        magnifications_csv (str): Path to magnifications.csv
        sigma (float): Number of standard deviations for confidence interval
        best_magnifications (dict, optional): Best magnification values for each object
        clip_sigma (float, optional): Number of sigma for outlier rejection via sigma clipping.
                                     If provided, removes values >clip_sigma from median before stats.
        
    Returns:
        tuple: (statistics_dataframe, clipping_summary_dict)
            - statistics_dataframe: Statistics with rows for median, mean, best, and confidence intervals
            - clipping_summary_dict: Dict with keys as object_ids and values as number of samples clipped
    """
    # Load magnifications
    df = pd.read_csv(magnifications_csv)
    
    # Get object columns (exclude 'sample' and 'fits_file')
    object_cols = [col for col in df.columns if col not in ['sample', 'fits_file']]
    
    # Initialize statistics dictionary
    stats = {
        'statistic': [
            'best',
            'median',
            'mean',
            f'error_lower_{sigma}sigma',
            f'error_upper_{sigma}sigma'
        ]
    }
    
    # Track clipping information
    clipping_summary = {}
    
    # Calculate statistics for each object
    for obj_id in object_cols:
        data = df[obj_id].values
        
        # Remove NaN values
        valid_data = data[~np.isnan(data)]
        
        if len(valid_data) == 0:
            stats[obj_id] = [np.nan, np.nan, np.nan, np.nan, np.nan]
            clipping_summary[obj_id] = 0
            continue
        
        # Apply sigma clipping if requested
        clipped_data = valid_data
        num_clipped = 0
        if clip_sigma is not None and clip_sigma > 0:
            median_val = np.nanmedian(valid_data)
            mad = np.nanmedian(np.abs(valid_data - median_val))
            # MAD to sigma conversion (for normal distribution: sigma ≈ MAD / 0.6745)
            sigma_est = mad / 0.6745 if mad > 0 else 1.0
            
            # Keep only values within clip_sigma from median
            lower_bound = median_val - clip_sigma * sigma_est
            upper_bound = median_val + clip_sigma * sigma_est
            mask = (valid_data >= lower_bound) & (valid_data <= upper_bound)
            clipped_data = valid_data[mask]
            num_clipped = len(valid_data) - len(clipped_data)
        
        clipping_summary[obj_id] = num_clipped
        
        if len(clipped_data) == 0:
            stats[obj_id] = [np.nan, np.nan, np.nan, np.nan, np.nan]
            continue
        
        median = np.nanmedian(clipped_data)
        mean = np.nanmean(clipped_data)
        _, error_lower, error_upper = calculate_confidence_interval(clipped_data, sigma=sigma)
        
        # Get best value if provided
        best = best_magnifications[obj_id] if best_magnifications and obj_id in best_magnifications else np.nan
        
        stats[obj_id] = [best, median, mean, error_lower, error_upper]
    
    # Create DataFrame
    stats_df = pd.DataFrame(stats)
    
    return stats_df, clipping_summary


def create_histogram(
    data: np.ndarray,
    object_id: str,
    output_dir: Path,
    sigma: float = 1.0,
    bins: int = 20,
    best_value: Optional[float] = None
) -> None:
    """
    Create and save a histogram for a single object's magnification distribution.
    
    Args:
        data (np.ndarray): Magnification values
        object_id (str): Object identifier
        output_dir (Path): Directory to save histogram
        sigma (float): Number of standard deviations for confidence interval
        bins (int): Number of histogram bins
        best_value (float, optional): Best-fit magnification value to plot
    """
    # Remove NaN values
    valid_data = data[~np.isnan(data)]
    
    if len(valid_data) == 0:
        print(f"  Skipping {object_id}: no valid data")
        return
    
    # Calculate statistics
    median = np.nanmedian(valid_data)
    mean = np.nanmean(valid_data)
    std = np.nanstd(valid_data)
    _, error_lower, error_upper = calculate_confidence_interval(valid_data, sigma=sigma)
    
    lower_ci = median - error_lower
    upper_ci = median + error_upper
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot histogram
    counts, edges, patches = ax.hist(valid_data, bins=bins, alpha=0.7, color='steelblue', edgecolor='black')
    
    # Add vertical lines for statistics
    ax.axvline(median, color='red', linestyle='--', linewidth=2, label=f'Median: {median:.3f}')
    ax.axvline(mean, color='green', linestyle='--', linewidth=2, label=f'Mean: {mean:.3f}')
    
    # Plot best value as a vertical line with marker
    if best_value is not None and not np.isnan(best_value):
        ax.axvline(best_value, color='purple', linestyle=':', linewidth=2.5, 
                   label=f'Best-fit: {best_value:.3f}')
    
    # Shade confidence interval
    ax.axvspan(lower_ci, upper_ci, alpha=0.2, color='yellow', 
               label=f'{sigma:.1f}σ CI: [{lower_ci:.3f}, {upper_ci:.3f}]')
    
    # Labels and title
    ax.set_xlabel('Magnification', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title(f'Magnification Distribution: {object_id}\n(N={len(valid_data)}, σ={std:.3f})', 
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=10, loc='upper right')
    ax.grid(True, alpha=0.3)
    
    # Save figure
    output_file = output_dir / f'{object_id}_histogram.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  Saved: {output_file.name}")


def extract_best_magnifications(
    ampli_directory: str,
    objects: List[Dict],
    redshift: Optional[str] = None
) -> Dict[str, float]:
    """
    Extract magnifications from the best-fit amplification FITS file.
    
    Args:
        ampli_directory (str): Path to directory containing ampli FITS files
        objects (List[Dict]): List of objects with 'object_id', 'ra', 'dec' keys
        redshift (str, optional): Redshift suffix to match (e.g., "1.524")
        
    Returns:
        dict: {object_id: magnification_value} for all objects from best-fit
    """
    ampli_dir = Path(ampli_directory)
    
    # Verify directory exists
    if not ampli_dir.exists():
        print(f"  Warning: Amplification directory not found: {ampli_dir.resolve()}")
        return {}
    
    # Find sample_best FITS file with matching redshift
    if redshift:
        pattern = f'sample_best_z{redshift}_ampli.fits'
    else:
        pattern = 'sample_best_ampli.fits'
    
    best_fits_files = list(ampli_dir.glob(pattern))
    
    if not best_fits_files:
        print(f"  Warning: No best-fit amplification file found matching pattern: {pattern}")
        print(f"           Looked in: {ampli_dir.resolve()}")
        return {}
    
    if len(best_fits_files) > 1:
        print(f"  Warning: Multiple best-fit files found, using first: {best_fits_files[0].name}")
    
    best_fits_file = best_fits_files[0]
    
    try:
        # Load FITS file
        with fits.open(best_fits_file) as hdul:
            hdr = hdul[0].header
            data = hdul[0].data.astype(np.float64)
        
        # Extract WCS
        wcs_obj = WCS(hdr).celestial
        
        # Extract magnifications for each object
        magnifications = {}
        for obj in objects:
            coord = SkyCoord(obj['ra'] * u.deg, obj['dec'] * u.deg, frame='icrs')
            
            # Convert sky coordinates to pixel coordinates
            x, y = wcs_obj.all_world2pix(coord.ra.deg, coord.dec.deg, 0)
            
            # Round to nearest pixel
            xi, yi = int(np.rint(x)), int(np.rint(y))
            
            # Check bounds and extract value
            ny, nx = data.shape
            if 0 <= xi < nx and 0 <= yi < ny:
                val = float(data[yi, xi])
                magnifications[obj['object_id']] = abs(val)
            else:
                magnifications[obj['object_id']] = np.nan
        
        print(f"  ✓ Extracted best magnifications from: {best_fits_file.name}")
        return magnifications
    
    except Exception as e:
        print(f"  Error extracting best magnifications from {best_fits_file.name}: {e}")
        return {}


def create_report_file(
    stats_df: pd.DataFrame,
    output_path: Path,
    sigma: float = 1.0,
    redshift: Optional[str] = None
) -> Path:
    """
    Create a human-readable report file with magnification statistics.
    
    Args:
        stats_df (pd.DataFrame): Statistics dataframe
        output_path (Path): Directory to save report
        sigma (float): Sigma level used for confidence intervals
        redshift (str, optional): Redshift of the data
        
    Returns:
        Path: Path to the created report file
    """
    # Determine report filename
    if redshift:
        report_file = output_path / f'magnification_report_z{redshift}.txt'
    else:
        report_file = output_path / 'magnification_report.txt'
    
    with open(report_file, 'w') as f:
        f.write("=" * 90 + "\n")
        f.write("MAGNIFICATION STATISTICS REPORT\n")
        f.write("=" * 90 + "\n")
        if redshift:
            f.write(f"Source Redshift: z = {redshift}\n")
        f.write(f"Confidence Level: {sigma:.1f}σ ({100*(1-np.exp(-sigma**2/2)):.1f}% confidence)\n")
        f.write("\n")
        
        # Get object columns
        object_cols = [col for col in stats_df.columns if col != 'statistic']
        
        # Write detailed table
        f.write("SUMMARY STATISTICS\n")
        f.write("-" * 90 + "\n")
        f.write(f"{'Object':<12} {'Best':<12} {'Median':<12} {'Mean':<12} ")
        f.write(f"{'Lower Error':<14} {'Upper Error':<14}\n")
        f.write("-" * 90 + "\n")
        
        for obj_id in object_cols:
            best = stats_df[stats_df['statistic'] == 'best'][obj_id].values[0]
            median = stats_df[stats_df['statistic'] == 'median'][obj_id].values[0]
            mean = stats_df[stats_df['statistic'] == 'mean'][obj_id].values[0]
            
            error_lower_key = f'error_lower_{sigma}sigma'
            error_upper_key = f'error_upper_{sigma}sigma'
            error_lower = stats_df[stats_df['statistic'] == error_lower_key][obj_id].values[0]
            error_upper = stats_df[stats_df['statistic'] == error_upper_key][obj_id].values[0]
            
            # Format values
            best_str = f"{best:.3f}" if not np.isnan(best) else "N/A"
            median_str = f"{median:.3f}" if not np.isnan(median) else "N/A"
            mean_str = f"{mean:.3f}" if not np.isnan(mean) else "N/A"
            error_lower_str = f"{error_lower:.3f}" if not np.isnan(error_lower) else "N/A"
            error_upper_str = f"{error_upper:.3f}" if not np.isnan(error_upper) else "N/A"
            
            f.write(f"{obj_id:<12} {best_str:<12} {median_str:<12} {mean_str:<12} ")
            f.write(f"{error_lower_str:<14} {error_upper_str:<14}\n")
        
        f.write("-" * 90 + "\n\n")
        
        # Write detailed statistics for each object
        f.write("DETAILED STATISTICS BY OBJECT\n")
        f.write("=" * 90 + "\n\n")
        
        for obj_id in object_cols:
            f.write(f"Object: {obj_id}\n")
            f.write("-" * 90 + "\n")
            
            best = stats_df[stats_df['statistic'] == 'best'][obj_id].values[0]
            median = stats_df[stats_df['statistic'] == 'median'][obj_id].values[0]
            mean = stats_df[stats_df['statistic'] == 'mean'][obj_id].values[0]
            
            error_lower_key = f'error_lower_{sigma}sigma'
            error_upper_key = f'error_upper_{sigma}sigma'
            error_lower = stats_df[stats_df['statistic'] == error_lower_key][obj_id].values[0]
            error_upper = stats_df[stats_df['statistic'] == error_upper_key][obj_id].values[0]
            
            if not np.isnan(best):
                f.write(f"  Best-fit magnification:        {best:.6f}\n")
            f.write(f"  Median magnification:          {median:.6f}\n")
            f.write(f"  Mean magnification:            {mean:.6f}\n")
            f.write(f"  \n")
            f.write(f"  {sigma:.1f}σ Confidence Interval:\n")
            f.write(f"    Lower error (below median):  -{error_lower:.6f}\n")
            f.write(f"    Upper error (above median):  +{error_upper:.6f}\n")
            f.write(f"    Range: [{median - error_lower:.6f}, {median + error_upper:.6f}]\n")
            f.write("\n")
        
        f.write("=" * 90 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 90 + "\n")
    
    return report_file


def create_magnification_map_visualization(
    ampli_fits_file: Path,
    objects: List[Dict],
    output_dir: Path,
    redshift: Optional[str] = None
) -> None:
    """
    Create an annotated magnification map visualization with object locations.
    
    Args:
        ampli_fits_file (Path): Path to amplification FITS file
        objects (List[Dict]): List of objects with 'object_id', 'ra', 'dec' keys
        output_dir (Path): Directory to save the visualization
        redshift (str, optional): Redshift to include in output filename (e.g., '1.939')
    """
    try:
        # Load FITS file
        with fits.open(ampli_fits_file) as hdul:
            hdr = hdul[0].header
            data = hdul[0].data.astype(np.float64)
        
        # Extract WCS
        wcs = WCS(hdr).celestial
        
        # Create figure with WCS projection
        fig = plt.figure(figsize=(14, 12))
        ax = fig.add_subplot(111, projection=wcs)
        
        # Apply ZScale normalization
        zscale = ZScaleInterval()
        vmin, vmax = zscale.get_limits(data)
        
        # Display image with rainbow colormap
        im = ax.imshow(data, origin='lower', cmap='rainbow', vmin=vmin, vmax=vmax)
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, label='Magnification', shrink=0.8)
        
        # Set up axes with RA/Dec
        ax.set_xlabel('Right Ascension', fontsize=12)
        ax.set_ylabel('Declination', fontsize=12)
        ax.set_title(f'Magnification Map: {ampli_fits_file.stem}\nwith Object Locations', 
                    fontsize=14, fontweight='bold')
        
        # Add tick marks on all sides and inside
        ax.tick_params(which='both', direction='in', length=6, width=1.5)
        
        # Plot object locations
        for obj in objects:
            coord = SkyCoord(obj['ra'] * u.deg, obj['dec'] * u.deg, frame='icrs')
            x, y = wcs.world_to_pixel(coord)
            
            # Check if coordinate is within bounds
            if 0 <= x < data.shape[1] and 0 <= y < data.shape[0]:
                # Plot X marker in black
                ax.plot(x, y, 'kx', markersize=20, markeredgewidth=2.5, label=None)
                
                # Add text annotation in black with no box
                ax.text(x + 30, y + 30, obj['object_id'], 
                       fontsize=11, fontweight='bold', color='black')
        
        # Save figure as PDF
        sample_name = ampli_fits_file.stem.rsplit('_', 2)[0]
        if redshift:
            output_file = output_dir / f'{sample_name}_z{redshift}_magnification_map.pdf'
        else:
            output_file = output_dir / f'{sample_name}_magnification_map.pdf'
        plt.savefig(output_file, dpi=150, bbox_inches='tight', format='pdf')
        plt.close()
        
    except Exception as e:
        print(f"  Error creating visualization for {ampli_fits_file.name}: {e}")


def generate_statistics_and_histograms(
    magnifications_csv: str,
    output_dir: str = 'statistics/magnification',
    sigma: float = 1.0,
    bins: int = 20,
    redshift: Optional[str] = None,
    ampli_directory: str = None,
    config_file: str = None,
    clip_sigma: Optional[float] = None,
    num_maps: Optional[int] = None
) -> Tuple[pd.DataFrame, Path]:
    """
    Generate statistics, histograms, and magnification maps for magnification data.
    
    Args:
        magnifications_csv (str): Path to magnifications.csv
        output_dir (str): Output directory for histograms and statistics
        sigma (float): Number of standard deviations for confidence interval
        bins (int): Number of histogram bins
        redshift (str, optional): Redshift suffix to match for file filtering
        ampli_directory (str): Path to directory containing ampli FITS files
        config_file (str): Path to magnification_config.json for object coordinates
        clip_sigma (float, optional): Sigma threshold for outlier rejection. If provided,
                                     removes values >clip_sigma from median before stats.
        num_maps (int, optional): Number of magnification maps to generate. If None, generates all.
        
    Returns:
        tuple: (statistics_dataframe, output_directory_path)
    """
    # Load magnifications
    df = pd.read_csv(magnifications_csv)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get object columns
    object_cols = [col for col in df.columns if col not in ['sample', 'fits_file']]
    
    print(f"\nGenerating statistics and histograms for {len(object_cols)} objects...")
    print(f"Sigma level: {sigma:.1f} (confidence interval)")
    if redshift:
        print(f"Redshift: z = {redshift}")
    print(f"Output directory: {output_path.resolve()}\n")
    
    # Extract best magnifications if config and ampli directory provided
    best_magnifications = {}
    if config_file and ampli_directory:
        print("Extracting best-fit magnifications...")
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                print(f"  Warning: Config file not found: {config_path.resolve()}")
                print(f"  Skipping best-fit magnification extraction")
            else:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                objects = config.get('objects', [])
                if not objects:
                    print(f"  Warning: No 'objects' found in config file")
                else:
                    best_magnifications = extract_best_magnifications(
                        ampli_directory, objects, redshift=redshift
                    )
                    if best_magnifications:
                        print(f"  Extracted magnifications for {len(best_magnifications)} objects")
        except Exception as e:
            print(f"  Warning: Could not extract best magnifications: {e}")
    
    # Create histograms
    print("\nCreating histograms:")
    for obj_id in object_cols:
        data = df[obj_id].values
        best_value = best_magnifications.get(obj_id) if best_magnifications else None
        create_histogram(data, obj_id, output_path, sigma=sigma, bins=bins, best_value=best_value)
    
    # Create magnification map visualizations if ampli_directory and config are provided
    if ampli_directory and config_file:
        print("\nCreating magnification map visualizations:")
        
        # Create maps subdirectory
        maps_dir = output_path / 'magnification_maps'
        maps_dir.mkdir(exist_ok=True)
        
        # Load object coordinates from config
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            objects = config['objects']
            
            # Get ampli files matching redshift if specified
            ampli_path = Path(ampli_directory)
            if redshift:
                pattern = f'*_z{redshift}_ampli.fits'
            else:
                pattern = '*_ampli.fits'
            fits_files = sorted(ampli_path.glob(pattern))
            
            # Create maps for a subset or all files
            maps_to_create = num_maps if num_maps is not None else len(fits_files)
            if maps_to_create > 0:
                print(f"  Creating visualizations for {maps_to_create} samples...")
                
                for idx, fits_file in enumerate(fits_files[:maps_to_create]):
                    create_magnification_map_visualization(fits_file, objects, maps_dir, redshift)
                    if (idx + 1) % max(1, maps_to_create // 5) == 0 or idx == maps_to_create - 1:
                        print(f"    Completed {idx + 1} / {maps_to_create} visualizations")
        
        except Exception as e:
            print(f"  Warning: Could not create magnification maps: {e}")
    
    # Compute statistics
    print("\nComputing statistics...")
    if clip_sigma is not None and clip_sigma > 0:
        print(f"Applying sigma-clipping (threshold: {clip_sigma:.1f}σ)...")
    stats_df, clipping_summary = compute_statistics(magnifications_csv, sigma=sigma, 
                                                     best_magnifications=best_magnifications,
                                                     clip_sigma=clip_sigma)
    
    # Report clipping summary if sigma-clipping was applied
    if clip_sigma is not None and clip_sigma > 0:
        total_clipped = sum(clipping_summary.values())
        if total_clipped > 0:
            print(f"Clipped samples:")
            for obj_id, num_clipped in clipping_summary.items():
                if num_clipped > 0:
                    print(f"  {obj_id}: {num_clipped} sample(s)")
            print(f"Total clipped: {total_clipped} sample(s)")
    
    # Save statistics to CSV
    if redshift:
        stats_csv = output_path / f'magnification_statistics_z{redshift}.csv'
    else:
        stats_csv = output_path / 'magnification_statistics.csv'
    stats_df.to_csv(stats_csv, index=False)
    print(f"Saved statistics CSV: {stats_csv.name}")
    
    # Create readable report file
    report_file = create_report_file(stats_df, output_path, sigma=sigma, redshift=redshift)
    print(f"Saved report: {report_file.name}\n")
    
    return stats_df, output_path


def main():
    """Command-line interface for magnification statistics."""
    # Check for help flag first
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Usage: magnification-statistics <magnifications_csv> [OPTIONS]")
        print("\nRequired:")
        print("  magnifications_csv  - Path to magnifications.csv")
        print("\nOptional:")
        print("  -redshift Z         - Source redshift (e.g., 1.524) for filtering FITS files")
        print("  -output DIR         - Output directory (default: statistics/magnification)")
        print("  -sigma SIGMA        - Confidence interval in sigma (default: 1.0 = 68%)")
        print("  -bins BINS          - Histogram bins (default: 20)")
        print("  -num_maps N         - Number of magnification maps to generate (default: all)")
        print("  -ampli DIR          - Directory with amplification FITS files (for maps and best values)")
        print("  -config FILE        - magnification_config.json (for object coordinates)")
        print("  -clip SIGMA         - Sigma threshold for outlier rejection (e.g., 3.0 for 3σ clipping)")
        print("\nExamples:")
        print("  magnification-statistics magnifications.csv")
        print("  magnification-statistics magnifications.csv -redshift 1.524")
        print("  magnification-statistics magnifications.csv -redshift 1.524 -sigma 2.0")
        print("  magnification-statistics magnifications.csv -redshift 1.524 -clip 3.0")
        print("  magnification-statistics magnifications.csv -redshift 1.524 -ampli output/ampli -config ../tests/magnification_config.json")
        sys.exit(0)
    
    if len(sys.argv) < 2:
        print("Usage: magnification-statistics <magnifications_csv> [OPTIONS]")
        print("\nRequired:")
        print("  magnifications_csv  - Path to magnifications.csv")
        print("\nOptional:")
        print("  -redshift Z         - Source redshift (e.g., 1.524) for filtering FITS files")
        print("  -output DIR         - Output directory (default: statistics/magnification)")
        print("  -sigma SIGMA        - Confidence interval in sigma (default: 1.0 = 68%)")
        print("  -bins BINS          - Histogram bins (default: 20)")
        print("  -num_maps N         - Number of magnification maps to generate (default: all)")
        print("  -ampli DIR          - Directory with amplification FITS files (for maps and best values)")
        print("  -config FILE        - magnification_config.json (for object coordinates)")
        print("  -clip SIGMA         - Sigma threshold for outlier rejection (e.g., 3.0 for 3σ clipping)")
        print("\nExamples:")
        print("  magnification-statistics magnifications.csv")
        print("  magnification-statistics magnifications.csv -redshift 1.524")
        print("  magnification-statistics magnifications.csv -redshift 1.524 -sigma 2.0")
        print("  magnification-statistics magnifications.csv -redshift 1.524 -clip 3.0")
        print("  magnification-statistics magnifications.csv -redshift 1.524 -ampli output/ampli -config ../tests/magnification_config.json")
        sys.exit(1)
    
    magnifications_csv = sys.argv[1]
    output_dir = 'statistics/magnification'
    sigma = 1.0
    bins = 20
    redshift = None
    ampli_directory = None
    config_file = None
    clip_sigma = None
    num_maps = None
    
    # Parse optional arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '-redshift' and i + 1 < len(sys.argv):
            redshift = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '-output' and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '-sigma' and i + 1 < len(sys.argv):
            try:
                sigma = float(sys.argv[i + 1])
            except ValueError:
                print(f"Error: -sigma must be a number, got {sys.argv[i + 1]}")
                sys.exit(1)
            i += 2
        elif sys.argv[i] == '-bins' and i + 1 < len(sys.argv):
            try:
                bins = int(sys.argv[i + 1])
            except ValueError:
                print(f"Error: -bins must be an integer, got {sys.argv[i + 1]}")
                sys.exit(1)
            i += 2
        elif sys.argv[i] == '-clip' and i + 1 < len(sys.argv):
            try:
                clip_sigma = float(sys.argv[i + 1])
            except ValueError:
                print(f"Error: -clip must be a number, got {sys.argv[i + 1]}")
                sys.exit(1)
            i += 2
        elif sys.argv[i] == '-ampli' and i + 1 < len(sys.argv):
            ampli_directory = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '-config' and i + 1 < len(sys.argv):
            config_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '-num_maps' and i + 1 < len(sys.argv):
            try:
                num_maps = int(sys.argv[i + 1])
            except ValueError:
                print(f"Error: -num_maps must be an integer, got {sys.argv[i + 1]}")
                sys.exit(1)
            i += 2
        else:
            print(f"Unknown option: {sys.argv[i]}")
            sys.exit(1)
    
    stats_df, output_path = generate_statistics_and_histograms(
        magnifications_csv, output_dir, sigma, bins, redshift, ampli_directory, config_file, clip_sigma, num_maps
    )
    
    # Print summary
    print("=" * 90)
    print("MAGNIFICATION STATISTICS SUMMARY")
    print("=" * 90)
    print(stats_df.to_string(index=False))
    
    if redshift:
        stats_csv = output_path / f'magnification_statistics_z{redshift}.csv'
        report_file = output_path / f'magnification_report_z{redshift}.txt'
    else:
        stats_csv = output_path / 'magnification_statistics.csv'
        report_file = output_path / 'magnification_report.txt'
    
    # Print report contents
    if report_file.exists():
        print(f"\n{Path(report_file).read_text()}")
    
    print(f"\n✓ Histograms saved to: {output_path.resolve()}")
    if stats_csv.exists():
        print(f"✓ Statistics CSV saved to: {stats_csv}")
    if report_file.exists():
        print(f"✓ Report saved to: {report_file}")
    
    maps_dir = output_path / 'magnification_maps'
    if maps_dir.exists():
        num_maps = len(list(maps_dir.glob('*.pdf')))
        if num_maps > 0:
            print(f"✓ Magnification maps saved to: {maps_dir.resolve()} ({num_maps} PDFs)\n")
    else:
        print()
    
    sys.exit(0)


if __name__ == "__main__":
    main()
