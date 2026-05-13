from setuptools import setup, find_packages

setup(
    name='lenstool_tools',
    version='0.1.0',
    description='Tools for analyzing lenstool gravitational lensing simulations',
    author='Erik Solhaug',
    packages=find_packages(),
    python_requires='>=3.6',
    install_requires=[
    ],
    entry_points={
        'console_scripts': [
            'lenstool-samples=lenstool_tools.samples:main',
            'lenstool-generate-samples=lenstool_tools.generate_samples:main',
            'lenstool-run-samples=lenstool_tools.run_samples:main',
            'extract-magnifications=lenstool_tools.extract_magnifications:main',
            'magnification-statistics=lenstool_tools.magnification_statistics:main',
        ],
    },
)
