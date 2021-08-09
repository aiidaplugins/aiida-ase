# -*- coding: utf-8 -*-
"""`CalcJob` implementation that can be used to wrap around the ASE calculators."""
from aiida import common
from aiida import engine
from aiida import orm
from aiida import plugins

Dict = plugins.DataFactory('dict')
StructureData = plugins.DataFactory('structure')
KpointsData = plugins.DataFactory('array.kpoints')


class AseCalculation(engine.CalcJob):
    """`CalcJob` implementation that can be used to wrap around the ASE calculators."""

    _default_parser = 'ase.ase'
    _INPUT_FILE_NAME = 'aiida_script.py'
    _OUTPUT_FILE_NAME = 'results.json'
    _TXT_OUTPUT_FILE_NAME = 'aiida.out'
    _input_aseatoms = 'aiida_atoms.json'
    _output_aseatoms = 'aiida_out_atoms.json'
    _OPTIMIZER_FILE_NAME = 'aiida_optimizer.log'

    @classmethod
    def define(cls, spec):
        # yapf: disable
        super().define(spec)
        spec.input('metadata.options.input_filename', valid_type=str, default=cls._INPUT_FILE_NAME,
            help='Filename to which the input for the code that is to be run will be written.')
        spec.input('metadata.options.output_filename', valid_type=str, default=cls._OUTPUT_FILE_NAME,
            help='Filename to which the content of stdout of the code that is to be run will be written.')
        spec.input('metadata.options.error_filename', valid_type=str, default='aiida.err',
            help='Filename to which the content of stderr of the code that is to be run will be written.')
        spec.input('metadata.options.parser_name', valid_type=str, default=cls._default_parser,
            help='Define the parser to be used by setting its entry point name.')
        spec.input('structure', valid_type=StructureData, help='The input structure.')
        spec.input('kpoints', valid_type=KpointsData, required=False, help='The k-points to use for the calculation.')
        spec.input('parameters', valid_type=Dict, help='Input parameters for the namelists.')
        spec.input('settings', valid_type=Dict, required=False, help='Optional settings that control the plugin.')
        spec.input('metadata.options.optimizer_stdout', valid_type=str, default=cls._OPTIMIZER_FILE_NAME,
            help='Optimiser filename for relaxation')

        spec.output('structure', valid_type=orm.StructureData, required=False)
        spec.output('parameters', valid_type=orm.Dict, required=False)
        spec.output('array', valid_type=orm.ArrayData, required=False)

        spec.exit_code(300, 'ERROR_OUTPUT_FILES', message='One of the expected output files was missing.')
        # yapf: enable

    def prepare_for_submission(self, folder):
        """This method is called prior to job submission with a set of calculation input nodes.

        The inputs will be validated and sanitized, after which the necessary input files will be written to disk in a
        temporary folder. A CalcInfo instance will be returned that contains lists of files that need to be copied to
        the remote machine before job submission, as well as file lists that are to be retrieved after job completion.

        :param folder: an aiida.common.folders.Folder to temporarily write files on disk
        :returns: CalcInfo instance
        """
        # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        if 'settings' in self.inputs:
            settings = self.inputs.settings.get_dict()
        else:
            settings = {}

        # default atom getter: I will always retrieve the total energy at least
        default_atoms_getters = [['total_energy', '']]

        # ================================

        # save the structure in ase format
        atoms = self.inputs.structure.get_ase()

        with folder.open(self._input_aseatoms, 'w') as handle:
            atoms.write(handle)

        # ================== prepare the arguments of functions ================

        parameters_dict = self.inputs.parameters.get_dict()

        # ==================== fix the args of the optimizer

        optimizer = parameters_dict.pop('optimizer', None)
        if optimizer is not None:
            # Validation
            if not isinstance(optimizer, dict):
                raise common.InputValidationError('optimizer key must contain a dictionary')
            # get the name of the optimizer
            optimizer_name = optimizer.pop('name', None)
            if optimizer_name is None:
                raise common.InputValidationError("Don't have access to the optimizer name")

            # prepare the arguments to be passed to the optimizer class
            optimizer_argsstr = f"atoms, logfile='{self.inputs.metadata.options.optimizer_stdout}', "\
                     + convert_the_args(optimizer.pop('args', []))

            # prepare the arguments to be passed to optimizer.run()
            optimizer_runargsstr = convert_the_args(optimizer.pop('run_args', []))

            # prepare the import string
            optimizer_import_string = get_optimizer_impstr(optimizer_name)

        # ================= determine the calculator name and its import ====

        calculator = parameters_dict.pop('calculator', {})
        calculator_import_string = get_calculator_impstr(calculator.pop('name', None))

        # =================== prepare the arguments for the calculator call

        read_calc_args = calculator.pop('args', [])
        if read_calc_args is None:
            calc_argsstr = ''
        else:
            # transform a in "a" if a is a string (needed for formatting)
            calc_args = {}
            for k, v in read_calc_args.items():
                if isinstance(v, str):
                    the_v = f'"{v}"'
                else:
                    the_v = v
                calc_args[k] = the_v

            def return_a_function(v):
                try:
                    has_magic = '@function' in v.keys()
                except AttributeError:
                    has_magic = False

                if has_magic:

                    args_dict = {}
                    for k2, v2 in v['args'].items():
                        if isinstance(v2, str):
                            the_v = f'"{v2}"'
                        else:
                            the_v = v2
                        args_dict[k2] = the_v

                    v2 = '{}({})'.format(
                        v['@function'], ', '.join(['{}={}'.format(k_, v_) for k_, v_ in args_dict.items()])
                    )
                    return v2
                return v

            tmp_list = ['{}={}'.format(k, return_a_function(v)) for k, v in calc_args.items()]

            calc_argsstr = ', '.join(tmp_list)

            # add kpoints if present
            if 'kpoints' in self.inputs:
                #TODO: here only the mesh is supported
                # maybe kpoint lists are supported as well in ASE calculators
                try:
                    mesh = self.inputs.kpoints.get_kpoints_mesh()[0]
                except AttributeError:
                    raise common.InputValidationError("Coudn't find a mesh of kpoints" ' in the KpointsData')
                calc_argsstr = ', '.join([calc_argsstr] + ['kpts=({},{},{})'.format(*mesh)])

        # =============== prepare the methods of atoms.get(), to save results

        atoms_getters = default_atoms_getters + convert_the_getters(parameters_dict.pop('atoms_getters', []))

        # =============== prepare the methods of calculator.get(), to save results

        calculator_getters = convert_the_getters(parameters_dict.pop('calculator_getters', []))

        # ===================== build the strings with the module imports

        all_imports = ['import ase', 'import ase.io', 'import json', 'import numpy', calculator_import_string]

        if optimizer is not None:
            all_imports.append(optimizer_import_string)

        try:
            if 'PW' in calc_args['mode'].values():
                all_imports.append('from gpaw import PW')
        except KeyError:
            pass

        extra_imports = parameters_dict.pop('extra_imports', [])
        for i in extra_imports:
            if isinstance(i, str):
                all_imports.append(f'import {i}')
            elif isinstance(i, (list, tuple)):
                if not all([isinstance(j, str) for j in i]):
                    raise ValueError('extra import must contain strings')
                if len(i) == 2:
                    all_imports.append('from {} import {}'.format(*i))
                elif len(i) == 3:
                    all_imports.append('from {} import {} as {}'.format(*i))
                else:
                    raise ValueError('format for extra imports not recognized')
            else:
                raise ValueError('format for extra imports not recognized')

        if self.options.withmpi:
            all_imports.append('from ase.parallel import paropen')

        all_imports_string = '\n'.join(all_imports) + '\n'

        # =================== prepare the python script ========================

        input_txt = all_imports_string
        input_txt += '\n'

        pre_lines = parameters_dict.pop('pre_lines', None)
        if pre_lines is not None:
            if not isinstance(pre_lines, (list, tuple)):
                raise ValueError('Prelines must be a list of strings')
            if not all([isinstance(_, str) for _ in pre_lines]):
                raise ValueError('Prelines must be a list of strings')
            input_txt += '\n'.join(pre_lines) + '\n\n'

        input_txt += f"atoms = ase.io.read('{self._input_aseatoms}')\n"
        input_txt += '\n'
        input_txt += f'calculator = custom_calculator({calc_argsstr})\n'
        input_txt += 'atoms.set_calculator(calculator)\n'
        input_txt += '\n'

        if optimizer is not None:
            # here block the trajectory file name: trajectory = 'aiida.traj'
            input_txt += f'optimizer = custom_optimizer({optimizer_argsstr})\n'
            input_txt += f'optimizer.run({optimizer_runargsstr})\n'
            input_txt += '\n'

        # now dump / calculate the results
        input_txt += 'results = {}\n'
        for getter, getter_args in atoms_getters:
            input_txt += f"results['{getter}'] = atoms.get_{getter}({getter_args})\n"
        input_txt += '\n'

        for getter, getter_args in calculator_getters:
            input_txt += f"results['{getter}'] = calculator.get_{getter}({getter_args})\n"
        input_txt += '\n'

        # Convert to lists
        input_txt += 'for k,v in results.items():\n'
        input_txt += '    if isinstance(results[k],(numpy.matrix,numpy.ndarray)):\n'
        input_txt += '        results[k] = results[k].tolist()\n'

        input_txt += '\n'

        post_lines = parameters_dict.pop('post_lines', None)
        if post_lines is not None:
            if not isinstance(post_lines, (list, tuple)):
                raise ValueError('Postlines must be a list of strings')
            if not all([isinstance(_, str) for _ in post_lines]):
                raise ValueError('Postlines must be a list of strings')
            input_txt += '\n'.join(post_lines) + '\n\n'

        # Dump results to file
        right_open = 'paropen' if self.options.withmpi else 'open'
        input_txt += f"with {right_open}('{self._OUTPUT_FILE_NAME}', 'w') as f:\n"
        input_txt += '    json.dump(results,f)'
        input_txt += '\n'

        # Dump trajectory if present
        if optimizer is not None:
            input_txt += f"atoms.write('{self._output_aseatoms}')\n"
            input_txt += '\n'

        # write all the input script to a file
        with folder.open(self._INPUT_FILE_NAME, 'w') as handle:
            handle.write(input_txt)

        # ============================ calcinfo ================================

        # TODO: look at the qmmm infoL: it might be necessary to put
        # some singlefiles in the directory.
        # right now it has to be taken care in the pre_lines

        local_copy_list = []
        remote_copy_list = []
        additional_retrieve_list = settings.pop('ADDITIONAL_RETRIEVE_LIST', [])

        calcinfo = common.CalcInfo()

        calcinfo.uuid = self.uuid
        # Empty command line by default
        # calcinfo.cmdline_params = settings.pop('CMDLINE', [])
        calcinfo.local_copy_list = local_copy_list
        calcinfo.remote_copy_list = remote_copy_list

        codeinfo = common.CodeInfo()
        cmdline_params = settings.pop('CMDLINE', [])
        if not isinstance(cmdline_params, (list, tuple)):
            raise common.InputValidationError('the `CMDLINE` key in the `settings` input should be a list or tuple.')
        cmdline_params.append(self._INPUT_FILE_NAME)
        codeinfo.cmdline_params = cmdline_params

        #calcinfo.stdin_name = self._INPUT_FILE_NAME
        codeinfo.stdout_name = self._TXT_OUTPUT_FILE_NAME
        codeinfo.code_uuid = self.inputs.code.uuid
        calcinfo.codes_info = [codeinfo]

        # Retrieve files
        calcinfo.retrieve_list = []
        calcinfo.retrieve_list.append(self.options.output_filename)
        calcinfo.retrieve_list.append(self._output_aseatoms)
        if optimizer is not None:
            calcinfo.retrieve_list.append(self._OPTIMIZER_FILE_NAME)

        calcinfo.retrieve_list += additional_retrieve_list

        # TODO: I should have two ways of running it: with gpaw-python in parallel
        # and executing python if in serial

        return calcinfo


