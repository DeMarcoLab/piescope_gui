from setuptools import setup

requirements = [
    # TODO: put your package requirements here
]

test_requirements = [
    'pytest',
    'pytest-cov',
    'pytest-faulthandler',
    'pytest-mock',
    'pytest-qt',
    'pytest-xvfb',
]

setup(
    name='piescope_gui',
    version='0.0.1-dev',
    description="A PyQt5 GUI application",
    author="DeMarco Lab",
    url='https://github.com/DeMarcoLab/piescope_gui',
    packages=['piescope_gui', 'piescope_gui.images',
              'piescope_gui.tests'],
    package_data={'piescope_gui.images': ['*.png']},
    entry_points={
        'console_scripts': [
            'Template=piescope_gui.main:main'
        ]
    },
    install_requires=requirements,
    zip_safe=False,
    keywords='piescope_gui',
    classifiers=[
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
