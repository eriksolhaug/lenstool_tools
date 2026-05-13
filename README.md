# lenstool_tools

A toolkit for generating and analyzing gravitational lens samples using lenstool.

## Quick Start

All commands below assume you're working within a model directory (e.g., `dec19a_model_solhaug/`).

### Generate samples

```bash
python -m lenstool_tools.generate_samples input/BAYES.DAT input/BESTOPT.PAR -runmode config/SAMPLE_GENERATION.json -bestopt input/BESTOPT.PAR -zlens 0.4301 -zsource 1.524 -output .
```

### Run samples

Run all:
```bash
python -m lenstool_tools.run_samples sample_input output -workdir . -config config/RUN_SAMPLES_CONFIG.json
```

Run just the files belonging to a specified redshift:
```bash
python -m lenstool_tools.run_samples sample_input output -workdir . -redshift 1.939 -config config/RUN_SAMPLES_CONFIG.json
```

### Extract magnifications

```bash
python -m lenstool_tools.extract_magnifications config/MAGNIFICATION_CONFIG.json MAGNIFICATIONS.csv
```

### Produce magnification statistics

```bash
python -m lenstool_tools.magnification_statistics MAGNIFICATIONS.csv -redshift 1.524 -sigma 1.0 -ampli output/ampli -config config/MAGNIFICATION_CONFIG.json
```

### Produce mass statistics

```bash
python -m lenstool_tools.mass_statistics output/mass config/MASS_CONFIG.json -redshift 0.4301 -sigma 1.0
```

### Extract time delays

```bash
python -m lenstool_tools.extract_timedelays output/poten config/TIMEDELAYS_CONFIG.json -output output/timedelay -z 1.524
```

### Plot time delay maps

```bash
python -m lenstool_tools.plot_sample_timedelays output/timedelay config/TIMEDELAYS_CONFIG.json -output statistics/timedelay/timedelay_maps -z 1.524
```

### Produce time delay statistics

```bash
python -m lenstool_tools.timedelay_statistics output/timedelay config/TIMEDELAYS_CONFIG.json -output statistics/timedelay -z 1.524
```

## Notes

- Replace capitalized names (e.g., `BAYES.DAT`, `BESTOPT.PAR`) with your actual file names
- All commands assume your model directory contains `input/`, `config/`, and `output/` subdirectories
- Configuration files (`.json`) should be placed in the `config/` directory

## Architecture

### Single-File Sample Generation (Current)

As of January 2026, sample generation uses a simplified single-file approach:

- **One file per sample**: `sample_NNNNN.par` contains ALL outputs (mass, ampli, dpl, poten)
- **Simplified execution**: Each sample is processed once by lenstool (not twice)
- **Cleaner codebase**: No need for special workarounds or separate poten file generation

**Key Fix**: Core radius parameters are set to `0.000001` instead of `0.0` to prevent NaN values in potential map calculations. This eliminates the need for separate poten-only files or special handling.

See `lenstool_tools/backup/ARCHITECTURE_CHANGES.txt` for details about the previous two-file approach and why it was changed.

## Installation

```bash
pip install -e .
```

## Usage

### Generate Sample Files

```bash
python -c "from lenstool_tools import generate_sample_input_files; generate_sample_input_files('tests/bayes.dat', 'tests/input.par')"
```

### Select and Generate Subset of Samples

```bash
python -c "from lenstool_tools import generate_sample_input_files; generate_sample_input_files('tests/bayes.dat', 'tests/input.par', sample_selection_config_file='tests/sample_selection_config.json')"
```

### Run Lenstool on Samples

```bash
cd samples
lenstool input/sample_00001.par -n
```

Or batch process all samples:

```bash
python -m lenstool_tools.run_samples samples/input samples/output -workdir samples/
```

**Output Files Generated**

Each `sample_NNNNN.par` file produces the following outputs in the `output/` directory:
- `ampli/sample_NNNNN_z*.fits` - Amplification map
- `dpl/sample_NNNNN_z*.fits` - Displacement field (x and y components)
- `poten/sample_NNNNN_z*.fits` - Gravitational potential map
- `mass/sample_NNNNN_z*.fits` - Mass distribution map (when lens redshift specified)

All these outputs are generated in a single lenstool run (not separate runs). There are NO separate `_poten.par` files anymore.

#### How to Run LENSTOOL-TOOLS to Extract Uncertainties

Complete workflow to generate samples, run lenstool, and extract magnification, mass, and time delay statistics:

**Configuration Files:**

Before running samples, ensure you have the required configuration files:

1. **`.lenstool_env`** - Specifies the conda environment name for lenstool (located in `lenstool_tools/.lenstool_env`). By default it contains `lenstool_env8`. Edit this file if your lenstool environment has a different name:
   ```
   your_custom_env_name
   ```

