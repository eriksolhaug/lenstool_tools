#!/usr/bin/env python
"""
Plot magnification maps for sample lens models.

Generates individual magnification maps for each sample FITS file with object
coordinate annotations. Each sample produces a single-panel PDF plot.

Colormap Scaling Methods
------------------------
The 'scaling' section in the config file controls how data is mapped to colors:

1. **percentile** (default): Uses percentile limits
   {
     "method": "percentile",
     "vmin_pct": 1.5,
     "vmax_pct": 98.5
   }

2. **zscale**: Uses astropy's ZScale algorithm for automated stretch
   {
     "method": "zscale"
   }

3. **manual**: Explicitly set min and max values
   {
     "method": "manual",
     "vmin": 0.0,
     "vmax": 10.0
   }

4. **auto**: Uses full data range (min to max)
   {
     "method": "auto"
   }

Usage:
    python -m lenstool_tools.plot_sample_magnifications \
        magnifications_csv \
        output_directory \
        -redshift Z \
        -config magnification_config.json \
        -ampli FITS_DIRECTORY

Example:
    python -m lenstool_tools.plot_sample_magnifications \
        magnifications.csv \
        output/ampli/plots \
        -redshift 1.524 \
        -config tests/plot_magnifications_config.json \
        -ampli output/ampli
"""

