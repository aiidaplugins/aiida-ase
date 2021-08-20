ASE
+++

Description
-----------
Use the plugin to support inputs of ASE structure optimizations and of total energy calculations.
Requires the installation of ASE on the computer where AiiDA is running.

Supported codes
---------------
Tested on ASE v3.8.1 and on GPAW v0.10.0.
ASE back compatibility is not guaranteed.
Calculators different from GPAW should work, if they follow the interface description of ASE calculators, but have not been tested.
Usage requires the installation of both ASE and of the software used by the calculator.

Inputs
------

* ``structure`` <:py:class:`StructureData <aiida.orm.nodes.data.structure.StructureData>`>

* ``parameters`` <:py:class:`Dict <aiida.orm.nodes.data.dict.Dict>`>
  Input parameters that defines the calculations to be performed, and their parameters.
  See the ASE documentation for more details.

* ``kpoints`` <:py:class:`KpointsData <aiida.orm.nodes.data.array.kpoints.KpointsData>`> (optional)
  Reciprocal space points on which to build the wavefunctions.
  Only kpoints meshes are currently supported.

* ``settings`` <:py:class:`Dict <aiida.orm.nodes.data.dict.Dict>`> (optional)
  An optional dictionary that activates non-default operations.
  Possible values are:

    *  **'CMDLINE'**: list of strings. parameters to be put after the executable and before the input file.
       Example: ["-npool","4"] will produce `gpaw -npool 4 < aiida_input`
    *  **'ADDITIONAL_RETRIEVE_LIST'**: list of strings.
       Specify additional files to be retrieved.
       By default, the output file and the xml file are already retrieved.

Outputs
-------
Actual output production depends on the input provided.

* ``output_parameters`` <:py:class:`Dict <aiida.orm.nodes.data.dict.Dict>`> (accessed by ``calculation.res``)
  Contains the scalar properties.
  Example: energy (in eV) or warnings (possible error messages generated in the run).
* ``output_array`` <:py:class:`ArrayData <aiida.orm.nodes.data.array.ArrayData>`>
  Stores vectorial quantities (lists, tuples, arrays), if requested in output.
  Example: forces, stresses, positions.
  Units are those produced by the calculator.
* ``output_structure`` <:py:class:`StructureData <aiida.orm.nodes.data.structure.StructureData>`>
  Present only if the structure is optimized.

Errors
------
Errors of the parsing are reported in the log of the calculation (accessible with the ``verdi process report`` command).
Moreover, they are stored in the Dict under the key ``warnings``, and are accessible with ``verdi calcjob res -k warnings``.

Examples
--------
The following example briefly describe the usage of GPAW within AiiDA, assuming that both ASE and GPAW have been installed on the remote machine.
Note that ASE calculators, at times, require the definition of environment variables.
Take your time to find them and make sure that they are loaded by the submission script of AiiDA (use the prepend text fields of a Code, for example).

First of all install the AiiDA Code as usual, noting that, if you plan to use the serial version of GPAW (applies to all other calculators) the remote absolute path of the code has to point to the python executable (i.e. the output of ``which python`` on the remote machine, typically it might be ``/usr/bin/python``).
If the parallel version of GPAW is used, set instead the path to gpaw-python.

To understand the plugin, it is probably easier to try to run a test calculation.
You can then inspect the Python script that the plugin will create on the remote machine.
Download any of the following example scripts:

* :download:`Plane-wave SCF calculation <../examples/example_pw_gpaw_scf.py>`
* :download:`Plane-wave geometry optimization calculation <../examples/example_pw_gpaw_relax.py>`

Before running the script, make sure you update the ``CODE_NAME`` variable in it to correspond to the GPAW code you have configured in AiiDA.
Then you can run the script using ``verdi run script.py``.
If successful, it will print the pk of the calculation that is submitted to the daemon.
To see the input script that is produced by the plugin, run ``verdi calcjob inputcat <PK>``.