def get_calculator_impstr(calculator_name):
    """
    Returns the import string for the calculator
    """
    if calculator_name is None or calculator_name.lower() == 'gpaw':
        return 'from gpaw import GPAW as custom_calculator'

    if calculator_name.lower() == 'espresso':
        return 'from espresso import espresso as custom_calculator'

    possibilities = {
        'abinit': 'abinit.Abinit',
        'aims': 'aims.Aims',
        'ase_qmmm_manyqm': 'AseQmmmManyqm',
        'castep': 'Castep',
        'dacapo': 'Dacapo',
        'dftb': 'Dftb',
        'eam': 'EAM',
        'elk': 'ELK',
        'emt': 'EMT',
        'exciting': 'Exciting',
        'fleur': 'FLEUR',
        'gaussian': 'Gaussian',
        'gromacs': 'Gromacs',
        'mopac': 'Mopac',
        'morse': 'MorsePotential',
        'nwchem': 'NWChem',
        'siesta': 'Siesta',
        'tip3p': 'TIP3P',
        'turbomole': 'Turbomole',
        'vasp': 'Vasp',
    }

    current_val = possibilities.get(calculator_name.lower())

    package, class_name = (calculator_name, current_val) if current_val else calculator_name.rsplit('.', 1)

    return f'from ase.calculators.{package} import {class_name} as custom_calculator'


