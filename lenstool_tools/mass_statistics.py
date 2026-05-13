#!/usr/bin/env python3
"""
Extract enclosed masses from mass FITS maps at a specified aperture radius.
Generate mass statistics and confidence intervals from sample models.
Creates histograms and summary statistics for the total lens mass.
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
    from astropy.cosmology import FlatLambdaCDM
    import astropy.units as u
except ImportError:
    raise ImportError("This module requires astropy. Install with: pip install astropy")


def get_cosmo():
    """Return cosmology instance."""
    return FlatLambdaCDM(H0=70 * u.km/u.s/u.Mpc, Om0=0.3)


def size_per_arcsec(z: float, cosmo=None) -> float:
    """Convert arcsec to kpc at redshift z.
    
    Args:
        z (float): Redshift
        cosmo: Cosmology object (optional)
        
    Returns:
        float: kpc per arcsec
    """
    if cosmo is None:
        cosmo = get_cosmo()
    return (cosmo.kpc_proper_per_arcmin(z)).to(u.kpc/u.arcsec).value


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


def extract_enclosed_mass(
    mass_fits_file: Path,
    z_lens: float,
    aperture_kpc: float,
    D_A_kpc: Optional[float] = None
) -> Optional[float]:
    """
    Extract enclosed mass within aperture from mass FITS file.
    
    Args:
        mass_fits_file (Path): Path to mass FITS file (in units of 1e12 Msun/pixel)
        z_lens (float): Lens redshift for cosmological calculations
        aperture_kpc (float): Aperture radius in kpc
        D_A_kpc (float, optional): Angular diameter distance in kpc. If None, will be calculated from cosmology.
        
    Returns:
        float: Enclosed mass in solar masses, or np.nan if extraction fails
    """
    try:
        # Load mass FITS file
        with fits.open(mass_fits_file) as hdul:
            hdr = hdul[0].header
            data = hdul[0].data.astype(np.float64)  # units: 1e12 Msun/pixel
        
        wcs = WCS(hdr).celestial
        ny, nx = data.shape
        
        # Calculate pixel area in steradians (same as mass_plot.py)
        if wcs.wcs.has_cd():
            CD_deg = wcs.wcs.cd[:2, :2]  # deg/pix
        else:
            PC = wcs.wcs.get_pc()[:2, :2]
            CDELT = np.array(wcs.wcs.cdelt[:2])  # deg/pix
            CD_deg = PC @ np.diag(CDELT)
        
        CD_rad = np.deg2rad(CD_deg)
        omega_pix_sr = float(abs(np.linalg.det(CD_rad)))
        
        # Get angular diameter distance
        if D_A_kpc is None:
            cosmo = get_cosmo()
            D_A_kpc = cosmo.angular_diameter_distance(z_lens).to(u.kpc).value
        
        # Convert to surface density (Msun/kpc^2)
        A_pix_kpc2 = (D_A_kpc**2) * omega_pix_sr
        
        Sigma_kpc2 = (data * 1.0e12) / A_pix_kpc2
        Sigma_kpc2 = np.where(np.isfinite(Sigma_kpc2), Sigma_kpc2, 0.0)
        
        # Convert aperture radius from kpc to radians
        theta_ap_rad = (aperture_kpc * u.kpc / (size_per_arcsec(z_lens, cosmo) * u.kpc/u.arcsec)).to(u.rad).value
        
        # Get transformation matrix
        M = CD_rad
        M_inv = np.linalg.inv(M)
        
        # Center pixel (assuming center of the image)
        xc, yc = nx / 2.0, ny / 2.0
        
        # Create mask for pixels within aperture
        Y, X = np.mgrid[0:ny, 0:nx]
        dX = X - xc
        dY = Y - yc
        dE_pix = M[0, 0] * dX + M[0, 1] * dY
        dN_pix = M[1, 0] * dX + M[1, 1] * dY
        r_rad = np.hypot(dE_pix, dN_pix)
        mask = (r_rad <= theta_ap_rad)
        
        # Integrate mass within aperture
        pix_area_kpc2 = (D_A_kpc**2) * abs(np.linalg.det(M))
        M_enc_Msun = np.sum(Sigma_kpc2[mask]) * pix_area_kpc2
        
        return M_enc_Msun
    
    except Exception as e:
        print(f"    Error extracting mass from {mass_fits_file.name}: {e}")
        return np.nan


def extract_best_enclosed_mass(
    mass_directory: str,
    z_lens: float,
    aperture_kpc: float,
    redshift: Optional[str] = None,
    D_A_kpc: Optional[float] = None
) -> Optional[float]:
    """
    Extract enclosed mass from the best-fit mass FITS file.
    
    Args:
        mass_directory (str): Path to directory containing mass FITS files
        z_lens (float): Lens redshift
        aperture_kpc (float): Aperture radius in kpc
        redshift (str, optional): Redshift suffix to match (e.g., "0.4301")
        D_A_kpc (float, optional): Angular diameter distance in kpc. If None, will be calculated from cosmology.
        
    Returns:
        float: Enclosed mass in solar masses, or np.nan if file not found
    """
    mass_dir = Path(mass_directory)
    
    # Find sample_best FITS file with matching redshift
    if redshift:
        pattern = f'sample_best_z{redshift}_mass.fits'
    else:
        pattern = 'sample_best_mass.fits'
    
    best_fits_files = list(mass_dir.glob(pattern))
    
    if not best_fits_files:
        print(f"  Warning: No best-fit mass file found matching pattern: {pattern}")
        return np.nan
    
    if len(best_fits_files) > 1:
        print(f"  Warning: Multiple best-fit files found, using first: {best_fits_files[0].name}")
    
    best_fits_file = best_fits_files[0]
    
    print(f"  Extracted best-fit mass from: {best_fits_file.name}")
    return extract_enclosed_mass(best_fits_file, z_lens, aperture_kpc, D_A_kpc=D_A_kpc)


def process_all_mass_files(
    mass_directory: str,
    z_lens: float,
    aperture_kpc: float,
    redshift: Optional[str] = None,
    D_A_kpc: Optional[float] = None
) -> pd.DataFrame:
    """
    Process all mass FITS files in a directory and extract enclosed masses.
    
    Args:
        mass_directory (str): Path to directory containing mass FITS files
        z_lens (float): Lens redshift
        aperture_kpc (float): Aperture radius in kpc
        redshift (str, optional): Redshift suffix to match (e.g., "0.4301")
        D_A_kpc (float, optional): Angular diameter distance in kpc. If None, will be calculated from cosmology.
        
    Returns:
        pd.DataFrame: DataFrame with columns ['sample', 'mass_Msun']
    """
    mass_dir = Path(mass_directory)
    
    # Find all FITS files matching redshift pattern
    if redshift:
        pattern = f'*_z{redshift}_mass.fits'
    else:
        pattern = '*_mass.fits'
    
    fits_files = sorted(mass_dir.glob(pattern))
    
    if not fits_files:
        print(f"No mass FITS files found matching pattern: {pattern}")
        return pd.DataFrame()
    
    print(f"Processing {len(fits_files)} mass FITS files...")
    print(f"Aperture radius: {aperture_kpc:.1f} kpc")
    print(f"Lens redshift: z = {z_lens}\n")
    
    # Initialize results
    data_rows = []
    
    for idx, fits_file in enumerate(fits_files, start=1):
        try:
            sample_name = fits_file.stem.rsplit('_', 2)[0]  # Remove _z* and _mass
            mass = extract_enclosed_mass(fits_file, z_lens, aperture_kpc, D_A_kpc=D_A_kpc)
            data_rows.append({'sample': sample_name, 'mass_Msun': mass})
            
            if idx % max(1, len(fits_files) // 10) == 0 or idx == len(fits_files):
                print(f"  Processed {idx} / {len(fits_files)} files")
        
        except Exception as e:
            print(f"  ERROR processing {fits_file.name}: {e}")
            sample_name = fits_file.stem.rsplit('_', 2)[0]
            data_rows.append({'sample': sample_name, 'mass_Msun': np.nan})
    
    return pd.DataFrame(data_rows)


def compute_mass_statistics(
    masses: np.ndarray,
    sigma: float = 1.0,
    best_mass: Optional[float] = None
) -> Dict:
    """
    Compute statistics (median, mean, confidence intervals) for masses.
    
    Args:
        masses (np.ndarray): Array of mass values (excluding NaN)
        sigma (float): Number of standard deviations for confidence interval
        best_mass (float, optional): Best-fit mass value
        
    Returns:
        dict: Statistics with keys: best, median, mean, error_lower, error_upper
    """
    # Remove NaN values
    valid_masses = masses[~np.isnan(masses)]
    
    if len(valid_masses) == 0:
        return {
            'best': np.nan,
            'median': np.nan,
            'mean': np.nan,
            'error_lower': np.nan,
            'error_upper': np.nan
        }
    
    median, error_lower, error_upper = calculate_confidence_interval(valid_masses, sigma=sigma)
    mean = np.nanmean(valid_masses)
    
    return {
        'best': best_mass if best_mass is not None and not np.isnan(best_mass) else np.nan,
        'median': median,
        'mean': mean,
        'error_lower': error_lower,
        'error_upper': error_upper
    }


def create_histogram(
    masses: np.ndarray,
    output_path: Path,
    sigma: float = 1.0,
    bins: int = 20,
    best_value: Optional[float] = None,
    aperture_kpc: float = 100.0
) -> None:
    """
    Create and save a histogram for enclosed mass distribution.
    
    Args:
        masses (np.ndarray): Array of mass values
        output_path (Path): Path to save histogram
        sigma (float): Number of standard deviations for confidence interval
        bins (int): Number of histogram bins
        best_value (float, optional): Best-fit mass value to plot
        aperture_kpc (float): Aperture radius for title
    """
    # Remove NaN values
    valid_masses = masses[~np.isnan(masses)]
    
    if len(valid_masses) == 0:
        print(f"  Skipping histogram: no valid data")
        return
    
    # Calculate statistics
    median, error_lower, error_upper = calculate_confidence_interval(valid_masses, sigma=sigma)
    mean = np.nanmean(valid_masses)
    std = np.nanstd(valid_masses)
    
    lower_ci = median - error_lower
    upper_ci = median + error_upper
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot histogram
    counts, edges, patches = ax.hist(valid_masses, bins=bins, alpha=0.7, color='steelblue', edgecolor='black')
    
    # Add vertical lines for statistics
    ax.axvline(median, color='red', linestyle='--', linewidth=2, label=f'Median: {median:.3e} $M_\\odot$')
    ax.axvline(mean, color='green', linestyle='--', linewidth=2, label=f'Mean: {mean:.3e} $M_\\odot$')
    
    # Plot best value as a vertical line with marker
    if best_value is not None and not np.isnan(best_value):
        ax.axvline(best_value, color='purple', linestyle=':', linewidth=2.5, 
                   label=f'Best-fit: {best_value:.3e} $M_\\odot$')
    
    # Shade confidence interval
    ax.axvspan(lower_ci, upper_ci, alpha=0.2, color='yellow', 
               label=f'{sigma:.1f}σ CI: [{lower_ci:.3e}, {upper_ci:.3e}] $M_\\odot$')
    
    # Labels and title
    ax.set_xlabel('Enclosed Mass ($M_\\odot$)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title(f'Enclosed Mass Distribution ($R < {aperture_kpc:.0f}$ kpc)\n(N={len(valid_masses)}, σ={std:.3e} $M_\\odot$)', 
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=10, loc='upper right')
    ax.grid(True, alpha=0.3)
    
    # Use scientific notation
    ax.ticklabel_format(style='scientific', axis='x', scilimits=(0, 0))
    
    # Save figure
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  Saved: {output_path.name}")


def create_report_file(
    stats: Dict,
    output_path: Path,
    sigma: float = 1.0,
    aperture_kpc: float = 100.0,
    z_lens: float = 0.4301,
    redshift: Optional[str] = None
) -> Path:
    """
    Create a human-readable report file with mass statistics.
    
    Args:
        stats (Dict): Statistics dictionary
        output_path (Path): Directory to save report
        sigma (float): Sigma level used for confidence intervals
        aperture_kpc (float): Aperture radius in kpc
        z_lens (float): Lens redshift
        redshift (str, optional): Redshift of the data
        
    Returns:
        Path: Path to the created report file
    """
    # Determine report filename
    if redshift:
        report_file = output_path / f'mass_report_z{redshift}.txt'
    else:
        report_file = output_path / 'mass_report.txt'
    
    with open(report_file, 'w') as f:
        f.write("=" * 90 + "\n")
        f.write("ENCLOSED MASS STATISTICS REPORT\n")
        f.write("=" * 90 + "\n")
        f.write(f"Aperture radius: {aperture_kpc:.1f} kpc\n")
        f.write(f"Lens redshift: z = {z_lens}\n")
        f.write(f"Confidence Level: {sigma:.1f}σ ({100*(1-np.exp(-sigma**2/2)):.1f}% confidence)\n")
        f.write("\n")
        
        f.write("SUMMARY STATISTICS\n")
        f.write("-" * 90 + "\n")
        
        best = stats['best']
        median = stats['median']
        mean = stats['mean']
        error_lower = stats['error_lower']
        error_upper = stats['error_upper']
        
        best_str = f"{best:.6e}" if not np.isnan(best) else "N/A"
        f.write(f"Best-fit enclosed mass:    {best_str} M_sun\n")
        f.write(f"Median enclosed mass:      {median:.6e} M_sun\n")
        f.write(f"Mean enclosed mass:        {mean:.6e} M_sun\n")
        f.write("\n")
        f.write(f"{sigma:.1f}σ Confidence Interval:\n")
        f.write(f"  Lower error (below median):  -{error_lower:.6e} M_sun\n")
        f.write(f"  Upper error (above median):  +{error_upper:.6e} M_sun\n")
        f.write(f"  Range: [{median - error_lower:.6e}, {median + error_upper:.6e}] M_sun\n")
        f.write("\n")
        
        f.write("-" * 90 + "\n")
        f.write("INTERPRETATION\n")
        f.write("-" * 90 + "\n")
        f.write(f"The enclosed mass within {aperture_kpc:.0f} kpc is:\n")
        f.write(f"  M = {median:.3e} (+{error_upper:.3e}) (-{error_lower:.3e}) M_sun\n")
        f.write("\n")
        f.write(f"This represents the total mass of the lens system within a projected radius\n")
        f.write(f"of {aperture_kpc:.1f} kpc from the lens center at redshift z = {z_lens}.\n")
        f.write("\n")
        
        f.write("=" * 90 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 90 + "\n")
    
    return report_file


def generate_mass_statistics(
    mass_directory: str,
    config_file: str,
    output_dir: str = 'statistics/mass',
    sigma: float = 1.0,
    bins: int = 20,
    redshift: Optional[str] = None
) -> Tuple[pd.DataFrame, Dict, Path]:
    """
    Generate mass statistics, histograms, and reports.
    
    Args:
        mass_directory (str): Path to directory containing mass FITS files
        config_file (str): Path to mass_config.json with aperture settings
        output_dir (str): Output directory for results
        sigma (float): Number of standard deviations for confidence interval
        bins (int): Number of histogram bins
        redshift (str, optional): Redshift suffix to match for file filtering
        
    Returns:
        tuple: (masses_dataframe, statistics_dict, output_directory_path)
    """
    # Load configuration
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    z_lens = config['cosmology']['z_lens']
    aperture_kpc = config['aperture']['aperture_kpc']
    
    # Get angular diameter distance from config if provided, otherwise None (will use astropy)
    D_A_kpc = config['cosmology'].get('angular_diameter_distance_kpc', None)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\nExtracting enclosed masses from mass FITS files...")
    print(f"Sigma level: {sigma:.1f} (confidence interval)")
    if redshift:
        print(f"Redshift: z = {redshift}")
    if D_A_kpc is not None:
        print(f"Angular diameter distance (from config): {D_A_kpc:.1f} kpc")
    print(f"Output directory: {output_path.resolve()}\n")
    
    # Process all mass files
    masses_df = process_all_mass_files(mass_directory, z_lens, aperture_kpc, 
                                        redshift=redshift, D_A_kpc=D_A_kpc)
    
    if masses_df.empty:
        print("No mass files processed. Exiting.")
        return masses_df, {}, output_path
    
    masses = masses_df['mass_Msun'].values
    
    # Extract best mass if available
    print("\nExtracting best-fit enclosed mass...")
    best_mass = extract_best_enclosed_mass(mass_directory, z_lens, aperture_kpc, 
                                           redshift=redshift, D_A_kpc=D_A_kpc)
    
    # Compute statistics
    print("Computing statistics...")
    stats = compute_mass_statistics(masses, sigma=sigma, best_mass=best_mass)
    
    # Create histogram
    print("\nCreating histogram:")
    histogram_file = output_path / f'mass_distribution.png'
    create_histogram(masses, histogram_file, sigma=sigma, bins=bins, 
                    best_value=best_mass, aperture_kpc=aperture_kpc)
    
    # Create report file
    report_file = create_report_file(stats, output_path, sigma=sigma, 
                                     aperture_kpc=aperture_kpc, z_lens=z_lens,
                                     redshift=redshift)
    print(f"Saved report: {report_file.name}")
    
    # Save statistics to CSV
    if redshift:
        stats_csv = output_path / f'mass_statistics_z{redshift}.csv'
    else:
        stats_csv = output_path / 'mass_statistics.csv'
    
    # Create CSV with statistics
    csv_data = {
        'statistic': ['best', 'median', 'mean', f'error_lower_{sigma}sigma', f'error_upper_{sigma}sigma'],
        'value': [stats['best'], stats['median'], stats['mean'], stats['error_lower'], stats['error_upper']]
    }
    stats_csv_df = pd.DataFrame(csv_data)
    stats_csv_df.to_csv(stats_csv, index=False)
    print(f"Saved statistics CSV: {stats_csv.name}\n")
    
    return masses_df, stats, output_path


def main():
    """Command-line interface for mass statistics."""
    if len(sys.argv) < 3:
        print("Usage: mass-statistics <mass_directory> <config_file> [OPTIONS]")
        print("\nRequired:")
        print("  mass_directory      - Path to directory with mass FITS files")
        print("  config_file         - Path to mass_config.json with aperture settings")
        print("\nOptional:")
        print("  -redshift Z         - Lens redshift (e.g., 0.4301) for filtering FITS files")
        print("  -output DIR         - Output directory (default: statistics/mass)")
        print("  -sigma SIGMA        - Confidence interval in sigma (default: 1.0 = 68%)")
        print("  -bins BINS          - Histogram bins (default: 20)")
        print("\nConfiguration file (mass_config.json):")
        print("  - cosmology.z_lens: Lens redshift")
        print("  - cosmology.kpc_per_arcsec: Conversion factor (optional)")
        print("  - cosmology.angular_diameter_distance_kpc: D_A in kpc (optional, null to use astropy)")
        print("  - aperture.aperture_kpc: Aperture radius for mass integration")
        print("\nExamples:")
        print("  mass-statistics output/mass tests/mass_config.json")
        print("  mass-statistics output/mass tests/mass_config.json -redshift 0.4301")
        print("  mass-statistics output/mass tests/mass_config.json -redshift 0.4301 -sigma 2.0")
        sys.exit(1)
    
    mass_directory = sys.argv[1]
    config_file = sys.argv[2]
    output_dir = 'statistics/mass'
    sigma = 1.0
    bins = 20
    redshift = None
    
    # Parse optional arguments
    i = 3
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
        else:
            print(f"Unknown option: {sys.argv[i]}")
            sys.exit(1)
    
    masses_df, stats, output_path = generate_mass_statistics(
        mass_directory, config_file, output_dir, sigma, bins, redshift
    )
    
    # Print summary
    print("=" * 90)
    print("ENCLOSED MASS STATISTICS SUMMARY")
    print("=" * 90)
    print(f"\nBest-fit mass:    {stats['best']:.6e} M_sun" if not np.isnan(stats['best']) else "\nBest-fit mass:    N/A")
    print(f"Median mass:      {stats['median']:.6e} M_sun")
    print(f"Mean mass:        {stats['mean']:.6e} M_sun")
    print(f"\n{sigma:.1f}σ Confidence Interval:")
    print(f"  Lower error:    -{stats['error_lower']:.6e} M_sun")
    print(f"  Upper error:    +{stats['error_upper']:.6e} M_sun")
    print(f"  Range:          [{stats['median'] - stats['error_lower']:.6e}, {stats['median'] + stats['error_upper']:.6e}] M_sun")
    
    if redshift:
        stats_csv = output_path / f'mass_statistics_z{redshift}.csv'
        report_file = output_path / f'mass_report_z{redshift}.txt'
    else:
        stats_csv = output_path / 'mass_statistics.csv'
        report_file = output_path / 'mass_report.txt'
    
    print(f"\n✓ Histogram saved to: {output_path / 'mass_distribution.png'}")
    print(f"✓ Statistics CSV saved to: {stats_csv}")
    print(f"✓ Report saved to: {report_file}\n")
    
    sys.exit(0)


if __name__ == "__main__":
    main()
