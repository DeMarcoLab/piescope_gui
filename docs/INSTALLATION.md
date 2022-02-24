# Software Installation Guide

## Dependencies

Hardware requirements
* FIB/SEM microscope (a commercial product by ThermoFisher FEI)
* Basler detector (https://www.baslerweb.com)
* Toptica lasers (for the fluorescence microscope)
* SMARACT stage (controlling the fluorescence objective lens position)

Software requirements
* Python 3.6
* Autoscript software (a commercial product by ThermoFisher FEI)
* The Basler [Pylon Software Suite](https://www.baslerweb.com/en/products/software/basler-pylon-camera-software-suite/)
* The Basler [`pypylon` python package](https://github.com/basler/pypylon)
* The [`piescope` python package](https://github.com/DeMarcoLab/piescope/releases)
* Other python packages, as specified in the [requirements.txt](requirements.txt) and [requirements-dev.txt](requirements-dev.txt)

## Python
Python 3.6 is required.

### Installing Autoscript
Autoscript provides an API (application programming interface) for scripting
control of compatible FEI microscope systems.
This is a commercial product by Thermo Fisher FEI, please visit their website
at https://fei.com for information on pricing and installation.

We use Autoscript version 4.2.2

The version numbers of the python packages autoscript installs were:
* autoscript-core 5.1.0
* autoscript-sdb-microscope-client 4.2.2
* autoscript-sdb-microscope-client-tests 4.2.2
* autoscript-toolkit 4.2.2
* thermoscientific-logging 5.1.0

### Installing the Pylon Software Suite and pypylon python library

#### Pylon software suite
The Pylon software suite is produced by Basler for use with their detectors.
Instructions for downloading and installing the latest version of Pylon can be found on their website:
https://www.baslerweb.com/en/products/software/basler-pylon-camera-software-suite/

#### pypylon python package
Basler also provide a Python API for use with their detectors and the Pylon software suite.
Instructions for downloading and installing the latest version can be found at:
https://github.com/basler/pypylon

## Install the `piescope` back-end library
Download the latest `piescope` release wheel from
https://github.com/DeMarcoLab/piescope/releases

Pip install the wheel file (`.whl`) into your python environment.
```
pip install $PIESCOPE_WHEEL_FILENAME.whl
```

## Install `piescope_gui`
Download the latest release of the `piescope_gui` source code from
https://github.com/DeMarcoLab/piescope_gui/releases

Unzip and then pip install `piescope_gui`:

```
cd piescope_gui
conda activate piescope_gui
pip install .
```

## Python package dependencies
All the python package dependencies you need should be installed automatically,
with the exceptions:
 1. Autoscript which is a commercial product and requires a special license key.
 2. The Basler `pypylon` python pacakge, made freely available at
 https://github.com/basler/pypylon
 3. The `piescope` back-end library, made freely availble at
 https://github.com/DeMarcoLab/piescope/releases

If you do encounter an issue with missing package dependencies,
you can always try reinstalling them with:
```
pip install -r requirements.txt
```

## Having problems?
* Check to see if Autoscript is correctly installed and configured.
* Check to see if your python environment contains all packages listed in
the requirements.txt
* Check that when you call python from the terminal, you get the python
environment containing the dependencies listed above
(i.e. you are not using a different python environment)
* Try cloning the repository and running the unit tests,
you may want to try installing from the source code.
