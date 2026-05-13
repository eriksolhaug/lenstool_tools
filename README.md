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

### Set up the Python environment for lenstool_tools

Create a Python environment to run the lenstool_tools code:

```bash
conda create -n lenstool_tools python=3.9
conda activate lenstool_tools
```

### Install the package

```bash
pip install -e .
```

This installs the lenstool_tools package and its Python dependencies.

### Set up the Conda environment for lenstool (the binary)

The code requires a **separate** Conda environment for running lenstool itself. The environment name is specified in `lenstool_tools/.lenstool_env`:

```bash
cat lenstool_tools/.lenstool_env  # shows "lenstool_env8"
```

Create the lenstool environment:

```bash
conda create -n lenstool_env8
# Then download lenstool in this environment
```

If you want to use a different environment name, edit `lenstool_tools/.lenstool_env`:

```bash
echo "your_custom_env_name" > lenstool_tools/.lenstool_env
```

## Dependencies

### Two Conda environments

This toolkit requires **two separate Conda environments**:

1. **Python environment (e.g., `lenstool_tools`)**: For running the lenstool_tools Python code. You activate this to run the commands listed in Quick Start.

2. **Lenstool environment (e.g., `lenstool_env8`)**: For running the lenstool binary. This is specified in `lenstool_tools/.lenstool_env`. The Python code automatically activates this environment when needed using `conda run`; you don't need to manually activate it.

The lenstool binary must be installed in the environment specified in `lenstool_tools/.lenstool_env`. I recommend using lenstool v8.


## Quick Start

All commands below assume you're working within a model directory (e.g., `example/`). Any CAPITALIZED names are for you to change (unless you use the provided sample files).

**Prerequisite:** Activate the lenstool_tools Python environment:
```bash
conda activate lenstool_tools
```

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

Please change any parameters in the configuration files.

```bash
python -m lenstool_tools.extract_magnifications config/MAGNIFICATION_CONFIG.json MAGNIFICATIONS.csv
```

Example:
```bash
python -m lenstool_tools.extract_magnifications config/magnification1.524_config.json magnifications1.524.csv
```

### Produce magnification statistics

Replace the redshift with the redshift of your source. The magnification depends on this redshift. Set the desired uncertainty interval with the `-sigma` flag, i.e. 1 corresponds to a 1(\sigma), or rather, the 16th-84th percentile.

Also, check the configuration file and change the parameters to the parameter of your field (e.g. image coordinates must be specified here).

```bash
python -m lenstool_tools.magnification_statistics MAGNIFICATIONS.csv -redshift 1.524 -sigma 1.0 -ampli output/ampli -config config/MAGNIFICATION_CONFIG.json
```

Example:
```bash
python -m lenstool_tools.magnification_statistics magnifications1.524.csv -redshift 1.524 -sigma 1.0 -ampli output/ampli -config config/magnification1.524_config.json
```

### Produce mass statistics

Please change any parameters in the configuration files. The `-redshift` flag should be set to the redshift of the lens.

```bash
python -m lenstool_tools.mass_statistics output/mass config/MASS_CONFIG.json -redshift 0.4301 -sigma 1.0
```

Example:
```bash
python -m lenstool_tools.mass_statistics output/mass config/mass_config.json -redshift 0.4301 -sigma 1.0
```

### Extract time delays

Please change any parameters in the configuration files.

```bash
python -m lenstool_tools.extract_timedelays output/poten config/TIMEDELAYS_CONFIG.json -output output/timedelay -z 1.524
```

Example:
```bash
python -m lenstool_tools.extract_timedelays output/poten config/timedelays_z1.524.json -output output/timedelay -z 1.524
```

### Plot time delay maps

Please change any parameters in the configuration files.

```bash
python -m lenstool_tools.plot_sample_timedelays output/timedelay config/TIMEDELAYS_CONFIG.json -output statistics/timedelay/timedelay_maps -z 1.524
```

Example:
```bash
python -m lenstool_tools.plot_sample_timedelays output/timedelay config/timedelays_z1.524.json -output statistics/timedelay/timedelay_maps -z 1.524
```

### Produce time delay statistics

Please change any parameters in the configuration files.

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
- Activate the Python environment for lenstool_tools when running commands: `conda activate lenstool_tools` (or whatever you named it)
- The `lenstool_env8` environment is used automatically by the code when calling the lenstool binary; you don't need to manually activate it

**Fix**: Core radius parameters are set to `0.000001` instead of `0.0` (when core radius is set to `0.0`, i.e. turning a PIEMD model into a SIE) to prevent NaN values in potential map calculations.
