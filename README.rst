===============================
fibsem_gui
===============================

A PyQt5 GUI application

Development installation
------------------------

Fork the repository at: https://github.com/DeMarcoLab/piescope_gui.git

Then install with:

.. code-block::

   git clone https://github.com/$YOUR_GITHUB_USERNAME/piescope_gui.git
   cd piescope_gui
   conda env create -f environment.yml
   conda activate piescope_gui
   pip install -e .

To launch the GUI:

.. code-block::

   python piescope_gui\main.py


Running the tests
-----------------

Pytest is used for this project. To run the tests:

.. code-block::

   cd piescope_gui
   pytest


To generate new test image baselines with the pytest-mpl plugin, run:

.. code-block::

   pytest --mpl-generate-path=piescope_gui/tests/baseline


Features
--------

* TODO

Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

