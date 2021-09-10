# -*- coding: utf-8 -*-
"""Example script of how to perform a relax GPAW calculation on crystalline silicon using AiiDA."""
from aiida import common
from aiida import engine
from aiida import orm
from aiida import plugins
from ase.build import bulk

# Change the following value to the ``Code`` that you have configured
CODE_NAME = 'gpaw-21.6.0@localhost'

Dict = plugins.DataFactory('dict')
StructureData = plugins.DataFactory('structure')
KpointsData = plugins.DataFactory('array.kpoints')
AseCalculation = plugins.CalculationFactory('ase.ase')


def main():
    # generate an example structure
    atoms = bulk('Si', 'diamond', a=5.4)
    StructureData = DataFactory('structure')
    structure = StructureData(ase=atoms)

    # k-point information
    KpointsData = DataFactory('array.kpoints')
    kpoints = KpointsData()
    kpoints.set_kpoints_mesh([1,1,1])

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
    builder.parameters = orm.Dict(dict=parameters)
    builder.settings = orm.Dict(dict=settings)
    builder.metadata.options.resources = {'num_machines': 1}
    builder.metadata.options.max_wallclock_seconds = 30 * 60  # 30 minutes
    builder.metadata.options.withmpi = False

    node = engine.submit(builder)
    print(f'AseCalculation<{node.pk}> submitted to the daemon.')


if __name__ == '__main__':
    main()
