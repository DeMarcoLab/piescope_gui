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
    name='fibsem_gui',
    version='0.0.1-dev',
    description="A PyQt5 GUI application",
    author="DeMarco Lab",
    url='https://github.com/DeMarcoLab/fibsem_gui',
    packages=['fibsem_gui', 'fibsem_gui.images',
              'fibsem_gui.tests'],
    package_data={'fibsem_gui.images': ['*.png']},
    entry_points={
        'console_scripts': [
            'Template=fibsem_gui.main:main'
        ]
    },
    install_requires=requirements,
    zip_safe=False,
    keywords='fibsem_gui',
    classifiers=[
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