2. **`config/run_samples_config.json`** - Specifies which output files to save after each run (see Run samples section below).

**Generate samples:**
```bash
python -m lenstool_tools.generate_samples input/bayes.dat input/input.par -runmode config/sample_generation_config.json -bestopt input/bestopt.par -zlens 0.4301 -zsource 1.524 -output .

python -m lenstool_tools.generate_samples input/bayes.dat input/input.par -runmode config/sample_generation_config.json -bestopt input/bestopt.par -zsource 1.939 -output .
```

**Run samples:**

The `-config` parameter specifies a JSON configuration file that controls which output files to save after each lenstool run. The configuration file should contain a `save_output_files` section listing the files to preserve (e.g., `image.dat`, `source.dat`). After each sample completes successfully, these files are copied to `output/selected_output/` with the sample name prepended.

**If you don't specify the config file:** The script will still run lenstool on all samples and generate output files, but it will NOT automatically save the intermediate files to the selected_output directory. You would need to manually copy them yourself.

**Example config file** (`config/run_samples_config.json`):
```json
{
  "save_output_files": {
    "poten": [
      "image.dat",
      "image.all",
      "source.dat"
    ]
  }
}
```

Run all:
```bash
cd /Users/eriksolhaug/Research/Tools/lenstool_tools/dec19a_model_solhaug && python -m lenstool_tools.run_samples sample_input output -workdir . -config config/run_samples_config.json
```

Run just the files belonging to the specified redshift:
```bash
python -m lenstool_tools.run_samples sample_input output -workdir . -config config/run_samples_config.json -redshift 1.939
```

**Extract magnification:**
```bash
python -m lenstool_tools.extract_magnifications config/magnification1.524_config.json magnifications.csv
```

**Produce magnification statistics:**
```bash
python -m lenstool_tools.magnification_statistics magnifications.csv -redshift 1.524 -sigma 1.0 -ampli output/ampli -config config/magnification1.524_config.json
```

**Produce mass statistics:**
```bash
python -m lenstool_tools.mass_statistics output/mass config/mass_config.json -redshift 0.4301 -sigma 1.0
```

**Extract timedelays:**
```bash
python -m lenstool_tools.extract_timedelays output/poten config/timedelays_z1.524.json -output output/timedelay -z 1.524

python -m lenstool_tools.extract_timedelays output/poten config/timedelays_z1.939.json -output output/timedelay -z 1.939
```

**Plot timedelay maps:**
```bash
python -m lenstool_tools.plot_sample_timedelays output/timedelay config/timedelays_z1.524.json -output statistics/timedelay/timedelay_maps -z 1.524
```

## Quickstart Example: COOLJ1153

### Complete Pipeline Script

Run the entire analysis pipeline in one go:

```bash
#!/bin/bash
cd /path/to/lenstool_tools

# Clean previous outputs
rm -rf samples/sample_input samples/output samples/statistics samples/magnifications.csv

# Step 1: Generate samples (both redshifts)
echo "Step 1: Generating samples with lens and source redshifts..."
python -m lenstool_tools.generate_samples \
  samples/input/bayes.dat \
  samples/input/bestopt.par \
  -runmode tests/sample_generation_config.json \
  -bestopt samples/input/bestopt.par \
  -zlens 0.4301 \
  -zsource 1.524

# Step 2: Generate poten-only files
echo "Step 2: Generating poten-only files..."
python -m lenstool_tools.generate_samples \
  samples/input/bayes.dat \
  samples/input/bestopt.par \
  -runmode tests/sample_generation_config.json \
  -bestopt samples/input/bestopt.par \
  -zsource 1.524

# Step 3: Run lenstool
echo "Step 3: Running lenstool on all samples..."
cd samples
python -m lenstool_tools.run_samples sample_input output -workdir .

# Step 4: Extract magnifications
echo "Step 4: Extracting magnifications..."
python -m lenstool_tools.extract_magnifications \
  ../tests/magnification1.524_config.json \
  magnifications.csv

# Step 5: Plot magnification maps
echo "Step 5: Plotting magnification maps..."
python -m lenstool_tools.plot_sample_magnifications \
  magnifications.csv \
  output/ampli/plots \
  -redshift 1.524 \
  -config ../tests/plot_magnifications_config.json \
  -ampli output/ampli

# Step 6: Generate magnification statistics
echo "Step 6: Generating magnification statistics..."
python -m lenstool_tools.magnification_statistics \
  magnifications.csv \
  -redshift 1.524 \
  -sigma 1.0 \
  -output statistics/magnification \
  -ampli output/ampli \
  -config ../tests/magnification1.524_config.json

# Step 7: Generate mass statistics
echo "Step 7: Generating mass statistics..."
python -m lenstool_tools.mass_statistics \
  output/mass \
  ../tests/mass_config.json \
  -redshift 0.4301 \
  -output statistics/mass \
  -sigma 1.0

# Step 8: Extract time delay surfaces
echo "Step 8: Extracting time delay surfaces..."
python -m lenstool_tools.extract_timedelays \
  output/poten \
  ../tests/timedelay_config.json \
  -output output/timedelay

# Step 10: Plot time delay contour maps
echo "Step 10: Plotting time delay contour maps..."
python -m lenstool_tools.plot_sample_timedelays \
  output/timedelay \
  ../tests/plot_sample_timedelays_config.json \
  -z 1.524

# Step 11: Generate time delay statistics
echo "Step 11: Generating time delay statistics..."
python -m lenstool_tools.timedelay_statistics \
  output/timedelay \
  ../tests/timedelay_config.json \
  -output statistics/timedelay \
  -z 1.524

echo "✓ Analysis pipeline complete!"
cd ..
```

