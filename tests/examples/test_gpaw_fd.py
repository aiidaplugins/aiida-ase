###########################################################################
## A simple test script for AiiDA-ase with a set of simple set of         #
## parameters including QuasiNewton and PW operation mode with GPAW       #
###########################################################################

import sys
import os
from aiida import orm, engine

def main():

    ## Use the CalculationFactory for ASE
    ASECalculation = CalculationFactory('ase.ase')
    ## get the builder
    builder = ASECalculation.get_builder()

    ### Add in the code
    code = load_code('gpaw-ase@dtu_xeon8') ## Change the right code
    builder.code = code

    ### BaTiO3 cubic structure
    alat = 4. # angstrom
    cell = [[alat, 0., 0.,],
            [0., alat, 0.,],
            [0., 0., alat,],
            ]
    StructureData = DataFactory('structure')
    s = StructureData(cell=cell)
    s.append_atom(position=(0.,0.,0.),symbols=['Ba'])
    s.append_atom(position=(alat/2.,alat/2.,alat/2.),symbols=['Ti'])
    s.append_atom(position=(alat/2.,alat/2.,0.),symbols=['O'])
    s.append_atom(position=(alat/2.,0.,alat/2.),symbols=['O'])
    s.append_atom(position=(0.,alat/2.,alat/2.),symbols=['O'])
    builder.structure = s

    ### Kpoints for the 
    KpointsData = DataFactory('array.kpoints')
    kpoints = KpointsData()
    kpoints.set_kpoints_mesh([2,2,2])
    builder.kpoints = kpoints

    ### setup the parameters
    parameters = {
                    "calculator": {\
                                 "name":"gpaw",
                                 "args":{\
                                    "mode":"fd",
                                    "gpts": {"@function":'h2gpts',\
                                             "args":{\
                                                 "h":0.18,
                                                 "cell_cv":cell,
                                                 },
                                            },
                                    "convergence":{'energy':1e-9},
                                    "occupations":{'name':'fermi-dirac', 'width':0.05},
                                        },
                                  },
              'atoms_getters':["temperature",
                               ["forces",{'apply_constraint':True}],
                               ["masses",{}],
                               ],
              'calculator_getters':[["potential_energy",{}],
                                    "spin_polarized",
                                    ],
              'optimizer':{'name':'QuasiNewton',
                           "args": {'alpha':0.9},
                           'run_args':{"fmax":0.05}
                           },

              "pre_lines":["# This is a set",
                           "# of various pre-lines",
                           "from gpaw.utilities import h2gpts"],
            
              "post_lines":["# This is a set",
                           "# of various post-lines"],
            
              "extra_imports":["os",
                               ["numpy","array"],
                               ["numpy","array","ar"],
                               ],
              }
    builder.parameters = orm.Dict(dict=parameters)
    settings = {"CMDLINE":"python"}
    builder.settings = orm.Dict(dict=settings)

    ### setup the labels and other book-keeping things
    # builder.label = 'Test calculation for GPAW'
    # builder.description = 'BaTiO3 ASE test calculation witH GPAW as a calculator'
    builder.metadata.options.resources = {'num_machines':1}
    builder.metadata.options.max_wallclock_seconds = 60 * 60
    builder.metadata.options.withmpi = True
    # builder.metadata.dry_run = True
    # builder.metadata.store_provenance = False

    engine.submit(ASECalculation, **builder)
    # engine.run(ASECalculation, **builder)



if __name__ == '__main__':
    main()