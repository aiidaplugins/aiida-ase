# -*- coding: utf-8 -*-
"""Tests for the ``AseCalculation`` class."""
from aiida.common import datastructures

from aiida_ase.calculations.ase import AseCalculation


def test_default(fixture_sandbox, generate_calc_job, generate_inputs_ase, file_regression):
    """Test a default ``AseCalculation``."""
    entry_point_name = 'ase.ase'
    inputs = generate_inputs_ase()

    calc_info = generate_calc_job(fixture_sandbox, entry_point_name, inputs)

    assert isinstance(calc_info, datastructures.CalcInfo)
    assert isinstance(calc_info.codes_info[0], datastructures.CodeInfo)

    with fixture_sandbox.open(AseCalculation._INPUT_FILE_NAME) as handle:  # pylint: disable=protected-access
        input_written = handle.read()

    # Checks on the files written to the sandbox folder as raw input
    file_regression.check(input_written, encoding='utf-8', extension='.in')