#### COOLJ1153B (z=1.939)
```bash
# Generate samples
cd /Users/eriksolhaug/Research/Tools/lenstool_tools && python -m lenstool_tools.generate_samples input/bayes.dat input/input.par -runmode ../tests/sample_generation_config.json -bestopt input/bestopt.par -zsource 1.939

# Run samples
cd /Users/eriksolhaug/Research/Tools/lenstool_tools/samples && python -m lenstool_tools.run_samples sample_input output -workdir . -redshift 1.939 -config ../tests/run_samples_config.json
```

### Configuration Files Used

**`tests/sample_generation_config.json`** - Consolidated configuration for sample generation:
```json
{
  "sample_selection": {
    "num_samples": 100,
    "random_seed": 42
  },
  "output_files": [
    {"name": "ampli", "float1": 1.524, "directory": "output/ampli"},
    {"name": "poten", "float1": 1.524, "directory": "output/poten"}
  ],
  "output_base_directories": {
    "ampli": "output/ampli",
    "poten": "output/poten"
  },
  "bayes_file": {
    "convert_r_to_kpc": true,
    "size_arcsec_to_kpc": 5.611
  }
}
```

**`tests/plot_magnifications_config.json`** - Configuration for magnification visualization:
```json
{
  "display": {
    "colormap": "Blues",
    "scaling": {
      "method": "percentile",
      "vmin_pct": 1.5,
      "vmax_pct": 98.5
    }
  },
  "objects": [
    {"name": "A1", "ra": 178.8475, "dec": 12.3257, "marker": "x", "color": "red"},
    {"name": "A2", "ra": 178.8520, "dec": 12.3205, "marker": "x", "color": "red"},
    {"name": "A3", "ra": 178.8510, "dec": 12.3310, "marker": "x", "color": "red"}
  ]
}
```

### Key Parameters Explained

| Parameter | Value | Meaning |
|-----------|-------|---------|
| `-zlens` | 0.4301 | Lens (cluster) redshift |
| `-zsource` | 1.524 | Source (lensed object) redshift |
| `size_arcsec_to_kpc` | 5.611 | Conversion from arcsec (bayes.dat) to kpc (.par files) at z=0.4301 |
| `num_samples` | 100 | Number of random samples to generate from MCMC chain |
| `random_seed` | 42 | Reproducible random selection |
| `colormap` | Blues | Magnification map color scheme |
| `scaling.method` | percentile | Use 1.5%-98.5% for robust color scaling |

### Troubleshooting

**Issue: "No FITS files found"**
- Ensure lenstool executed successfully (check for error messages in Step 4)
- Verify output directory structure: `samples/output/ampli/`, `samples/output/mass/`, etc.

**Issue: Magnification values seem incorrect**
- Check that `-redshift 1.524` matches the source redshift used in Step 2
- Verify `size_arcsec_to_kpc: 5.611` is correct for your lens redshift and cosmology

**Issue: Empty statistics with NaN values or missing best-fit values**
- This is normal if `-ampli` and `-config` flags are omitted from magnification_statistics
- Best-fit values require both flags to extract from FITS files
- **Important:** The config file must match your redshift suffix (e.g., `magnification1.524_config.json` for z=1.524, not `magnification_config.json`)

### Additional Notes on This Quickstart

- All commands assume you're in the `/path/to/lenstool_tools` directory
- Statistics use 1.0σ confidence interval (68% confidence) by default
- Magnification maps use percentile scaling for robust color normalization
- The arcsec-to-kpc conversion is critical for accurate sample models
- Total execution time: ~10-30 minutes depending on hardware (202 lenstool runs)

### Important Notes on Potential Files

When generating potential (poten) files via the `-zsource` flag, be aware of the following:

**Issue:** Potential maps may contain only NaN values if a potential component is positioned far from the reference coordinate system origin (e.g., +180 arcsec West, -80 arcsec South). This can occur when lens models include distant components or line-of-sight structures.

