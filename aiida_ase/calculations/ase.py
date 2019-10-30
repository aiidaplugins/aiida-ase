# -*- coding: utf-8 -*-
"""`CalcJob` implementation that can be used to wrap around the ASE calculators."""
import six

from aiida import get_file_header
from aiida import orm
from aiida.common.datastructures import CalcInfo, CodeInfo
from aiida.common.exceptions import InputValidationError
from aiida.engine import CalcJob


class AseCalculation(CalcJob):
    """`CalcJob` implementation that can be used to wrap around the ASE calculators."""

    _default_parser = 'ase.ase'
    _INPUT_FILE_NAME = 'aiida_script.py'
    _OUTPUT_FILE_NAME = 'results.json'
    _TXT_OUTPUT_FILE_NAME = 'aiida.out'
    _input_aseatoms = 'aiida_atoms.json'
    _output_aseatoms = 'aiida_out_atoms.json'

    @classmethod
    def define(cls, spec):
        # yapf: disable
        super(AseCalculation, cls).define(spec)
        spec.input('metadata.options.input_filename', valid_type=six.string_types, default=cls._INPUT_FILE_NAME,
            help='Filename to which the input for the code that is to be run will be written.')
        spec.input('metadata.options.output_filename', valid_type=six.string_types, default=cls._OUTPUT_FILE_NAME,
            help='Filename to which the content of stdout of the code that is to be run will be written.')
        spec.input('metadata.options.error_filename', valid_type=six.string_types, default='aiida.err',
            help='Filename to which the content of stderr of the code that is to be run will be written.')
        spec.input('metadata.options.parser_name', valid_type=six.string_types, default=cls._default_parser,
            help='Define the parser to be used by setting its entry point name.')

        spec.input('structure', valid_type=orm.StructureData, required=True,
            help='')
        spec.input('parameters', valid_type=orm.Dict, required=False,
            help='')
        spec.input('kpoints', valid_type=orm.KpointsData, required=False,
            help='')
        spec.input('settings', valid_type=orm.Dict, required=False,
            help='')

        spec.output('structure', valid_type=orm.StructureData, required=False,
            help='The `structure` output node of the successful calculation if present.')
        spec.output('parameters', valid_type=orm.Dict, required=False,
            help='')
        spec.output('array', valid_type=orm.ArrayData, required=False,
            help='')

        spec.exit_code(300, 'ERROR_OUTPUT_FILES',
            message='One of the expected output files was missing.')

    def prepare_for_submission(self, folder):
        """This method is called prior to job submission with a set of calculation input nodes.

        The inputs will be validated and sanitized, after which the necessary input files will be written to disk in a
        temporary folder. A CalcInfo instance will be returned that contains lists of files that need to be copied to
        the remote machine before job submission, as well as file lists that are to be retrieved after job completion.

        :param folder: an aiida.common.folders.Folder to temporarily write files on disk
        :returns: CalcInfo instance
        """
        if 'settings' in self.inputs:
            settings = self.inputs.settings.get_dict()
        else:
            settings = {}

        # default atom getter: I will always retrieve the total energy at least
        default_atoms_getters = [["total_energy", ""]]

        # ================================

        # save the structure in ase format
        atoms = self.inputs.structure.get_ase()

        with folder.open(self._input_aseatoms, 'w') as handle:
            atoms.write(handle, format='json')

        # ================== prepare the arguments of functions ================

        parameters_dict = self.inputs.parameters.get_dict()

        # ==================== fix the args of the optimizer

        optimizer = parameters_dict.pop("optimizer", None)
        if optimizer is not None:
            # Validation
            if not isinstance(optimizer, dict):
                raise InputValidationError("optimizer key must contain a dictionary")
            # get the name of the optimizer
            optimizer_name = optimizer.pop("name", None)
            if optimizer_name is None:
                raise InputValidationError("Don't have access to the optimizer name")

            # prepare the arguments to be passed to the optimizer class
            optimizer_argsstr = "atoms, " + convert_the_args(optimizer.pop("args", []))

            # prepare the arguments to be passed to optimizer.run()
            optimizer_runargsstr = convert_the_args(optimizer.pop("run_args", []))

            # prepare the import string
            optimizer_import_string = get_optimizer_impstr(optimizer_name)

        # ================= determine the calculator name and its import ====

        calculator = parameters_dict.pop("calculator", {})
        calculator_import_string = get_calculator_impstr(calculator.pop("name", None))

        # =================== prepare the arguments for the calculator call

        read_calc_args = calculator.pop("args",[])
        if read_calc_args is None:
            calc_argsstr = ""
        else:
            # transform a in "a" if a is a string (needed for formatting)
            calc_args = {}
            for k,v in read_calc_args.items():
                if isinstance(v,  six.string_types):
                    the_v = '"{}"'.format(v)
                else:
                    the_v = v
                calc_args[k] = the_v

            def return_a_function(v):
                try:
                    has_magic = "@function" in v.keys()
                except AttributeError:
                    has_magic = False

                if has_magic:

                    args_dict = {}
                    for k2,v2 in v['args'].items():
                        if isinstance(v2, six.string_types):
                            the_v = '"{}"'.format(v2)
                        else:
                            the_v = v2
                        args_dict[k2] = the_v

                    v2 = "{}({})".format(v['@function'],
                                         ", ".join(["{}={}".format(k_,v_)
                                            for k_,v_ in args_dict.items()]))
                    return v2
                else:
                    return v

            tmp_list = [ "{}={}".format(k,return_a_function(v))
                         for k,v in calc_args.items() ]

            calc_argsstr = ", ".join( tmp_list )

            # add kpoints if present
            if 'kpoints' in self.inputs:
                #TODO: here only the mesh is supported
                # maybe kpoint lists are supported as well in ASE calculators
                try:
                    mesh = self.inputs.kpoints.get_kpoints_mesh()[0]
                except AttributeError:
                    raise InputValidationError("Coudn't find a mesh of kpoints"
                                               " in the KpointsData")
                calc_argsstr = ", ".join( [calc_argsstr] + ["kpts=({},{},{})".format( *mesh )] )

        # =============== prepare the methods of atoms.get(), to save results

        atoms_getters = default_atoms_getters + convert_the_getters(parameters_dict.pop("atoms_getters", []))

        # =============== prepare the methods of calculator.get(), to save results

        calculator_getters = convert_the_getters(parameters_dict.pop("calculator_getters", []))

        # ===================== build the strings with the module imports

        all_imports = ["import ase", 'import ase.io', "import json", "import numpy", calculator_import_string]

        if optimizer is not None:
            all_imports.append(optimizer_import_string)

        try:
            if "PW" in calc_args['mode'].values():
                all_imports.append("from gpaw import PW")
        except KeyError:
            pass

        extra_imports = parameters_dict.pop("extra_imports",[])
        for i in extra_imports:
            if isinstance(i, six.string_types):
                all_imports.append("import {}".format(i))
            elif isinstance(i,(list,tuple)):
                if not all( [isinstance(j, six.string_types) for j in i] ):
                    raise ValueError("extra import must contain strings")
                if len(i)==2:
                    all_imports.append("from {} import {}".format(*i))
                elif len(i)==3:
                    all_imports.append("from {} import {} as {}".format(*i))
                else:
                    raise ValueError("format for extra imports not recognized")
            else:
                raise ValueError("format for extra imports not recognized")

        if self.options.withmpi:
            all_imports.append( "from ase.parallel import paropen" )

        all_imports_string = "\n".join(all_imports) + "\n"

        # =================== prepare the python script ========================

        input_txt = ""
        input_txt += get_file_header()
        input_txt += "# calculation pk: {}\n".format(self.node.pk)
        input_txt += "\n"
        input_txt += all_imports_string
        input_txt += "\n"

        pre_lines = parameters_dict.pop("pre_lines",None)
        if pre_lines is not None:
            if not isinstance(pre_lines,(list,tuple)):
                raise ValueError("Prelines must be a list of strings")
            if not all( [isinstance(_, six.string_types) for _ in pre_lines] ):
                raise ValueError("Prelines must be a list of strings")
            input_txt += "\n".join(pre_lines) + "\n\n"

        input_txt += "atoms = ase.io.read('{}')\n".format(self._input_aseatoms)
        input_txt += "\n"
        input_txt += "calculator = custom_calculator({})\n".format(calc_argsstr)
        input_txt += "atoms.set_calculator(calculator)\n"
        input_txt += "\n"

        if optimizer is not None:
            # here block the trajectory file name: trajectory = 'aiida.traj'
            input_txt += "optimizer = custom_optimizer({})\n".format(optimizer_argsstr)
            input_txt += "optimizer.run({})\n".format(optimizer_runargsstr)
            input_txt += "\n"

        # now dump / calculate the results
        input_txt += "results = {}\n"
        for getter,getter_args in atoms_getters:
            input_txt += "results['{}'] = atoms.get_{}({})\n".format(getter,
                                                                     getter,
                                                                     getter_args)
        input_txt += "\n"

        for getter,getter_args in calculator_getters:
            input_txt += "results['{}'] = calculator.get_{}({})\n".format(getter,
                                                                          getter,
                                                                          getter_args)
        input_txt += "\n"

        # Convert to lists
        input_txt += "for k,v in results.items():\n"
        input_txt += "    if isinstance(results[k],(numpy.matrix,numpy.ndarray)):\n"
        input_txt += "        results[k] = results[k].tolist()\n"

        input_txt += "\n"

        post_lines = parameters_dict.pop("post_lines",None)
        if post_lines is not None:
            if not isinstance(post_lines,(list,tuple)):
                raise ValueError("Postlines must be a list of strings")
            if not all( [isinstance(_, six.string_types) for _ in post_lines] ):
                raise ValueError("Postlines must be a list of strings")
            input_txt += "\n".join(post_lines) + "\n\n"

        # Dump results to file
        right_open = "paropen" if self.options.withmpi else "open"
        input_txt += "with {}('{}', 'w') as f:\n".format(right_open, self._OUTPUT_FILE_NAME)
        input_txt += "    json.dump(results,f)\n"
        input_txt += "\n"

        # Always dump the resulting structure because even if we do not specify an explicit ASE optimizer, the
        # calculation itself can perform an internal optimization producing a new structure.
        input_txt += "atoms.write('{}')\n".format(self._output_aseatoms)
        input_txt += "\n"

        # write all the input script to a file
        with folder.open(self._INPUT_FILE_NAME, 'w') as handle:
            handle.write(input_txt)

        # ============================ calcinfo ================================

        # TODO: look at the qmmm infoL: it might be necessary to put
        # some singlefiles in the directory.
        # right now it has to be taken care in the pre_lines

        local_copy_list = []
        remote_copy_list = []
        additional_retrieve_list = settings.pop("ADDITIONAL_RETRIEVE_LIST", [])

        calcinfo = CalcInfo()

        calcinfo.uuid = self.uuid
        # Empty command line by default
        # calcinfo.cmdline_params = settings.pop('CMDLINE', [])
        calcinfo.local_copy_list = local_copy_list
        calcinfo.remote_copy_list = remote_copy_list

        codeinfo = CodeInfo()
        codeinfo.cmdline_params = [self._INPUT_FILE_NAME]
        #calcinfo.stdin_name = self._INPUT_FILE_NAME
        codeinfo.stdout_name = self.options.output_filename
        codeinfo.code_uuid = self.inputs.code.uuid
        calcinfo.codes_info = [codeinfo]

        # Retrieve files
        calcinfo.retrieve_list = []
        calcinfo.retrieve_list.append(self._OUTPUT_FILE_NAME)
        calcinfo.retrieve_list.append(self._output_aseatoms)
        calcinfo.retrieve_list += additional_retrieve_list

        # TODO: I should have two ways of running it: with gpaw-python in parallel
        # and executing python if in serial

        return calcinfo

