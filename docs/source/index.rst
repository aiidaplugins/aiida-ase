#######################
`AiiDA`_ plugin for ASE
#######################

.. figure:: images/AiiDA_transparent_logo.png
    :width: 250px
    :align: center
    :height: 100px

.. _AiiDA: http://www.aiida.net

Description
===========

The plugin is available at http://github.com/aiidateam/aiida-ase

`ASE`_ (Atomic Simulation Environment) is a set of tools and Python modules for
setting up, manipulating, running, visualizing and analyzing atomistic
simulations. The ASE code is freely available under the GNU LGPL license (the
ASE installation guide and the source can be found `here`_).

Besides the manipulation of structures (``Atoms`` objects), one can attach
``calculators`` to a structure and run it to compute, as an example, energies or
forces.
Multiple calculators are currently supported by ASE, like GPAW, Vasp, Abinit and
many others.

In AiiDA, we have developed a plugin which currently supports the use of ASE
calculators for total energy calculations and structure optimizations.

.. _here: http://wiki.fysik.dtu.dk/ase/
.. _ASE: http://wiki.fysik.dtu.dk/ase/


If you use AiiDA or this plugin for your research, please cite the following work:

.. highlights:: Giovanni Pizzi, Andrea Cepellotti, Riccardo Sabatini, Nicola Marzari,
  and Boris Kozinsky, *AiiDA: automated interactive infrastructure and database
  for computational science*, Comp. Mat. Sci 111, 218-230 (2016);
  https://doi.org/10.1016/j.commatsci.2015.09.013; http://www.aiida.net.

User's guide
++++++++++++

.. toctree::
   :maxdepth: 4

   user_guide/index

Modules provided with aiida-ase (API reference)
++++++++++++++++++++++++++++++++++++++++++++++++++

.. toctree::
   :maxdepth: 4

   module_guide/index

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
