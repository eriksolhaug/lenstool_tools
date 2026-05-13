#!/usr/bin/env python
"""
Plot time delay contour maps for each sample lens model.

Generates publication-quality time delay contour maps for all sample models,
similar to single_model/timedelay/timedelay_plot.py but for sample distributions.
"""

import os
import sys
import json
import argparse
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import ticker as mticker
from matplotlib.lines import Line2D
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


def setup_latex(use_latex=True, latex_path=None):
    """Configure LaTeX rendering for plots."""
    if use_latex and latex_path:
        os.environ["PATH"] += os.pathsep + latex_path
    
    from matplotlib import rc
    rc('font', **{'family': 'serif', 'serif': ['Computer Modern Roman']})
    rc('text', usetex=use_latex)
    
    matplotlib.rcParams['pdf.fonttype'] = 42
    matplotlib.rcParams['ps.fonttype'] = 42


def set_plot_styles(font_size=20):
    """Set global plot styles."""
    plt.rcParams.update({
        'font.size': font_size,
        'axes.labelsize': font_size,
        'axes.titlesize': font_size,
        'legend.fontsize': font_size - 2,
        'xtick.labelsize': font_size - 2,
        'ytick.labelsize': font_size - 2,
        'xtick.major.size': 8,
        'ytick.major.size': 8,
        'xtick.minor.size': 5,
        'ytick.minor.size': 5,
        'axes.labelweight': 'bold',
        'axes.titleweight': 'bold',
        'text.usetex': True,
        'font.family': 'serif',
    })


def draw_alternating_contours(ax, Z, levels, color, lw_base=1.0, lw_step=0.001, lw_invert=True):
    """Draw contours with alternating line styles (solid/dashed/dotted) and variable line width."""
    linestyles = ['solid', 'dashed', 'dotted', 'dashdot', 'solid', 'dashed', 'dotted']
    
    cs_sets = []
    Lmax = float(np.max(levels))
    
    for i, lev in enumerate(levels):
        ls = linestyles[i % len(linestyles)]
        if lw_invert:
            lw = lw_base + lw_step * (Lmax - float(lev))
        else:
            lw = lw_base + lw_step * float(lev)
        
        cs = ax.contour(Z, levels=[lev], colors=color, linestyles=ls,
                       linewidths=lw, alpha=0.8)
        cs_sets.append(cs)
    
    return cs_sets


def plot_cross_with_text(ax, coord, text, color, offset_pts=(10, 0), marker='x'):
    """Plot quasar image marker with label."""
    ax.plot(coord.ra.deg, coord.dec.deg, marker=marker, mew=2.0, ms=16,
            color=color, transform=ax.get_transform('world'))
    ax.annotate(text, xy=(coord.ra.deg, coord.dec.deg),
                xycoords=ax.get_transform('world'),
                textcoords='offset points', xytext=offset_pts,
                ha='left', va='center', color=color)


def set_rect_window(ax, wcs, center, half_w_arcsec=30, half_h_arcsec=30):
    """Set rectangular window with specified size in arcseconds."""
    # Convert to pixels
    pixscale_arcsec = np.sqrt(wcs.pixel_scale_matrix[0, 0]**2 + wcs.pixel_scale_matrix[0, 1]**2) * 3600
    half_w_pix = half_w_arcsec / pixscale_arcsec
    half_h_pix = half_h_arcsec / pixscale_arcsec
    
    cx, cy = wcs.all_world2pix(center.ra.deg, center.dec.deg, 0)
    
    ax.set_xlim(cx - half_w_pix, cx + half_w_pix)
    ax.set_ylim(cy - half_h_pix, cy + half_h_pix)


def sample_value_at(coord, data, wcs):
    """Sample value at a sky coordinate."""
    try:
        x, y = wcs.all_world2pix(coord.ra.deg, coord.dec.deg, 0)
        xi, yi = int(np.rint(x)), int(np.rint(y))
        ny, nx = data.shape
        if 0 <= xi < nx and 0 <= yi < ny:
            return float(data[yi, xi])
        return np.nan
    except Exception as e:
        return np.nan


