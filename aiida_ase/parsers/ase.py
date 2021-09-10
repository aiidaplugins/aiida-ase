# -*- coding: utf-8 -*-
"""Parser implementation for the ``AseCalculation``."""
import json
import numpy

from aiida import parsers
from aiida import plugins
from ase.io import read

Dict = plugins.DataFactory('dict')
ArrayData = plugins.DataFactory('array')
StructureData = plugins.DataFactory('structure')
TrajectoryData = plugins.DataFactory('array.trajectory')
AseCalculation = plugins.CalculationFactory('ase.ase')


class AseParser(parsers.Parser):
    """Parser implementation for the ``AseCalculation``."""

    def parse(self, **kwargs):  # pylint: disable=inconsistent-return-statements
        """Parse the retrieved files from a ``AseCalculation``."""
        retrieved = self.retrieved

        # check what is inside the folder
        list_of_files = retrieved.list_object_names()

        # at least the stdout should exist
        if AseCalculation._OUTPUT_FILE_NAME not in list_of_files:  # pylint: disable=protected-access
            self.logger.error('Standard output not found')
            return self.exit_codes.ERROR_OUTPUT_FILES

        # output structure
        if AseCalculation._output_aseatoms in list_of_files:  # pylint: disable=protected-access
            with retrieved.open(AseCalculation._output_aseatoms, 'r') as handle:  # pylint: disable=protected-access
                atoms = read(handle, format='json')
                structure = StructureData(ase=atoms)
                self.out('structure', structure)

        filename_stdout = self.node.get_attribute('output_filename')

        # load the results dictionary
        with retrieved.open(filename_stdout, 'r') as handle:
            json_params = json.load(handle)

        # extract arrays from json_params
        dictionary_array = {}
        for k, v in list(json_params.items()):
            if isinstance(v, (list, tuple)):
                dictionary_array[k] = json_params.pop(k)

        # look at warnings
        warnings = []
        with retrieved.open('_scheduler-stderr.txt', 'r') as handle:
            errors = handle.read()
        if errors:
            warnings = [errors]
        json_params['warnings'] = warnings

        if dictionary_array:
            array_data = ArrayData()
            for k, v in dictionary_array.items():
                array_data.set_array(k, numpy.array(v))
            self.out('array', array_data)

        if json_params:
            self.out('parameters', Dict(dict=json_params))

        return


class GPAWParser(parsers.Parser):
    """Parser implementation for GPAW through an ``AseCalculation``."""

    def parse(self, **kwargs):  # pylint: disable=inconsistent-return-statements,too-many-branches,too-many-locals
        """Parse the retrieved files from a ``AseCalculation``."""

        # check what is inside the folder
        list_of_files = self.retrieved.list_object_names()

        # check if it was a relaxation
        optimizer = self.node.inputs.parameters.get_dict().pop('optimizer', None)

        # output json file
        if AseCalculation._OUTPUT_FILE_NAME in list_of_files:  # pylint: disable=protected-access
            # This calculation is likely to have been alright
            pass
        elif AseCalculation._TXT_OUTPUT_FILE_NAME in list_of_files:  # pylint: disable=protected-access
            # An output structure was not found but there is a txt file
            # Probably helpful for restarts
            self.logger.error('Output results was not found, inspecting log file')
            # Checking for possible errors common to all calculations
            with self.retrieved.open('_scheduler-stderr.txt', 'r') as handle:
                lines = handle.readlines()
                is_paw_missing = check_paw_missing(lines)
                if is_paw_missing:
                    self.logger.error('Could not find paw potentials')
                    return self.exit_codes.ERROR_PAW_NOT_FOUND

            if optimizer is not None:
                # This is a relaxation calculation that did not complete
                # try to get all the structures that are available
                try:
                    with self.retrieved.open(self.node.get_attribute('log_filename'), 'r') as handle:
                        all_ase_traj = read(handle, index=':', format='gpaw-out')
                    trajectory = store_to_trajectory_data(all_ase_traj)
                    self.outputs.trajectory = trajectory
                    return self.exit_codes.ERROR_RELAX_NOT_COMPLETE
                except Exception:  # pylint: disable=broad-except
                    # If it made it to here then the error is due to the SCF not completing
                    self.logger.error('First relaxation step not completed')
                    return self.exit_codes.ERROR_SCF_NOT_COMPLETE
            else:
                # This is an SCF calculation that did not complete
                self.logger.error('SCF did not complete')
                return self.exit_codes.ERROR_SCF_NOT_COMPLETE
        else:
            # Neither log file nor end result file were produced
            # Likely to be bad news
            return self.exit_codes.ERROR_UNEXPECTED_EXCEPTION

        # Check if output structure is needed
        if optimizer is not None:
            # If we are here the calculation did complete sucessfully
            with self.retrieved.open(AseCalculation._output_aseatoms, 'r') as handle:  # pylint: disable=protected-access
                atoms = read(handle, format='json')
                self.out('structure', StructureData(ase=atoms))
            # Store the trajectory as well
            with self.retrieved.open(self.node.get_attribute('log_filename'), 'r') as handle:
                all_ase_traj = read(handle, index=':', format='gpaw-out')
            self.outputs.trajectory = store_to_trajectory_data(all_ase_traj)
        # load the results dictionary
        with self.retrieved.open(AseCalculation._OUTPUT_FILE_NAME, 'r') as handle:  # pylint: disable=protected-access
            json_params = json.load(handle)

        # get the relavent data from the log file for the final structure
        with self.retrieved.open(self.node.get_attribute('log_filename'), 'r') as handle:
            atoms_log = read(handle, format='gpaw-out')
        create_output_parameters(atoms_log, json_params)

        # look at warnings
        with self.retrieved.open('_scheduler-stderr.txt', 'r') as handle:
            errors = handle.read()
        if errors:
            json_params['warnings'] = [errors]

        # extract arrays from json_params
        dictionary_array = {}
        for k, v in list(json_params.items()):
            if isinstance(v, (list, tuple, numpy.ndarray)):
                dictionary_array[k] = json_params.pop(k)

        if dictionary_array:
            array_data = ArrayData()
            for k, v in dictionary_array.items():
                array_data.set_array(k, numpy.array(v))
            self.out('array', array_data)

        if json_params:
            self.out('parameters', Dict(dict=json_params))

        return


def check_paw_missing(lines):
    """Check if paw potentials are missing and that is the source of the error."""
    for line in lines:
        if 'Could not find required PAW dataset file' in line:
            return True
    return False


def create_output_parameters(atoms_log, json_params):
    """Create the output parameters from the log file."""
    results_calc = atoms_log.calc.results
    json_params['energy'] = atoms_log.get_potential_energy()
    json_params['energy_contributions'] = atoms_log.calc.energy_contributions
    json_params['forces'] = atoms_log.get_forces()
    json_params['stress'] = results_calc.pop('stress', None)
    json_params['magmoms'] = results_calc.pop('magmoms', None)
    json_params['dipole'] = results_calc.pop('dipole', None)
    json_params['pbc'] = atoms_log.get_pbc()
    json_params['fermi_energy'] = atoms_log.calc.eFermi
    json_params['eigenvalues'] = atoms_log.calc.get_eigenvalues()


def store_to_trajectory_data(all_ase_traj):
    """Store ase atoms object into a TrajectoryFile."""
    all_aiida_atoms = []
    for atoms in all_ase_traj:
        structure = StructureData(ase=atoms)
        all_aiida_atoms.append(structure)
    return TrajectoryData(all_aiida_atoms)
