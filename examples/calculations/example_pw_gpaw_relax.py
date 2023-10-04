# -*- coding: utf-8 -*-
"""Example script of how to perform a relax GPAW calculation on crystalline silicon using AiiDA."""
from aiida import common, engine, orm, plugins
from ase.build import bulk

# Change the following value to the ``Code`` that you have configured
CODE_NAME = 'gpaw-21.6.0@localhost'

Dict = plugins.DataFactory('core.dict')
StructureData = plugins.DataFactory('core.structure')
KpointsData = plugins.DataFactory('core.array.kpoints')
AseCalculation = plugins.CalculationFactory('ase.ase')


def main():
    alat = 4.  # angstrom
    cell = [
        [
            alat,
            0.,
            0.,
        ],
        [
            0.,
            alat,
            0.,
        ],
        [
            0.,
            0.,
            alat,
        ],
    ]

    # BaTiO3 cubic structure
    StructureData = DataFactory('core.structure')
    structure = StructureData(cell=cell)
    structure.append_atom(position=(0., 0., 0.), symbols=['Ba'])
    structure.append_atom(position=(alat / 2., alat / 2., alat / 2.), symbols=['Ti'])
    structure.append_atom(position=(alat / 2., alat / 2., 0.), symbols=['O'])
    structure.append_atom(position=(alat / 2., 0., alat / 2.), symbols=['O'])
    structure.append_atom(position=(0., alat / 2., alat / 2.), symbols=['O'])

    builder.structure = structure

    # k-point information
    KpointsData = DataFactory('core.array.kpoints')
    kpoints = KpointsData()
    kpoints.set_kpoints_mesh([2,2,2])
    builder.kpoints = kpoints

    parameters = {
        'calculator': {
            'name': 'gpaw',
            'args': {
                'mode': {
                    '@function': 'PW',
                    'args': {
                        'ecut': 300
                    }
                },
                'convergence': {'energy': 1e-9},
                'occupations': {
                    'name': 'fermi-dirac',
                    'width': 0.05
                }
            }
        },
        'optimizer':{
            'name': 'BFGS',
            'maxiter': 50,
        }
    }

    # Running the calculation using GPAW Python
    settings = {'CMDLINE': ['python']}

    builder = AseCalculation.get_builder()
    builder.code = load_code(CODE_NAME)
    builder.structure = structure
    builder.kpoints = kpoints
    builder.parameters = orm.Dict(parameters)
    builder.settings = orm.Dict(settings)
    builder.metadata.options.resources = {'num_machines': 1}
    builder.metadata.options.max_wallclock_seconds = 30 * 60  # 30 minutes
    builder.metadata.options.withmpi = False
    builder.metadata.options.parser_name = 'ase.gpaw'

    node = engine.submit(builder)
    print(f'AseCalculation<{node.pk}> submitted to the daemon.')


if __name__ == '__main__':
    main()
