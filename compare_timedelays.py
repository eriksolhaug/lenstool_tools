#!/usr/bin/env python3
"""
Compare timedelay FITS files from extract_timedelays with the working version from single_model.
"""

import numpy as np
from astropy.io import fits
import sys

# Pick one sample file to compare
sample_file = "/Users/eriksolhaug/Research/Tools/lenstool_tools/dec19a_model_solhaug/output/timedelay/sample_00027_z1.524_timedelay.fits"
reference_file = "/Users/eriksolhaug/Research/Tools/lenstool_tools/single_model/tmp.test/tau_onimg_1.fits"

print("Comparing timedelay FITS files...")
print(f"New file: {sample_file}")
print(f"Reference file: {reference_file}")
print()

try:
    # Load both files
    with fits.open(sample_file) as hdul_new:
        data_new_sec = hdul_new[0].data.astype(np.float64)
        data_new_days = hdul_new[1].data.astype(np.float64)
        data_new_rel = hdul_new[2].data.astype(np.float64)
    
    with fits.open(reference_file) as hdul_ref:
        data_ref_sec = hdul_ref[0].data.astype(np.float64)
        data_ref_days = hdul_ref[1].data.astype(np.float64)
        data_ref_rel = hdul_ref[2].data.astype(np.float64)
    
    print("SECONDS (EXT0):")
    diff_sec = np.abs(data_new_sec - data_ref_sec)
    print(f"  Max diff: {diff_sec.max():.6e}")
    print(f"  Mean diff: {diff_sec.mean():.6e}")
    print(f"  Std diff: {diff_sec.std():.6e}")
    match_sec = diff_sec.max() < 1e-3
    print(f"  Match: {match_sec}")
    print()
    
    print("DAYS (EXT1):")
    diff_days = np.abs(data_new_days - data_ref_days)
    print(f"  Max diff: {diff_days.max():.6e}")
    print(f"  Mean diff: {diff_days.mean():.6e}")
    print(f"  Std diff: {diff_days.std():.6e}")
    match_days = diff_days.max() < 1e-3
    print(f"  Match: {match_days}")
    print()
    
    print("DAYS_REL (EXT2):")
    diff_rel = np.abs(data_new_rel - data_ref_rel)
    print(f"  Max diff: {diff_rel.max():.6e}")
    print(f"  Mean diff: {diff_rel.mean():.6e}")
    print(f"  Std diff: {diff_rel.std():.6e}")
    match_rel = diff_rel.max() < 1e-3
    print(f"  Match: {match_rel}")
    print()
    
    if match_sec and match_days and match_rel:
        print("✓ FILES MATCH PERFECTLY!")
    else:
        print("✗ Files differ - investigating...")
        
        # Show some sample values
        print(f"\nSample values at pixel (256, 256):")
        print(f"  New - Seconds: {data_new_sec[256, 256]:.6e}, Days: {data_new_days[256, 256]:.6e}, Days_rel: {data_new_rel[256, 256]:.6e}")
        print(f"  Ref - Seconds: {data_ref_sec[256, 256]:.6e}, Days: {data_ref_days[256, 256]:.6e}, Days_rel: {data_ref_rel[256, 256]:.6e}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