**Solution:** To handle models with potentials far from the reference coordinate, you can:
1. Generate potential files as normal and check for NaN values in the output FITS files
2. For models with distant potentials (e.g., second line-of-sight clusters), consider adjusting the potential output coordinate system or using alternative analysis methods
3. Pre-filter samples if distant potentials are known to be problematic for your analysis

The potential output coordinate system in lenstool defaults to the reference image coordinates, so potentials positioned far outside this reference frame may not produce valid pixel values.

### Extract Magnifications from Amplification Maps

After running lenstool on samples, extract magnifications at specified object coordinates:

```bash
cd samples
python -m lenstool_tools.extract_magnifications ../tests/magnification_config.json magnifications.csv
```

This creates a CSV file where:
- Each row is a different sample lens model
- Each column is an object (A1, A2, etc.) with extracted magnification value
- Magnifications are extracted from the amplification FITS maps at the specified RA/Dec coordinates

### Generate Magnification Statistics

After extraction, compute statistics and confidence intervals:

```bash
cd samples
python -m lenstool_tools.magnification_statistics magnifications.csv \
  -redshift 1.524 \
  -sigma 1.0 \
  -ampli output/ampli \
  -config ../tests/magnification_config.json
```

Output includes:
- `magnification_statistics_z1.524.csv`: Median, mean, and error bars for each object
- `magnification_report_z1.524.txt`: Detailed human-readable report with interpretation
- `magnification_distribution_z1.524.png`: Histograms showing distribution and best-fit values

### Generate Mass Statistics

Compute enclosed mass statistics within an aperture:

```bash
cd samples
python -m lenstool_tools.mass_statistics output/mass ../tests/mass_config.json \
  -redshift 0.4301 \
  -sigma 1.0
```

Configuration (mass_config.json):
```json
{
  "cosmology": {
    "z_lens": 0.4301,
    "angular_diameter_distance_kpc": null  # null = use astropy calculation
  },
  "aperture": {
    "aperture_kpc": 200.0
  }
}
```

Output includes:
- `mass_statistics_z0.4301.csv`: Median, mean, and error bars for enclosed mass
- `mass_report_z0.4301.txt`: Detailed report with mass values and uncertainties
- `mass_distribution_z0.4301.png`: Histogram showing mass distribution and best-fit

## Important Notes

### Lenstool Version Compatibility

When attempting to output potential (poten) files, **use lenstool-6.5** instead of lenstool-7.1.1. Version 7.1.1 may have issues with writing the potential FITS files. You can manage multiple versions using conda:

```bash
conda create -n lenstool_6.5 -c conda-forge lenstool=6.5
conda activate lenstool_6.5
```

Then update the `run_samples.py` to use the correct conda environment or modify the environment variable accordingly.

## Directory Structure

```
lenstool_tools/
├── lenstool_tools/           # Main package
│   ├── __init__.py
│   ├── samples.py            # Core sample handling functions
│   ├── parameter_mapping.py  # Parameter mapping utilities
│   ├── generate_samples.py   # Sample generation module
│   ├── run_samples.py        # Lenstool execution module
│   └── extract_magnifications.py  # Magnification extraction module
├── tests/
│   ├── bayes.dat             # MCMC chain data
│   ├── input.par             # Template input file
│   ├── cats/                 # Catalog files
│   ├── *.json                # Configuration files
│   ├── runmode_config.json   # Output file configuration
│   └── magnification_config.json  # Magnification extraction config
└── samples/
    ├── cats/                 # Catalog files (symlink/copy)
    ├── input/                # Generated sample_XXXXX.par files
    ├── output/
    │   ├── ampli/            # Amplification maps (FITS)
    │   └── poten/            # Potential maps (FITS)
    └── magnifications.csv    # Extracted magnification results
```

## Configuration Files

### sample_selection_config.json

```json
{
  "num_samples": 100,
  "random_seed": 42
}
```

### runmode_config.json

Specifies output directories for ampli and poten files:

```json
{
  "output_files": [
    {
      "name": "ampli",
      "float1": 1.524,
      "directory": "output/ampli"
    },
    {
      "name": "poten",
      "float1": 1.524,
      "directory": "output/poten"
    }
  ]
}
```

### magnification_config.json

Specifies which amplification map to use and which objects to extract magnifications for:

```json
{
  "description": "Configuration for extracting magnifications from amplification maps",
  "amplification": {
    "name": "ampli",
    "float1": 1.524,
    "directory": "../samples/output/ampli"
  },
  "objects": [
    {
      "object_id": "A1",
      "ra": 178.33523,
      "dec": 7.93357
    },
    {
      "object_id": "A2",
      "ra": 178.33687,
      "dec": 7.93285
    }
  ]
}
```

Each object specifies:
- `object_id`: Unique identifier for the object (e.g., "A1", "B1")
- `ra`: Right Ascension in degrees
- `dec`: Declination in degrees

