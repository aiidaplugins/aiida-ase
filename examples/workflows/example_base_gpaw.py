# -*- coding: utf-8 -*-


from aiida.orm import load_code
from ase.build import bulk
from aiida import orm, engine

def runner():

    BaseGPAW = WorkflowFactory('ase.gpaw.base')
    builder = BaseGPAW.get_builder()

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
    StructureData = DataFactory('structure')
    structure = StructureData(cell=cell)
    structure.append_atom(position=(0., 0., 0.), symbols=['Ba'])
    structure.append_atom(position=(alat / 2., alat / 2., alat / 2.), symbols=['Ti'])
    structure.append_atom(position=(alat / 2., alat / 2., 0.), symbols=['O'])
    structure.append_atom(position=(alat / 2., 0., alat / 2.), symbols=['O'])
    structure.append_atom(position=(0., alat / 2., alat / 2.), symbols=['O'])
    builder.structure = structure

    code = load_code('gpaw.21.6.0@localhost')
    builder.gpaw.code = code

    # k-point information
    KpointsData = DataFactory('array.kpoints')
    kpoints = KpointsData()
    kpoints.set_kpoints_mesh([2,2,2])
    builder.gpaw.kpoints = kpoints

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
    'optimizer':{
        'name': 'BFGS',
        'maxiter': 50,
        },
    }

    builder.gpaw.parameters = orm.Dict(dict=parameters)

    # Running the calculation using gpaw python
    settings = {'CMDLINE': ['python']}
    builder.gpaw.settings = orm.Dict(dict=settings)

    builder.gpaw.metadata.options.resources = {'num_machines': 1}
    builder.gpaw.metadata.options.max_wallclock_seconds = 1 * 30 * 60

    engine.run(BaseGPAW, **builder)


if __name__ == '__main__':
    runner()