def get_optimizer_impstr(optimizer_name):
    """
    Returns the import string for the optimizer
    """
    possibilities = {
        'bfgs': 'BFGS',
        'bfgslinesearch': 'BFGSLineSearch',
        'fire': 'FIRE',
        'goodoldquasinewton': 'GoodOldQuasiNewton',
        'hesslbfgs': 'HessLBFGS',
        'lbfgs': 'LBFGS',
        'lbfgslinesearch': 'LBFGSLineSearch',
        'linelbfgs': 'LineLBFGS',
        'mdmin': 'MDMin',
        'ndpoly': 'NDPoly',
        'quasinewton': 'QuasiNewton',
        'scipyfmin': 'SciPyFmin',
        'scipyfminbfgs': 'SciPyFminBFGS',
        'scipyfmincg': 'SciPyFminCG',
        'scipyfminpowell': 'SciPyFminPowell',
        'scipygradientlessoptimizer': 'SciPyGradientlessOptimizer',
    }

    current_val = possibilities.get(optimizer_name.lower())

    if current_val:
        return f'from ase.optimize import {current_val} as custom_optimizer'

    package, current_val = optimizer_name.rsplit('.', 1)
    return f'from ase.optimize.{package} import {current_val} as custom_optimizer'


def convert_the_getters(getters):
    """
    A function used to prepare the arguments of calculator and atoms getter methods
    """
    return_list = []
    for getter in getters:

        if isinstance(getter, str):
            out_args = ''
            method_name = getter

        else:
            method_name, a = getter

            out_args = convert_the_args(a)

        return_list.append((method_name, out_args))

    return return_list


def convert_the_args(raw_args):
    """
    Function used to convert the arguments of methods
    """
    if not raw_args:
        return ''

    if isinstance(raw_args, dict):
        out_args = ', '.join([f'{k}={v}' for k, v in raw_args.items()])

    elif isinstance(raw_args, (list, tuple)):
        new_list = []
        for x in raw_args:
            if isinstance(x, str):
                new_list.append(x)
            elif isinstance(x, dict):
                new_list.append(', '.join([f'{k}={v}' for k, v in x.items()]))
            else:
                raise ValueError('Error preparing the getters')
        out_args = ', '.join(new_list)
    else:
        raise ValueError("Couldn't recognize list of getters")
    return out_args
