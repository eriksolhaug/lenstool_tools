#!/usr/bin/env python
"""Test script to extract enclosed mass from mass_nopot6.fits"""
import sys
import numpy as np
from pathlib import Path
import importlib.util

# Import directly from the module file
spec = importlib.util.spec_from_file_location(
    'mass_statistics', 
    'lenstool_tools/mass_statistics.py'
)
mass_statistics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mass_statistics)

extract_enclosed_mass = mass_statistics.extract_enclosed_mass

# Parameters from mass_config.json
z_lens = 0.4301
aperture_kpc = 200.0
# mass_fits_file = Path('dec19a_model_solhaug/input_test/fits/mass_nopot6.fits')
mass_fits_file = Path('dec19a_model_solhaug/output/mass/sample_best_z0.4301_mass.fits')

print(f'Extracting enclosed mass from: {mass_fits_file}')
print(f'Lens redshift: {z_lens}')
print(f'Aperture radius: {aperture_kpc} kpc\n')

# Extract enclosed mass
mass_result = extract_enclosed_mass(
    mass_fits_file=mass_fits_file,
    z_lens=z_lens,
    aperture_kpc=aperture_kpc
)

print(f'Enclosed mass within {aperture_kpc} kpc aperture: {mass_result:.4e} solar masses')
if not np.isnan(mass_result):
    print(f'In 10^12 solar masses: {mass_result/1e12:.4e}')
else:
    print('Extraction failed: result is NaN')