import argparse
import json
import os
import sys
from pathlib import Path
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import ticker as mticker
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_config(config_path):
    """Load configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)


def setup_latex(use_latex=True, latex_path=None):
    """Configure LaTeX rendering for plots."""
    if use_latex and latex_path:
        os.environ["PATH"] += os.pathsep + latex_path
    
    from matplotlib import rc
    rc('font', **{'family': 'serif', 'serif': ['Computer Modern Roman']})
    rc('text', usetex=use_latex)
    
    # Vector fonts in PDF
    matplotlib.rcParams['pdf.fonttype'] = 42
    matplotlib.rcParams['ps.fonttype'] = 42


def set_plot_styles(font_size=20):
    """Set global plot styles."""
    plt.rcParams.update({
        'font.size': font_size,
        'axes.labelsize': font_size,
        'axes.titlesize': font_size,
        'legend.fontsize': font_size,
        'xtick.labelsize': font_size,
        'ytick.labelsize': font_size,
        'xtick.major.size': 10,
        'ytick.major.size': 10,
        'xtick.minor.size': 7,
        'ytick.minor.size': 7,
        'axes.labelweight': 'bold',
        'axes.titleweight': 'bold',
        'legend.title_fontsize': font_size,
        'text.usetex': True,
        'font.family': 'serif',
    })


def robust_limits(data, scaling_config=None):
    """
    Compute data limits based on scaling configuration.
    
    Args:
        data (array): Data to compute limits for
        scaling_config (dict): Scaling configuration with 'method' and parameters:
            - 'percentile': Uses vmin_pct and vmax_pct percentiles
            - 'zscale': Uses astropy's zscale algorithm
            - 'manual': Uses explicit vmin and vmax values
            - 'auto': Uses full data range (min to max)
    
    Returns:
        tuple: (vmin, vmax) for colormap scaling
    """
    if scaling_config is None:
        # Default: percentile scaling
        scaling_config = {'method': 'percentile', 'vmin_pct': 1.5, 'vmax_pct': 98.5}
    
    method = scaling_config.get('method', 'percentile')
    
    if method == 'percentile':
        vmin_pct = scaling_config.get('vmin_pct', 1.5)
        vmax_pct = scaling_config.get('vmax_pct', 98.5)
        vmin = np.nanpercentile(data, vmin_pct)
        vmax = np.nanpercentile(data, vmax_pct)
    
    elif method == 'zscale':
        from astropy.visualization import ZScaleInterval
        interval = ZScaleInterval()
        vmin, vmax = interval.get_limits(data[~np.isnan(data)])
    
    elif method == 'manual':
        vmin = scaling_config.get('vmin', np.nanmin(data))
        vmax = scaling_config.get('vmax', np.nanmax(data))
    
    elif method == 'auto':
        vmin = np.nanmin(data)
        vmax = np.nanmax(data)
    
    else:
        raise ValueError(f"Unknown scaling method: {method}")
    
    return vmin, vmax


def parse_coordinate_string(coord_string):
    """Parse coordinate string (HHhMMmSSs ±DDdMMmSSs) to SkyCoord."""
    # Replace h, m, s and d with spaces for easier parsing
    coord_string = coord_string.replace('h', ' ').replace('m', ' ').replace('s', ' ')
    coord_string = coord_string.replace('d', ' ')
    parts = [p.strip() for p in coord_string.split() if p.strip()]
    
    # We expect 6 parts: RA_h RA_m RA_s Dec_d Dec_m Dec_s
    if len(parts) < 6:
        raise ValueError(f"Cannot parse coordinates: {coord_string}")
    
    # Handle RA (hours minutes seconds)
    ra_h = float(parts[0])
    ra_m = float(parts[1])
    ra_s = float(parts[2])
    ra_deg = (ra_h + ra_m/60 + ra_s/3600) * 15  # Convert hours to degrees
    
    # Handle Dec (degrees arcmin arcsec) - parts[3] may have sign
    dec_str = parts[3]
    dec_d = float(dec_str)
    dec_m = float(parts[4])
    dec_s = float(parts[5])
    sign = 1 if dec_d >= 0 else -1
    dec_deg = dec_d + sign * (dec_m / 60 + dec_s / 3600)
    
    return SkyCoord(ra_deg * u.deg, dec_deg * u.deg, frame='icrs')


def plot_magnification_map(fits_file, output_pdf, config, redshift=None, is_absolute=False):
    """
    Plot a single magnification map with object coordinate annotations.
    
    Args:
        fits_file (str): Path to magnification FITS file
        output_pdf (str): Output PDF filename
        config (dict): Configuration dictionary
        redshift (str, optional): Source redshift for annotations
        is_absolute (bool): Whether this is an absolute value magnification map
    """
    # Load display settings
    cmap = config.get('display', {}).get('colormap', 'Blues')
    scaling_config = config.get('display', {}).get('scaling', {
        'method': 'percentile',
        'vmin_pct': 1.5,
        'vmax_pct': 98.5
    })
    
    # Setup plotting
    use_latex = config.get('plotting', {}).get('use_latex', False)
    latex_path = config.get('plotting', {}).get('latex_path', None)
    font_size = config.get('plotting', {}).get('font_size', 20)
    
    setup_latex(use_latex, latex_path)
    set_plot_styles(font_size)
    
    # Load magnification map
    with fits.open(fits_file) as hdu:
        hdr = hdu[0].header
        data = hdu[0].data.astype(np.float64)
    wcs = WCS(hdr).celestial
    
    # Get object coordinates from config
    objects = config.get('objects', [])
    
    # Create figure with WCS
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection=wcs)
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlabel("RA (J2000)")
    ax.set_ylabel("Dec (J2000)")
    
    # Display magnification map with flexible scaling
    vmin, vmax = robust_limits(data, scaling_config)
    im = ax.imshow(data, origin='lower', cmap=cmap, vmin=vmin, vmax=vmax)
    
    # Colorbar
    cb = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.02,
                      extend='both', extendrect=False, extendfrac=0.06)
    cb.set_label(r"$|\mu|$" if is_absolute else r"$\mu$")
    cb.ax.yaxis.set_minor_locator(mticker.AutoMinorLocator(5))
    cb.ax.tick_params(which='major', length=7, width=1)
    cb.ax.tick_params(which='minor', length=4, width=0.8)
    
    # Configure axes
    lon = ax.coords[0]
    lat = ax.coords[1]
    lon.set_ticks_position('bt')
    lat.set_ticks_position('lr')
    lon.set_ticklabel_position('b')
    lat.set_ticklabel_position('l')
    lon.tick_params(which='both', direction='in', labelsize=font_size)
    lat.tick_params(which='both', direction='in', labelsize=font_size)
    lon.display_minor_ticks(True)
    lat.display_minor_ticks(True)
    
    # Plot object coordinates with magnification values
    for obj in objects:
        # Parse or extract coordinates
        if 'coord_string' in obj:
            coord = parse_coordinate_string(obj['coord_string'])
        else:
            coord = SkyCoord(obj['ra'] * u.deg, obj['dec'] * u.deg, frame='icrs')
        
        # Plot marker
        marker = obj.get('marker', 'x')
        color = obj.get('color', 'black')
        ax.plot(coord.ra.deg, coord.dec.deg, marker=marker, mew=2.0, ms=16,
               color=color, transform=ax.get_transform('world'))
        
        # Sample value at nearest pixel (magnification at this location)
        x, y = wcs.all_world2pix(coord.ra.deg, coord.dec.deg, 0)
        xi, yi = int(np.rint(x)), int(np.rint(y))
        ny, nx = data.shape
        val = np.nan
        if 0 <= xi < nx and 0 <= yi < ny:
            val = float(data[yi, xi])
            val = abs(val)  # Use absolute value
        
        val_str = f"{val:.0f}" if np.isfinite(val) else "--"
        
        # Annotate with ID and magnification value
        obj_id = obj.get('id', '')
        offset_pts = obj.get('annotation_offset', (10, 0))
        ax.annotate(f"{obj_id}\n({val_str})",
                   xy=(coord.ra.deg, coord.dec.deg),
                   xycoords=ax.get_transform('world'),
                   textcoords='offset points', xytext=tuple(offset_pts),
                   ha='left', va='center', color=color)
    
    # Add redshift annotation if provided
    if redshift:
        ax.text(0.98, 0.98, f"$z_{{\\rm source}}={redshift}$", 
               transform=ax.transAxes,
               ha='right', va='top', fontsize=font_size, color='k')
    
    plt.tight_layout()
    plt.savefig(output_pdf, dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_pdf


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description='Plot magnification maps for sample lens models'
    )
    parser.add_argument('magnifications_csv', help='Path to magnifications.csv')
    parser.add_argument('output_dir', help='Output directory for PDF plots')
    parser.add_argument('-redshift', required=True, help='Source redshift (e.g., 1.524)')
    parser.add_argument('-config', required=True, help='magnification_config.json file')
    parser.add_argument('-ampli', required=True, help='Directory with amplification FITS files')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Create output directory
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load magnifications CSV to get sample list
    df = pd.read_csv(args.magnifications_csv)
    
    print(f"\nPlotting magnification maps for {len(df)} samples...")
    print(f"Output directory: {output_path.resolve()}")
    print(f"Redshift: z = {args.redshift}")
    print(f"Colormap: {config.get('display', {}).get('colormap', 'Blues')}")
    
    # Process each sample - generate both regular and absolute value plots
    fits_dir = Path(args.ampli)
    
    # Regular magnification plots
    print(f"\nGenerating regular magnification plots...")
    ampli_files = sorted(fits_dir.glob(f'*_z{args.redshift}_ampli.fits'))
    if not ampli_files:
        print(f"Error: No FITS files found matching pattern *_z{args.redshift}_ampli.fits")
        sys.exit(1)
    
    print(f"Found {len(ampli_files)} amplification FITS files\n")
    
    for i, fits_file in enumerate(ampli_files, 1):
        base_name = fits_file.stem
        sample_name = base_name.replace(f'_z{args.redshift}_ampli', '')
        pdf_name = f'{sample_name}_z{args.redshift}_ampli.pdf'
        pdf_path = output_path / pdf_name
        
        try:
            plot_magnification_map(str(fits_file), str(pdf_path), config, args.redshift, is_absolute=False)
            status = "✓"
        except Exception as e:
            status = f"✗ ({str(e)[:30]})"
        
        if i % 10 == 0 or i == len(ampli_files):
            print(f"  Completed {i} / {len(ampli_files)} regular plots {status}")
    
    # Absolute value magnification plots
    print(f"\nGenerating absolute value magnification plots...")
    absampli_files = sorted(fits_dir.glob(f'*_z{args.redshift}_absampli.fits'))
    
    if absampli_files:
        for i, fits_file in enumerate(absampli_files, 1):
            base_name = fits_file.stem
            sample_name = base_name.replace(f'_z{args.redshift}_absampli', '')
            pdf_name = f'{sample_name}_z{args.redshift}_absampli.pdf'
            pdf_path = output_path / pdf_name
            
            try:
                plot_magnification_map(str(fits_file), str(pdf_path), config, args.redshift, is_absolute=True)
                status = "✓"
            except Exception as e:
                status = f"✗ ({str(e)[:30]})"
            
            if i % 10 == 0 or i == len(absampli_files):
                print(f"  Completed {i} / {len(absampli_files)} absolute value plots {status}")
    else:
        print(f"  No absolute value FITS files found. Run extract_magnifications first.")
    
    total_plots = len(ampli_files) + len(absampli_files)
    print(f"\n✓ All magnification maps saved to: {output_path.resolve()}")
    print(f"  Total PDF plots generated: {total_plots}\n")
    sys.exit(0)


if __name__ == '__main__':
    main()
