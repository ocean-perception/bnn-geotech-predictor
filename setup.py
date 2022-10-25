# -*- coding: utf-8 -*-

# setup.py to manage installation of the package and its dependencies
# package name: bayesian_predictor
# package source folder: src/
# dependencies: numpy, scipy, torch, pandas, scikit-learn, blitz

import os
import sys
from importlib_metadata import entry_points
from setuptools import setup, find_packages

# TODO: Complete git hook to retrieve version from git tags
# get the version number from the version file
# with open(os.path.join('src', 'version.py')) as f:
#     exec(f.read())

def run_setup():
        
    # get the long description from the README file
    # TODO: Merge with short/specific decription provided during setup() call
    with open('README.md') as f:
        long_description = f.read()
    if long_description is None:
        long_description = 'No description available'

    # the requirements can be retrieved from the conda environment file
    # with open('environment.yml') as f:
    #     requirements = f.read().splitlines()

    setup(
        name='bayesian_predictor',
        version='0.1.4',
        description='Bayesian NN training/inference engine to learn mappings between latent representations of low resolution maps and high resolution maps',
        author='Jose Cappelletto',
        author_email='j.cappelletto@soton.ac.uk',
        url='https://github.com/cappelletto/bayesian_inference',
        license='GPLv3',

        packages=['bnn_inference'],

        entry_points={
            'console_scripts': [
                'bnn_train = bnn_inference.bnn_train:main',
                'bnn_predict = bnn_inference.bnn_predict:main',
            ],
        },

        install_requires = [
            "blitz-bayesian-pytorch==0.2.7",
            "numpy==1.19.0",
            "pandas==0.25.3",
            "torch==1.7.0",
            "torchvision==0.8.1",
            "scikit-learn==0.23.1",
            "scipy==1.5.0",
        ]
)

if __name__ == "__main__":
    run_setup()