def plot_sample_timedelay(timedelay_fits, config, output_path, timedelay_dir=None):
    """
    Create a contour plot for a single sample's time delay map.
    
    Args:
        timedelay_fits: Path to time delay FITS file
        config: Configuration dictionary
        output_path: Path to save output PDF file
        timedelay_dir: Directory containing time delay FITS files (used for image.dat inference)
    """
    try:
        with fits.open(timedelay_fits) as hdul:
            # Use EXT2 (DAYS_REL) for the plot
            td_data = hdul[2].data.astype(np.float64)
            td_header = hdul[2].header
        
        wcs = WCS(td_header).celestial
        Z = np.ma.masked_invalid(td_data)
        
        # Get configuration
        levels = np.array(config['contours']['levels'])
        label_levels = config['contours'].get('label_levels', [])
        color = config['contours']['color']
        lw_base = config['display'].get('lw_base', 1.0)
        lw_step = config['display'].get('lw_step', 0.001)
        lw_invert = config['display'].get('lw_invert', True)
        center_str = config['display']['center_str']
        half_size_arcsec = config['display']['half_size_arcsec']
        
        # Determine image locations - read per-sample image.dat
        image_locations_config = config.get('image_locations', {})
        
        if image_locations_config == "infer_from_image.dat":
            # Extract sample name from timedelay FITS filename
            # Format: sample_XXXXX_z1.524_timedelay.fits -> sample_XXXXX_z1.524_poten_image.dat
            td_filename = Path(timedelay_fits).name
            poten_filename = td_filename.replace('_timedelay.fits', '')
            
            image_dat_dir = config.get('image_dat_directory', 'output/poten/selected_output')
            image_dat_path = Path(image_dat_dir) / f"{poten_filename}_image.dat"
            
            # Get ID mapping and mode from config
            image_object_ids = config.get('image_object_ids', ['A1', 'A2', 'A3'])
            id_mapping = config.get('image_dat_object_id_mapping', {oid: oid for oid in image_object_ids})
            image_dat_mode = config.get('image_dat_mode', 'true')
            
            print(f"    Reading image coordinates from: {image_dat_path}", flush=True)
            image_coords_dict = read_image_dat_coordinates(str(image_dat_path), image_object_ids, id_mapping, mode=image_dat_mode)
            print(f"    Result: {image_coords_dict}", flush=True)
            
            if image_coords_dict is None:
                print(f"    WARNING: Could not read image.dat, using fallback from config", flush=True)
                image_locations = config.get('image_locations', {})
                if not image_locations:
                    print("    ERROR: No fallback image_locations in config", flush=True)
                    return False
            else:
                print(f"    Using inferred image locations: {image_coords_dict}", flush=True)
                image_locations = image_coords_dict
        else:
            # Use default hardcoded locations
            print(f"    Using hardcoded image locations from config", flush=True)
            image_locations = config.get('image_locations', {})
        
        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(10, 10), subplot_kw={"projection": wcs})
        ax.set_aspect('equal', adjustable='box')
        ax.set_xlabel("RA (J2000)")
        ax.set_ylabel("Dec (J2000)", labelpad=-0.3)
        
        # Draw contours
        cs_sets = draw_alternating_contours(ax, Z, levels, color=color,
                                           lw_base=lw_base, lw_step=lw_step,
                                           lw_invert=lw_invert)
        
        # Plot quasar image markers at inferred/configured locations
        image_colors = config.get('image_colors', {'A1': 'red', 'A2': 'blue', 'A3': 'green'})
        image_markers = config.get('image_markers', {'A1': 'x', 'A2': 'x', 'A3': 'x'})
        image_offsets = config.get('image_offsets', {'A1': [10, 0], 'A2': [10, 0], 'A3': [10, 0]})
        
        for img_id, coord_input in image_locations.items():
            marker_color = image_colors.get(img_id, 'k')
            marker = image_markers.get(img_id, 'x')
            offset = image_offsets.get(img_id, [10, 0])
            
            # Handle both decimal coordinates (list/tuple) and sexagesimal strings
            if isinstance(coord_input, (list, tuple)):
                sc = SkyCoord(ra=coord_input[0]*u.deg, dec=coord_input[1]*u.deg)
            else:
                sc = parse_coordinate_string(coord_input)
            
            value = sample_value_at(sc, td_data, wcs)
            
            text = f"{img_id}\n{value:.0f}" if np.isfinite(value) else img_id
            plot_cross_with_text(ax, sc, text, marker_color, offset_pts=tuple(offset), marker=marker)
        
        # Configure axes
        lon = ax.coords[0]
        lat = ax.coords[1]
        lon.set_ticks_position('bt')
        lat.set_ticks_position('lr')
        lon.set_ticklabel_position('b')
        lat.set_ticklabel_position('l')
        lon.tick_params(which='both', direction='in', labelsize=16)
        lat.tick_params(which='both', direction='in', labelsize=16)
        lon.display_minor_ticks(True)
        lat.display_minor_ticks(True)
        
        # Set rectangular window
        center = parse_coordinate_string(center_str)
        set_rect_window(ax, wcs, center,
                       half_w_arcsec=half_size_arcsec/2,
                       half_h_arcsec=half_size_arcsec/2)
        
        # Add legend for contour color and redshift
        panel_annot = config.get('panel_annotations', {}).get('panel_1', {})
        z = panel_annot.get('redshift', {}).get('z', 1.524)
        
        handle = Line2D([0], [0], color=color, lw=2, linestyle='solid',
                       label=rf'$z_{{\rm source}}={z}$')
        
        # Get legend configuration
        legend_config = config.get('legends', {})
        redshift_loc = legend_config.get('redshift_location', 'upper right')
        redshift_bbox = legend_config.get('redshift_bbox_to_anchor')
        
        leg_kwargs = {
            'loc': redshift_loc,
            'frameon': True,
            'facecolor': 'white',
            'edgecolor': 'black',
            'prop': {'size': 16}
        }
        if redshift_bbox is not None:
            leg_kwargs['bbox_to_anchor'] = tuple(redshift_bbox)
        
        leg1 = ax.legend(handles=[handle], **leg_kwargs)
        leg1.get_frame().set_alpha(0.95)
        
        # Add contour level legend (subset of levels, similar to single_model)
        def _lw_for_level(lev):
            Lmax = float(np.max(levels))
            if lw_invert:
                return lw_base + lw_step * (Lmax - float(lev))
            else:
                return lw_base + lw_step * float(lev)
        
        max_handles = config['display'].get('max_legend_entries', 6)
        handles_contour = []
        
        # Select subset of label levels to show
        label_levels_arr = np.array(label_levels, dtype=float)
        if len(label_levels_arr) > max_handles:
            idx = np.linspace(0, len(label_levels_arr)-1, max_handles).astype(int)
            label_levels_subset = label_levels_arr[idx]
        else:
            label_levels_subset = label_levels_arr
        
        for lev in label_levels_subset:
            lw = _lw_for_level(lev)
            handles_contour.append(Line2D([0], [0], color='k', linestyle='solid', lw=lw,
                                         label=f"{int(lev)}"))
        
        # Get contour legend configuration
        contour_loc = legend_config.get('contour_location', 'lower left')
        contour_bbox = legend_config.get('contour_bbox_to_anchor', [0.02, -0.01])
        
        if handles_contour:
            leg2 = ax.legend(
                handles=handles_contour, 
                loc=contour_loc,
                bbox_to_anchor=tuple(contour_bbox),
                frameon=True, 
                facecolor='white', 
                edgecolor='black',
                prop={'size': 12}, 
                title=r"$\Delta t_{\rm rel}$ (days)", 
                title_fontsize=14
            )
            leg2.get_frame().set_alpha(0.95)
            ax.add_artist(leg1)  # Re-add first legend since second one replaces it
        
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return True
    
    except Exception as e:
        print(f"  Error plotting {timedelay_fits}: {e}")
        return False


