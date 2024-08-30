# -*- coding: utf-8 -*-
"""
Example script of how to perform a geometry optimization with the python INQ 
interface on crystalline silicon using AiiDA. 
"""
from aiida import engine, orm
from aiida.orm import load_code
from aiida.plugins import DataFactory, CalculationFactory
from ase.build import bulk

# Change the following value to the ``Code`` that you have configured
CODE_NAME = 'pinq@localhost'

Dict = DataFactory('core.dict')
StructureData = DataFactory('core.structure')
KpointsData = DataFactory('core.array.kpoints')
AseCalculation = CalculationFactory('ase.ase')


def main():
    # generate an example structure
    atoms = bulk('Si', 'diamond', a=5.4)
    structure = StructureData(ase=atoms)

    # k-point information
    kpoints = KpointsData()
    kpoints.set_kpoints_mesh([1,1,1])

    parameters = {
        'calculator': {
            'name': 'inq',
            'args': {
                'ecut': 300,
                'convergence': {'energy': 1e-9},
                'occupations': {
                    'name': 'fermi-dirac',
                    'width': 0.05
                }
            }
        },
        'optimizer':{
            'name': 'BFGS',
            'run_args': {
                'fmax': 0.02,
                'steps': 50
            }
        }
    }


    builder = AseCalculation.get_builder()
    builder.code = load_code(CODE_NAME)
    builder.structure = structure
    builder.kpoints = kpoints
    builder.parameters = orm.Dict(parameters)
    builder.metadata.options.resources = {'tot_num_mpiprocs': 4}
    builder.metadata.options.max_wallclock_seconds = 30 * 60  # 30 minutes
    builder.metadata.options.withmpi = True

    node = engine.submit(builder)
    print(f'AseCalculation<{node.pk}> submitted to the daemon.')


if __name__ == '__main__':
    main()