The output CSV will have one row per sample and one column per object.

## Magnification Extraction Workflow

After running lenstool to generate amplification maps (ampli FITS files), you can extract magnification values at specific object coordinates.

### Overview

The magnification extraction process:
1. Loads amplification FITS files from the output directory
2. Uses WCS (World Coordinate System) to convert RA/Dec coordinates to pixel coordinates
3. Extracts the magnification value at each object's position
4. Compiles results into a CSV file with one row per sample and one column per object

### Complete Example Workflow

```bash
# 1. Generate 100 samples from MCMC chain
python -c "from lenstool_tools import generate_sample_input_files; \
  generate_sample_input_files('tests/bayes.dat', 'tests/input.par', \
  sample_selection_config_file='tests/sample_selection_config.json')"

# 2. Run lenstool on all samples
python -m lenstool_tools.run_samples samples/input samples/output -workdir samples/

# 3. Extract magnifications at object coordinates
cd samples
python -m lenstool_tools.extract_magnifications ../tests/magnification_config.json magnifications.csv

# 4. Analyze the results
python -c "import pandas as pd; df = pd.read_csv('magnifications.csv'); print(df)"
```

### Output CSV Format

The output CSV contains:
- **sample**: Sample identifier (e.g., "sample_00014")
- **fits_file**: Name of the source FITS file
- **Object columns** (A1, A2, A3, B1, B2, B3, etc.): Magnification values at each object's coordinates

Example output:
```
sample,fits_file,A1,A2,A3,B1,B2,B3
sample_00014,sample_00014_1.524_ampli.fits,11.679,5.832,172.610,2.257,0.750,3.834
sample_00052,sample_00052_1.524_ampli.fits,9.456,6.638,34.283,2.350,0.816,3.557
sample_00055,sample_00055_1.524_ampli.fits,10.000,6.188,68.550,2.514,0.774,3.544
```

### Customizing Object Coordinates

Edit `tests/magnification_config.json` to specify different objects:

```json
{
  "amplification": {
    "name": "ampli",
    "float1": 1.524,
    "directory": "../samples/output/ampli"
  },
  "objects": [
    {
      "object_id": "MyObject",
      "ra": 178.33523,
      "dec": 7.93357
    }
  ]
}
```

**Key fields:**
- `object_id`: String identifier for the object (appears as CSV column header)
- `ra`: Right Ascension in decimal degrees
- `dec`: Declination in decimal degrees

### Technical Details

**Coordinate Transformation:**
- Uses astropy's WCS (World Coordinate System) to transform world coordinates (RA/Dec) to pixel coordinates
- The transformation reads WCS information from the FITS header
- Pixel values are rounded to nearest integer and bounds-checked

**Magnification Extraction:**
- Retrieves the pixel value at the calculated position
- Returns absolute value (for handling potentially negative values in some conventions)
- Returns NaN if coordinate falls outside the image boundaries

**Error Handling:**
- Invalid FITS files are skipped with error reporting
- Coordinates outside image bounds are reported as NaN
- Processing continues even if individual files fail

### Using the Extracted Data

Once you have the magnifications CSV, you can analyze it with pandas:

```python
import pandas as pd
import numpy as np

# Load magnifications
df = pd.read_csv('magnifications.csv')

# Calculate statistics per object
print("Mean magnifications:")
print(df[['A1', 'A2', 'A3', 'B1', 'B2', 'B3']].mean())

# Find samples with specific magnification ranges
bright_A1 = df[df['A1'] > 10]
print(f"Samples with A1 > 10: {len(bright_A1)}")

# Export for further analysis
df.to_csv('magnifications_analysis.csv', index=False)
```

### Command-line Usage

```bash
# Basic usage
extract-magnifications tests/magnification_config.json magnifications.csv

# From samples directory
cd samples
python -m lenstool_tools.extract_magnifications ../tests/magnification_config.json magnifications.csv
```

### Requirements

The magnification extraction requires:
- `astropy` (for FITS I/O and WCS transformations)
- `pandas` (for CSV output)
- `numpy` (for array operations)

All are included in standard scientific Python distributions.

## Magnification Statistics and Confidence Intervals

After extracting magnifications, you can generate statistics, histograms, and confidence intervals for each object.

### Overview

The magnification statistics module:
1. Loads the magnifications CSV file
2. Calculates median, mean, and standard deviation for each object
3. Computes confidence intervals at specified sigma levels
4. Creates histograms showing the magnification distributions
5. Outputs both visualizations and CSV summary

### Confidence Intervals

The module calculates symmetric confidence intervals around the median:
- **1.0σ** (default): ~68.3% confidence interval
- **2.0σ**: ~95.4% confidence interval
- **3.0σ**: ~99.7% confidence interval

Each interval is defined as: `[median - σ·std, median + σ·std]`