def get_calculator_impstr(calculator_name):
    """
    Returns the import string for the calculator
    """
    if calculator_name.lower() == "gpaw" or calculator_name is None:
        return "from gpaw import GPAW as custom_calculator"
    elif calculator_name.lower() == "espresso":
        return "from espresso import espresso as custom_calculator"
    else:
        possibilities = {"abinit":"abinit.Abinit",
                         "aims":"aims.Aims",
                         "ase_qmmm_manyqm":"AseQmmmManyqm",
                         "castep":"Castep",
                         "dacapo":"Dacapo",
                         "dftb":"Dftb",
                         "eam":"EAM",
                         "elk":"ELK",
                         "emt":"EMT",
                         "exciting":"Exciting",
                         "fleur":"FLEUR",
                         "gaussian":"Gaussian",
                         "gromacs":"Gromacs",
                         "mopac":"Mopac",
                         "morse":"MorsePotential",
                         "nwchem":"NWChem",
                         'siesta':"Siesta",
                         "tip3p":"TIP3P",
                         "turbomole":"Turbomole",
                         "vasp":"Vasp",
                         }

        current_val = possibilities.get(calculator_name.lower())

        package, class_name = (calculator_name,current_val) if current_val else calculator_name.rsplit('.',1)

        return "from ase.calculators.{} import {} as custom_calculator".format(package, class_name)

