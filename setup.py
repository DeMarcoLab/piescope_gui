from setuptools import setup, find_packages

from piescope_gui._version import __version__


def parse_requirements_file(filename):
    with open(filename) as fid:
        requires = [l.strip() for l in fid.readlines() if l]

    return requires


INST_DEPENDENCIES = parse_requirements_file("requirements.txt")

setup(
    name='piescope_gui',
    version=__version__,
    description="A PyQt5 GUI application",
    author="David Dierickx (DeMarco Lab)",
    author_email="David.Dierickx1@monash.edu",
    url='https://github.com/DeMarcoLab/piescope_gui',
    packages=find_packages(),
    package_data={'piescope_gui.images': ['*.png']},
    entry_points={
        'console_scripts': [
            'piescope=piescope_gui.main:main'
        ]
    },
    install_requires=INST_DEPENDENCIES,
    zip_safe=False,
    classifiers=[
        'Programming Language :: Python :: 3.7',
    ]
)