### Usage

```bash
# Default: 1 sigma confidence interval, 20 histogram bins
python -m lenstool_tools.magnification_statistics magnifications.csv

# Custom output directory
python -m lenstool_tools.magnification_statistics magnifications.csv -output results/stats

# Different sigma level (2 sigma = 95% confidence)
python -m lenstool_tools.magnification_statistics magnifications.csv -sigma 2.0

# Custom histogram bins
python -m lenstool_tools.magnification_statistics magnifications.csv -bins 30

# All options combined
python -m lenstool_tools.magnification_statistics magnifications.csv \
  -output results/stats -sigma 2.0 -bins 25
```

### Output Files

#### Histograms
Individual PNG histograms are created for each object showing:
- Distribution of magnifications across all samples
- Median (red dashed line)
- Mean (green dashed line)
- Confidence interval (shaded yellow region)
- Sample count and standard deviation in title

Files: `<object_id>_histogram.png`

#### Statistics CSV
Summary statistics file: `magnification_statistics.csv`

Contains rows for:
- **median**: Median magnification value
- **mean**: Mean magnification value
- **lower_<sigma>sigma**: Lower confidence interval bound
- **upper_<sigma>sigma**: Upper confidence interval bound

Example (1 sigma):
```
statistic,A1,A2,A3,B1,B2,B3
median,9.935,6.303,50.068,2.318,0.782,3.590
mean,10.039,6.314,69.020,2.358,0.782,3.637
lower_1.0sigma,9.130,6.018,2.127,2.220,0.761,3.459
upper_1.0sigma,10.739,6.587,98.010,2.416,0.802,3.721
```

### Complete Workflow Example

```bash
# 1. Generate and run lenstool on samples
python -m lenstool_tools.generate_samples tests/bayes.dat tests/input.par
cd samples
python -m lenstool_tools.run_samples ../samples/input output -workdir .

# 2. Extract magnifications
python -m lenstool_tools.extract_magnifications ../tests/magnification_config.json magnifications.csv

# 3. Generate statistics and histograms
python -m lenstool_tools.magnification_statistics magnifications.csv -sigma 1.0

# 4. Analyze results
python << 'PYTHON'
import pandas as pd
stats = pd.read_csv('statistics/magnification/magnification_statistics.csv')
print(stats)

# Extract just the median values
medians = stats[stats['statistic'] == 'median'].iloc[0, 1:]
print("\nMedian magnifications:", medians.to_dict())
PYTHON
```

### Customizing Histogram Generation

The histograms can be customized by modifying the source code or by using the options:
- `-bins N`: Number of histogram bins (default: 20)
- `-sigma X`: Confidence interval level (default: 1.0)

### Statistical Interpretation

**Example interpretation with σ=1.0:**
```
A1: median=9.935, lower_1σ=9.130, upper_1σ=10.739
```

This means:
- The typical (median) magnification is 9.935
- There's a ~68% probability the true magnification lies between 9.130 and 10.739
- The standard deviation is approximately (10.739 - 9.130) / 2 = 0.804

**Example interpretation with σ=2.0:**
```
A1: median=9.935, lower_2σ=8.326, upper_2σ=11.543
```

This means:
- There's a ~95% probability the true magnification lies between 8.326 and 11.543

### Command-line Reference

```bash
magnification-statistics <magnifications_csv> [OPTIONS]

Options:
  -output DIR      Output directory (default: statistics/magnification)
  -sigma SIGMA     Confidence interval in sigma (default: 1.0)
  -bins BINS       Number of histogram bins (default: 20)

Examples:
  magnification-statistics magnifications.csv
  magnification-statistics magnifications.csv -output results/stats
  magnification-statistics magnifications.csv -sigma 2.0
  magnification-statistics magnifications.csv -sigma 1.0 -bins 30
```

### Requirements

The magnification statistics module requires:
- `matplotlib` (for histogram generation)
- `pandas` (for CSV handling)
- `numpy` (for statistics calculations)

All can be installed with: `pip install matplotlib pandas numpy`

## Enclosed Mass Statistics and Confidence Intervals

After running lenstool to generate mass maps (mass FITS files), you can extract enclosed masses within a specified aperture radius and compute statistics.

### Overview

The mass statistics module:
1. Loads mass FITS files from the output directory (in units of 1e12 M_sun/pixel)
2. Converts mass per pixel to surface density (M_sun/kpc²) using cosmological calculations
3. Integrates mass within a specified aperture radius (in kpc)
4. Computes median, mean, and confidence intervals for the enclosed mass
5. Creates histograms and summary reports
6. Extracts best-fit mass from sample_best.par output (if available)

### Usage

