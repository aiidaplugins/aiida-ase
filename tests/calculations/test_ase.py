# -*- coding: utf-8 -*-
# pylint: disable=unused-argument
"""Tests for the `AseCalculation` class."""
from __future__ import absolute_import

from aiida import orm
from aiida.common import datastructures
from aiida.plugins import CalculationFactory

AseCalculation = CalculationFactory('ase.ase')


def test_ase_default(aiida_profile, aiida_localhost, fixture_sandbox_folder, generate_calc_job,
    aiida_local_code_factory, generate_structure, generate_kpoints_mesh, generate_upf_data):
    """Test a default `AseCalculation`."""
    entry_point_name = 'ase.ase'

    parameters = {
    "calculator": {"name":"gpaw",
                         "args":{"mode":{"@function":"PW",
                                         "args":{"ecut":300}
                         }}},
          'atoms_getters':["temperature",
                           ["forces",{'apply_constraint':True}],
                           ["masses",{}],
                           ],
          'calculator_getters':[["potential_energy",{}],
                                "spin_polarized",
                                ["stress",['atoms']],
                                #["orbital_dos",['atoms', {'spin':0}] ],
                                ],
          'optimizer':{'name':'QuasiNewton',
                       "args": {'alpha':0.9},
                       'run_args':{"fmax":0.05}
                       },

          "pre_lines":["# This is a set",
                       "# of various pre-lines"],

          "post_lines":["# This is a set",
                       "# of various post-lines"],

          "extra_imports":["os",
                           ["numpy","array"],
                           ["numpy","array","ar"],
                           ],
          }

    options = {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        }
    }

    inputs = {
        'code': aiida_local_code_factory(entry_point_name, aiida_localhost),
        'structure': generate_structure('Si'),
        'kpoints': generate_kpoints_mesh(2),
        'parameters': orm.Dict(dict=parameters),
        'metadata': {'options': options}
    }

    calc_info = generate_calc_job(fixture_sandbox_folder, entry_point_name, inputs)

    cmdline_params = ['aiida_script.py']
    local_copy_list = []
    retrieve_list = [AseCalculation._output_aseatoms, AseCalculation._OUTPUT_FILE_NAME]

    # Check the attributes of the returned `CalcInfo`
    assert isinstance(calc_info, datastructures.CalcInfo)
    assert sorted(calc_info.codes_info[0].cmdline_params) == sorted(cmdline_params)
    assert sorted(calc_info.local_copy_list) == sorted(local_copy_list)
    assert sorted(calc_info.retrieve_list) == sorted(retrieve_list)

    # Checks on the files written to the sandbox folder as raw input
    assert sorted(fixture_sandbox_folder.get_content_list()) == sorted([AseCalculation._INPUT_FILE_NAME, AseCalculation._input_aseatoms])

    with fixture_sandbox_folder.open(AseCalculation._INPUT_FILE_NAME) as handle:
        file_input = handle.read()

    with fixture_sandbox_folder.open(AseCalculation._input_aseatoms) as handle:
        file_atoms = handle.read()

    # file_regression.check(file_input, encoding='utf-8', extension='.in')
    # file_regression.check(file_atoms, encoding='utf-8', extension='.traj')
