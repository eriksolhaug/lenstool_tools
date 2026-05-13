# lenstool_tools

A toolkit for generating and analyzing gravitational lens samples using lenstool.

## Quick Start

All commands below assume you're working within a model directory (e.g., `dec19a_model_solhaug/`).

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

**Fix**: Core radius parameters are set to `0.000001` instead of `0.0` (when core radius is set to `0.0`, i.e. turning a PIEMD model into a SIE) to prevent NaN values in potential map calculations.

## Installation

```bash
pip install -e .
```