```bash
# Basic usage with default aperture
python -m lenstool_tools.mass_statistics output/mass tests/mass_config.json

# With specific lens redshift
python -m lenstool_tools.mass_statistics output/mass tests/mass_config.json -redshift 0.4301

# Different confidence level (2 sigma = 95%)
python -m lenstool_tools.mass_statistics output/mass tests/mass_config.json -redshift 0.4301 -sigma 2.0

# Custom output directory and histogram bins
python -m lenstool_tools.mass_statistics output/mass tests/mass_config.json \
  -redshift 0.4301 -output results/mass_stats -bins 25
```

### Configuration File

The `mass_config.json` file specifies cosmology and aperture settings:

```json
{
  "description": "Configuration for extracting enclosed masses from mass maps",
  "cosmology": {
    "z_lens": 0.4301,
    "kpc_per_arcsec": 5.611
  },
  "aperture": {
    "aperture_kpc": 100.0,
    "sigma": 1.0
  }
}
```

**Key fields:**
- `z_lens`: Lens redshift (used for cosmological distance calculations)
- `kpc_per_arcsec`: Conversion factor from arcseconds to kpc at the lens redshift
- `aperture_kpc`: Aperture radius in kpc for mass integration (e.g., 100 kpc)
- `sigma`: Confidence level in sigma (e.g., 1.0 for 68% confidence interval)

### Output Files

#### Mass Histogram
File: `mass_distribution.png`

Shows the distribution of enclosed masses across all samples with:
- Histogram of mass values
- Median and mean lines
- Best-fit value (if available)
- Confidence interval as shaded region
- Error statistics in title

#### Statistics CSV
Files: `mass_statistics_z{redshift}.csv` or `mass_statistics.csv`

Contains statistics table with rows:
- **best**: Best-fit enclosed mass
- **median**: Median enclosed mass
- **mean**: Mean enclosed mass  
- **error_lower_{sigma}sigma**: Error magnitude below median
- **error_upper_{sigma}sigma**: Error magnitude above median

Example output (1 sigma):
```
statistic,value
best,5.5e+13
median,5.7e+13
mean,5.7e+13
error_lower_1.0sigma,1.2e+12
error_upper_1.0sigma,1.2e+12
```

#### Detailed Report
Files: `mass_report_z{redshift}.txt` or `mass_report.txt`

Human-readable report containing:
- Aperture radius and lens redshift
- Best-fit, median, and mean enclosed masses
- Confidence interval errors (negative and positive directions)
- Physical interpretation of the results

Example report section:
```
The enclosed mass within 100 kpc is:
  M = 5.722e+13 (+1.200e+12) (-1.200e+12) M_sun

This represents the total mass of the lens system within a projected radius
of 100.0 kpc from the lens center at redshift z = 0.4301.
```

### Complete Workflow with Mass Statistics

```bash
# 1. Generate and run lenstool on samples with lens redshift
cd /path/to/lenstool_tools
python -m lenstool_tools.generate_samples \
  samples/input/bayes.dat \
  samples/input/bestopt.par \
  -config tests/sample_selection_config.json \
  -bestopt samples/input/bestopt.par \
  -zlens 0.4301 \
  -zsource 1.524

cd samples
python -m lenstool_tools.run_samples input output -workdir .

# 2. Extract magnifications
python -m lenstool_tools.extract_magnifications ../tests/magnification_config.json magnifications.csv

# 3. Generate magnification statistics
python -m lenstool_tools.magnification_statistics magnifications.csv -redshift 1.524 -sigma 1.0

# 4. Generate mass statistics
python -m lenstool_tools.mass_statistics output/mass ../tests/mass_config.json -redshift 0.4301 -sigma 1.0

# 5. Analyze both results
echo "Magnification uncertainties:"
cat statistics/magnification/magnification_report_z1.524.txt
echo ""
echo "Mass uncertainties:"
cat statistics/mass/mass_report_z0.4301.txt
```

### Technical Details

**Mass Calculation Method:**
1. Load mass FITS file (units: 1e12 M_sun/pixel)
2. Calculate pixel area in kpc² using WCS information and cosmological distances
3. Convert pixel masses to surface density (M_sun/kpc²)
4. Create circular aperture mask at specified radius
5. Sum surface density within aperture and multiply by pixel area
6. Result: Enclosed mass in M_sun

**Confidence Intervals:**
- Calculated from sample distribution statistics
- Reported as symmetric errors: median ± σ·std
- Accessible via command-line argument: `-sigma 1.0`, `-sigma 2.0`, `-sigma 3.0`

**Error Reporting:**
- Errors are reported separately for positive and negative directions
- Allows asymmetric error representation if data distribution is non-Gaussian

### Command-line Reference

