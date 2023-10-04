# -*- coding: utf-8 -*-
"""Parser implementation for the ``AseCalculation``."""
import json

from aiida import parsers, plugins
from ase.io import read
import numpy

Dict = plugins.DataFactory('core.dict')
ArrayData = plugins.DataFactory('core.array')
StructureData = plugins.DataFactory('core.structure')
AseCalculation = plugins.CalculationFactory('ase.ase')


class AseParser(parsers.Parser):
    """Parser implementation for the ``AseCalculation``."""

    def parse(self, **kwargs):  # pylint: disable=inconsistent-return-statements
        """Parse the retrieved files from a ``AseCalculation``."""
        retrieved = self.retrieved

        # check what is inside the folder
        list_of_files = retrieved.base.repository.list_object_names()

        # at least the stdout should exist
        if AseCalculation._OUTPUT_FILE_NAME not in list_of_files:  # pylint: disable=protected-access
            self.logger.error('Standard output not found')
            return self.exit_codes.ERROR_OUTPUT_FILES

        # output structure
        if AseCalculation._output_aseatoms in list_of_files:  # pylint: disable=protected-access
            with retrieved.base.repository.open(AseCalculation._output_aseatoms, 'r') as handle:  # pylint: disable=protected-access
                atoms = read(handle, format='json')
                structure = StructureData(ase=atoms)
                self.out('structure', structure)

        filename_stdout = self.node.base.attributes.all.get('output_filename')

        # load the results dictionary
        with retrieved.base.repository.open(filename_stdout, 'r') as handle:
            json_params = json.load(handle)

        # extract arrays from json_params
        dictionary_array = {}
        for k, v in list(json_params.items()):
            if isinstance(v, (list, tuple)):
                dictionary_array[k] = json_params.pop(k)

        # look at warnings
        warnings = []
        with retrieved.base.repository.open('_scheduler-stderr.txt', 'r') as handle:
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
            self.out('parameters', Dict(json_params))

        return