def main():
    """Main entry point for plotting sample time delay maps."""
    parser = argparse.ArgumentParser(
        description="Plot time delay contour maps for sample lens models"
    )
    parser.add_argument(
        'timedelay_dir',
        help='Directory containing time delay FITS files'
    )
    parser.add_argument(
        'config_file',
        help='Configuration file (similar to single_model/timedelay/timedelay_config.json)'
    )
    parser.add_argument(
        '-output',
        default='output/timedelay/plots',
        help='Output directory for plots (default: output/timedelay/plots)'
    )
    parser.add_argument(
        '-z',
        type=float,
        default=None,
        help='Source redshift filter (only plot files with this redshift)'
    )
    
    args = parser.parse_args()
    
    # Setup plotting
    setup_latex(True, None)
    set_plot_styles(20)
    
    # Load configuration
    config = load_config(args.config_file)
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get list of time delay FITS files
    timedelay_dir = Path(args.timedelay_dir)
    timedelay_files = sorted(timedelay_dir.glob('*_timedelay.fits'))
    
    if args.z is not None:
        z_str = f'_z{args.z:.3f}'
        timedelay_files = [f for f in timedelay_files if z_str in f.name]
    
    if not timedelay_files:
        print(f"No time delay FITS files found in {timedelay_dir}")
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
    
    # Plot each sample
    print(f"\nPlotting time delay maps to: {output_dir}", flush=True)
    successful = 0
    
    for i, td_file in enumerate(sample_files, 1):
        sample_name = td_file.stem.replace('_timedelay', '')
        output_path = output_dir / f"{sample_name}_timedelay.pdf"
        
        if plot_sample_timedelay(str(td_file), config, str(output_path), timedelay_dir=str(timedelay_dir)):
            print(f"  [{i:3d}/{len(sample_files)}] {sample_name}", flush=True)
            successful += 1
        else:
            print(f"  [{i:3d}/{len(sample_files)}] {sample_name} (FAILED)", flush=True)
    
    # Plot best-fit if available
    if best_fit_file:
        sample_name = best_fit_file.stem.replace('_timedelay', '')
        output_path = output_dir / f"{sample_name}_timedelay.pdf"
        
        if plot_sample_timedelay(str(best_fit_file), config, str(output_path), timedelay_dir=str(timedelay_dir)):
            print(f"  [BEST-FIT] {sample_name}")
            successful += 1
        else:
            print(f"  [BEST-FIT] {sample_name} (FAILED)")
    
    print(f"\n✓ Successfully plotted {successful} time delay maps")
    print(f"✓ Plots saved to: {output_dir}")


if __name__ == '__main__':
    main()
