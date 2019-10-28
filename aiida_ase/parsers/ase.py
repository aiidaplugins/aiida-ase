# -*- coding: utf-8 -*-
import json
import numpy

import ase

from aiida import orm
from aiida.common import exceptions
from aiida.parsers import Parser
from aiida.plugins import CalculationFactory

AseCalculation = CalculationFactory('ase.ase')


class AseParser(Parser):
    """`Parser` implementation that can parse the output produced by an ASE calculator."""

    def __init__(self, node):
        super(AseParser, self).__init__(node)
        if not issubclass(node.process_class, AseCalculation):
            raise exceptions.ParsingError(
                'Node process class must be a {} but node<{}> has process class {}'.format(
                    AseCalculation, node.uuid, node.process_class
                )
            )

    def parse(self, **kwargs):
        """Parse the contents of the output files retrieved in the `FolderData`."""
        try:
            output_folder = self.retrieved
        except exceptions.NotExistent:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        # select the folder object
        output_folder = self._calc.get_retrieved_node()

        # check what is inside the folder
        list_of_files = output_folder.get_content_list()

        # at least the stdout should exist
        if AseCalculation._OUTPUT_FILE_NAME not in list_of_files:
            self.logger.error('Standard output not found')
            return self.exit_codes.ERROR_OUTPUT_FILES

        # output structure
        has_out_atoms = True if AseCalculation._output_aseatoms in list_of_files else False
        if has_out_atoms:
            with output_folder.open(AseCalculation._output_aseatoms, 'rb') as handle:
                atoms = ase.io.read(handle)
                structure = orm.StructureData().set_ase(atoms)
                self.out('structure', structure)

        filename_stdout = self.node.get_attribute('output_filename')

        # load the results dictionary
        with output_folder.open(filename_stdout, 'r') as handle:
            json_params = json.load(handle)

        # extract arrays from json_params
        dictionary_array = {}
        for k, v in list(json_params.items()):
            if isinstance(v, (list, tuple)):
                dictionary_array[k] = json_params.pop(k)

        # look at warnings
        warnings = []
        with output_folder.open('_scheduler-stderr.txt', 'r') as handle:
            errors = handle.read()
        if errors:
            warnings = [errors]
        json_params['warnings'] = warnings

        if dictionary_array:
            array_data = orm.ArrayData()
            for k, v in dictionary_array.items():
                array_data.set_array(k, numpy.array(v))
            self.out('array', array_data)

        if json_params:
            self.out('parameters', orm.Dict(dict=json_params))

        return
