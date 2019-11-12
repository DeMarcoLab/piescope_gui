===============================
piescope_gui
===============================

.. image:: https://ci.appveyor.com/api/projects/status/bnsr1sliamycehiv/branch/master?svg=true
    :target: https://ci.appveyor.com/project/GenevieveBuckley/piescope-gui-9sta2/branch/master


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

Then download the pypylon wheel "pypylon-1.4.0-cp36-cp36m-win_amd64.whl" located at https://github.com/basler/pypylon/releases

Navigate to where this file is downloaded and then pip install using:

.. code-block::

   pip install pypylon-1.4.0-cp36-cp36m-win_amd64.whl

Finally fork Piescope repository at: https://github.com/DeMarcoLab/piescope_gui.git into a new folder 

Navigate to that folder, then: 

.. code-block::

   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   pip install -e.

To launch the GUI, navigate to your piescope_gui repository, then:

.. code-block::

   python piescope_gui\main.py


Running the tests
-----------------

Pytest is used for this project. To run the tests:

.. code-block::

   cd piescope_gui
   pytest


Features
--------

* TODO

Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
