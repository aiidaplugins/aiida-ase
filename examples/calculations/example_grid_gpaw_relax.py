# -*- coding: utf-8 -*-
from aiida import engine, orm
from aiida.orm import load_code
from ase.build import bulk


def runner():

    AseCalculation = CalculationFactory('ase.ase')
    builder = AseCalculation.get_builder()

    code = load_code('gpaw.21.6.0@localhost')
    builder.code = code

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
            'gpts': {
                '@function': 'h2gpts',
                'args': {'h': 0.18, 'cell_cv': cell, }},
            'convergence': {'energy': 1e-9},
            'occupations': {
                'name': 'fermi-dirac',
                'width':0.05}
            },
        },
    'optimizer':{
        'name': 'BFGS',
        'maxiter': 50,
        },
    'extra_imports': [['gpaw.utilities', 'h2gpts'],],
    }


    builder.parameters = orm.Dict(parameters)

    # Running the calculation using gpaw python
    settings = {'CMDLINE': ['python']}
    builder.settings = orm.Dict(settings)

    builder.metadata.options.resources = {'num_machines': 1}
    builder.metadata.options.max_wallclock_seconds = 1 * 30 * 60
    builder.metadata.options.parser_name = 'ase.gpaw'


    engine.run(builder)


if __name__ == '__main__':
    runner()
