# SPYC
*pronounced 'spicy'*

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![build](https://github.com/fanoway/spyc/actions/workflows/build.yaml/badge.svg?branch=main)](https://github.com/fanoway/spyc/actions/workflows/build.yaml)
[![codecov](https://codecov.io/gh/fanoway/spyc/branch/main/graph/badge.svg?token=RMHSZXZSLK)](https://codecov.io/gh/fanoway/spyc)

Simple tool to help plot SPC data for production purposes

Supports comparison of measurment data between locations (could also be hijacked to compare production equipment within a single location)

Interactive plots are outputted in ther browser using plotly and dash

## Installation
pipx is the recommened tool for installation as it will install in a virtual enviroment

'''
python3 -m pip install --user pipx
python3 -m pipx ensurepath
'''

spyc can then be installed from  pypi


'''
pipx install spyc
'''

## Usage

spyc can be ran as follows to display the help

'''
spyc
''''