```bash
mass-statistics <mass_directory> <config_file> [OPTIONS]

Required:
  mass_directory      Path to directory with mass FITS files
  config_file         Path to mass_config.json

Options:
  -redshift Z         Redshift for filtering FITS files (e.g., 0.4301)
  -output DIR         Output directory (default: statistics/mass)
  -sigma SIGMA        Confidence interval in sigma (default: 1.0)
  -bins BINS          Histogram bins (default: 20)

Examples:
  mass-statistics output/mass tests/mass_config.json
  mass-statistics output/mass tests/mass_config.json -redshift 0.4301
  mass-statistics output/mass tests/mass_config.json -redshift 0.4301 -sigma 2.0
```

### Requirements

The mass statistics module requires:
- `matplotlib` (for histogram generation)
- `pandas` (for CSV handling)
- `numpy` (for array operations)
- `astropy` (for FITS I/O and WCS transformations)

All can be installed with: `pip install matplotlib pandas numpy astropy`

## Corner Plot Analysis

Generate publication-quality corner plots from lenstool Bayesian sampling output to visualize parameter distributions, correlations, and credible intervals.

### Overview

The corner plot module reads Bayesian sampling chains (e.g., from lenstool MCMC runs) and creates corner plots showing:
- **1D distributions**: Histograms with quantile lines for each parameter
- **2D correlations**: Scatter plots and contours showing parameter relationships
- **Credible intervals**: Contours at 1σ, 2σ, and 3σ confidence levels
- **Best-fit point**: Marked with crosshairs for visual reference
- **Quantile lines**: 16th, 50th (median), and 84th percentiles

### Usage

Inside the single_model/ directory:

```bash
# Basic usage
python corner/lenstool_corner.py input/bayes.dat output/corner_plot.pdf
```

### Command-line Reference

```bash
python corner/lenstool_corner.py <input_file> <output_file>

Arguments:
  input_file   Path to Bayesian output file (e.g., bayes.dat from lenstool)
  output_file  Output PDF filename (e.g., corner_plot.pdf)
```

### Input Format

The input file should be a space-separated text file with:
- **Header lines** starting with `#` indicating parameter names
- **Data lines** with numerical values (one chain step per line)

Example `bayes.dat`:
```
# O1 : x (arcsec)
# O1 : y (arcsec)
# O1 : emass
# O1 : rc (arcsec)
# O1 : sigma (km/s)
# O2 : emass
# O2 : rc (arcsec)
# O2 : sigma (km/s)
# Chi2
0.123  0.456  0.789  0.234  150.0  0.567  0.345  160.0  45.23
0.125  0.458  0.791  0.235  151.2  0.568  0.346  161.5  45.19
```

### Customization

Edit the "USER CUSTOMIZATION SECTION" in `single_model/corner/lenstool_corner.py` to control all aspects of the plot.

#### Parameter Selection

```python
param_names = [
    "O1 : emass",
    "O1 : rc (arcsec)",
    "O1 : sigma (km/s)",
    "O2 : emass",
    "O2 : rc (arcsec)",
    "O2 : sigma (km/s)",
    "Chi2"
]
```

Select which parameters to include in the corner plot by adding/removing entries from the list.

#### Confidence Intervals

```python
contour_levels = [1, 2, 3]  # Display 1σ, 2σ, and 3σ confidence levels
```

Choose which sigma levels to display. Available options: 1, 2, 3.

#### Visual Customization

```python
contour_color = "navy"                      # Color for contour lines
quantile_lines = True                       # Show 1D quantile lines
quantile_line_color = "orange"              # Color for 16th/84th percentiles
quantile_line_style = "dashed"              # Line style for quantiles
center_quantile_color = "darkgreen"         # Color for median (50th percentile)
center_quantile_style = "dashdot"           # Line style for median
best_point_method = "mean"                  # "mean", "median", or "none"
best_point_color = "darkgreen"              # Color for best-fit marker
best_point_size = 40                        # Size of best-fit marker
```

#### Best-Fit Point

The best-fit point can be computed as:
- `"mean"`: Average of all chain samples
- `"median"`: Median of all chain samples
- `"none"`: No best-fit point displayed

### Example Workflow

```bash
# 1. Generate and run lenstool on samples to create bayes.dat
python -c "from lenstool_tools import generate_sample_input_files; \
  generate_sample_input_files('tests/bayes.dat', 'tests/input.par')"

# 2. Create corner plot from Bayesian chain
python single_model/corner/lenstool_corner.py tests/bayes.dat output/corner_plot.pdf

# 3. View the publication-quality PDF
open output/corner_plot.pdf
```

### Output

The corner plot is saved as a high-resolution PDF (300 dpi) with:
- Parameters on diagonal (1D distributions)
- 2D correlation plots on lower triangle
- Contours at specified confidence levels
- Best-fit point marked with crosshairs
- Automatic axis labels and titles

### Requirements

The corner plot module requires:
- `matplotlib` (for plotting)
- `numpy` (for numerical operations)
- `corner` (for corner plot generation)

Install with: `pip install matplotlib numpy corner`
