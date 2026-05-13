"""
lenstool_tools: Tools for analyzing lenstool gravitational lensing simulations
"""

__version__ = "0.1.0"

from .samples import read_bayes_dat, print_parameter_summary
from .generate_samples import generate_sample_input_files
from .run_samples import run_lenstool_on_samples
from .extract_magnifications import extract_magnifications, load_magnification_config, sample_mu
from .magnification_statistics import generate_statistics_and_histograms

__all__ = [
    'read_bayes_dat',
    'print_parameter_summary',
    'generate_sample_input_files',
    'run_lenstool_on_samples',
    'extract_magnifications',
    'load_magnification_config',
    'sample_mu',
    'generate_statistics_and_histograms'
]
