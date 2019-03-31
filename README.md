# Universal Packaging Tool: MacPorts backend
This is a [MacPorts](https://www.macports.org) backend for [upt](https://pypi.python.org/pypi/upt).

#### Steps to use this tool out:

- Install upt
- Clone this repository and run ```python3 setup.py install``` to install macports backend
- Run ```$ upt package -f pypi -b macports package_name```
- Portfile output will be printed via stdout