def get_optimizer_impstr(optimizer_name):
    """
    Returns the import string for the optimizer
    """
    possibilities = {"bfgs":"BFGS",
                     "bfgslinesearch":"BFGSLineSearch",
                     "fire":"FIRE",
                     "goodoldquasinewton":"GoodOldQuasiNewton",
                     "hesslbfgs":"HessLBFGS",
                     "lbfgs":"LBFGS",
                     "lbfgslinesearch":"LBFGSLineSearch",
                     "linelbfgs":"LineLBFGS",
                     "mdmin":"MDMin",
                     "ndpoly":"NDPoly",
                     "quasinewton":"QuasiNewton",
                     "scipyfmin":"SciPyFmin",
                     "scipyfminbfgs":"SciPyFminBFGS",
                     "scipyfmincg":"SciPyFminCG",
                     "scipyfminpowell":"SciPyFminPowell",
                     "scipygradientlessoptimizer":"SciPyGradientlessOptimizer",
                     }

    current_val = possibilities.get(optimizer_name.lower())

    if current_val:
        return "from ase.optimize import {} as custom_optimizer".format(current_val)
    else:
        package,current_val = optimizer_name.rsplit('.',1)
        return "from ase.optimize.{} import {} as custom_optimizer".format(package,current_val)

def convert_the_getters(getters):
    """
    A function used to prepare the arguments of calculator and atoms getter methods
    """
    return_list = []
    for getter in getters:

        if isinstance(getter, six.string_types):
            out_args = ""
            method_name = getter

        else:
            method_name, a = getter

            out_args = convert_the_args(a)

        return_list.append( (method_name, out_args) )
    return return_list

def convert_the_args(raw_args):
    """
    Function used to convert the arguments of methods
    """
    if not raw_args:
        return ""
    if isinstance(raw_args,dict):
        out_args = ", ".join([ "{}={}".format(k,v) for k,v in raw_args.items() ])

    elif isinstance(raw_args,(list,tuple)):
        new_list = []
        for x in raw_args:
            if isinstance(x, six.string_types):
                new_list.append(x)
            elif isinstance(x,dict):
                new_list.append( ", ".join([ "{}={}".format(k,v) for k,v in x.items() ]) )
            else:
                raise ValueError("Error preparing the getters")
        out_args = ", ".join(new_list)
    else:
        raise ValueError("Couldn't recognize list of getters")
    return out_args
