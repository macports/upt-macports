# Universal Packaging Tool: MacPorts backend
This is a [MacPorts](https://www.macports.org) backend for [upt](https://pypi.python.org/pypi/upt).

The prototype was written by Mojca Miklavec (@mojca) and further developed as part of
[Google Summer of Code 2019](https://summerofcode.withgoogle.com/archive/2019) by
Karan Sheth (@Korusuke), mentored by Cyril Roelandt (@Steap) and Renee Otten (@reneeotten).

## Installation

### Using MacPorts
Follow [the instructions](https://www.macports.org/install.php) to install MacPorts on your Mac.

Use the command below to install `upt`, the `upt-macports` backend, and all supported frontends:

> sudo port install upt

### Install from source
The source can be obtained from [PyPI](https://pypi.org/project/upt/) or [framagit](https://framagit.org/upt/upt); several
frontends are also available from these websites.

To install the MacPorts backend, first clone the repository and follow the typical installation steps:
```
git clone https://github.com/macports/upt-macports.git
cd upt-macports/
python setup.py install
```
where `python` is the Python 3 executable on your system.

**Note**: to use the recursive and/or update feature a working MacPorts installation is required (see above for instructions).
To install MacPorts using [Docker](https://www.docker.com/), please follow [these steps](https://github.com/Korusuke/MacPorts-Docker).

## Usage

For usage instructions, refer to the [upt guide](https://framagit.org/upt/upt/blob/master/README.md) or the man page (`man upt`).
