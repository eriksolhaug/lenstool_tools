# lenstool_tools

A toolkit for generating and analyzing gravitational lens samples using lenstool.

## Table of Contents

- [Installation](#installation)
- [Dependencies](#dependencies)
- [Quick Start](#quick-start)
  - [Generate samples](#generate-samples)
  - [Run samples](#run-samples)
  - [Extract magnifications](#extract-magnifications)
  - [Produce magnification statistics](#produce-magnification-statistics)
  - [Produce mass statistics](#produce-mass-statistics)
  - [Extract time delays](#extract-time-delays)
  - [Plot time delay maps](#plot-time-delay-maps)
  - [Produce time delay statistics](#produce-time-delay-statistics)
- [Notes](#notes)

## Installation

### Clone the repository

```bash
git clone https://github.com/eriksolhaug/lenstool_tools.git
cd lenstool_tools
```

### Set up the Conda environment

The code requires a Conda environment for lenstool. The environment name is specified in `lenstool_tools/.lenstool_env`:

```bash
cat lenstool_tools/.lenstool_env  # shows "lenstool_env8" (or your custom environment name)
```

Create or activate the lenstool environment (if you haven't already):

```bash
conda create -n lenstool_env8 -c conda-forge lenstool=6.5
conda activate lenstool_env8
```

### Install the package

```bash
pip install -e .
```

## Dependencies

### Lenstool

This toolkit requires **lenstool 6.5** (installed in a Conda environment). 

**Important:** Use lenstool 6.5, not 7.1.1 or later. Version 7.1.1+ may have issues with writing potential (poten) FITS files.

The environment name (`lenstool_env8` by default) is read from `lenstool_tools/.lenstool_env` and used by the `run_samples` module to execute lenstool in the correct environment.

### Python packages

Standard scientific Python packages:
- numpy
- pandas
- astropy (for FITS I/O)
- matplotlib

## Quick Start

All commands below assume you're working within a model directory (e.g., `example/`). Any CAPITALIZED names are for you to change (unless you use the provided sample files).

### Generate samples

```bash
python -m lenstool_tools.generate_samples input/BAYES.DAT input/BESTOPT.PAR -runmode config/SAMPLE_GENERATION.json -bestopt input/BESTOPT.PAR -zlens 0.4301 -zsource 1.524 -output .
```

Example:
```bash
python -m lenstool_tools.generate_samples input/bayes.dat input/bestopt.par -runmode config/sample_generation.json -bestopt input/bestopt.par -zlens 0.4301 -zsource 1.524 -output .
```

### Run samples

Run all:
```bash
python -m lenstool_tools.run_samples sample_input output -workdir . -config config/RUN_SAMPLES_CONFIG.json
```

Example:
```bash
python -m lenstool_tools.run_samples sample_input output -workdir . -config config/run_samples_config.json
```

Run just the files belonging to a specified redshift:
```bash
python -m lenstool_tools.run_samples sample_input output -workdir . -redshift 1.939 -config config/RUN_SAMPLES_CONFIG.json
```

Example:
```bash
python -m lenstool_tools.run_samples sample_input output -workdir . -redshift 1.939 -config config/run_samples_config.json
```

### Extract magnifications

```bash
python -m lenstool_tools.extract_magnifications config/MAGNIFICATION_CONFIG.json MAGNIFICATIONS.csv
```

Example:
```bash
python -m lenstool_tools.extract_magnifications config/magnification1.524_config.json magnifications1.524.csv
```

### Produce magnification statistics

```bash
python -m lenstool_tools.magnification_statistics MAGNIFICATIONS.csv -redshift 1.524 -sigma 1.0 -ampli output/ampli -config config/MAGNIFICATION_CONFIG.json
```

Example:
```bash
python -m lenstool_tools.magnification_statistics magnifications1.524.csv -redshift 1.524 -sigma 1.0 -ampli output/ampli -config config/magnification1.524_config.json
```

### Produce mass statistics

```bash
python -m lenstool_tools.mass_statistics output/mass config/MASS_CONFIG.json -redshift 0.4301 -sigma 1.0
```

Example:
```bash
python -m lenstool_tools.mass_statistics output/mass config/mass_config.json -redshift 0.4301 -sigma 1.0
```

### Extract time delays

```bash
python -m lenstool_tools.extract_timedelays output/poten config/TIMEDELAYS_CONFIG.json -output output/timedelay -z 1.524
```

Example:
```bash
python -m lenstool_tools.extract_timedelays output/poten config/timedelays_z1.524.json -output output/timedelay -z 1.524
```

### Plot time delay maps

```bash
python -m lenstool_tools.plot_sample_timedelays output/timedelay config/TIMEDELAYS_CONFIG.json -output statistics/timedelay/timedelay_maps -z 1.524
```

Example:
```bash
python -m lenstool_tools.plot_sample_timedelays output/timedelay config/timedelays_z1.524.json -output statistics/timedelay/timedelay_maps -z 1.524
```

### Produce time delay statistics

```bash
python -m lenstool_tools.timedelay_statistics output/timedelay config/TIMEDELAYS_CONFIG.json -output statistics/timedelay -z 1.524
```

Example:
```bash
python -m lenstool_tools.timedelay_statistics output/timedelay config/timedelays_z1.524.json -output statistics/timedelay -z 1.524
```

## Notes

- Replace capitalized names (e.g., `BAYES.DAT`, `BESTOPT.PAR`) with your actual file names
- All commands assume your model directory contains `input/`, `config/`, and `output/` subdirectories
- Configuration files (`.json`) should be placed in the `config/` directory
- When running commands, activate the lenstool environment first: `conda activate lenstool_env8` (or the name in `lenstool_tools/.lenstool_env`)

**Fix**: Core radius parameters are set to `0.000001` instead of `0.0` (when core radius is set to `0.0`, i.e. turning a PIEMD model into a SIE) to prevent NaN values in potential map calculations.
