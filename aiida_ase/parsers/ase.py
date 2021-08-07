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
                self.out('output_structure', structure)

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
            self.out('output_array', array_data)

        if json_params:
            self.out('output_parameters', Dict(dict=json_params))

        return
