# -*- coding: utf-8 -*-


from aiida.orm import load_code
from ase.build import bulk
from aiida import orm, engine

def runner():

    AseCalculation = CalculationFactory('ase.ase')
    builder = AseCalculation.get_builder()

    code = load_code('gpaw-21.6.0@localhost')
    builder.code = code

    # generate an example structure
    atoms = bulk('Si', 'diamond', a=5.4)
    StructureData = DataFactory('structure')
    structure = StructureData(ase=atoms)
    builder.structure = structure

    # k-point information
    KpointsData = DataFactory('array.kpoints')
    kpoints = KpointsData()
    kpoints.set_kpoints_mesh([1,1,1])
    builder.kpoints = kpoints

    parameters = {
    'calculator': {
        'name': 'gpaw',
        'args': {
            'mode': {
                '@function': 'PW',
                'args': {'ecut': 300}},
            'convergence': {'energy': 1e-9},
            'occupations': {
                'name': 'fermi-dirac',
                'width':0.05}
            },
        },
    }

    builder.parameters = orm.Dict(dict=parameters)

    # Running the calculation using gpaw python
    settings = {'CMDLINE': ['python']}
    builder.settings = orm.Dict(dict=settings)

    builder.metadata.options.resources = {'num_machines': 1}
    builder.metadata.options.max_wallclock_seconds = 1 * 30 * 60
    builder.metadata.options.withmpi = False


    engine.submit(builder)


if __name__ == '__main__':
    runner()
