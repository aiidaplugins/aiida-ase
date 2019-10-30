# -*- coding: utf-8 -*-
# pylint: disable=unused-argument
"""Tests for the `PwParser`."""
from __future__ import absolute_import

import pytest
from aiida.common import AttributeDict
from aiida.plugins import CalculationFactory

AseCalculation = CalculationFactory('ase.ase')


@pytest.fixture
def generate_inputs_default():
    """Return only those inputs that the parser will expect to be there."""
    return AttributeDict({})


def test_default_gpaw(aiida_profile, aiida_localhost, generate_calc_job_node, generate_parser, generate_inputs_default,
    data_regression):
    """Test a default GPAW calculator."""
    name = 'default_gpaw'
    entry_point_calc_job = 'ase.ase'
    entry_point_parser = 'ase.ase'

    attributes = {
        'output_filename': AseCalculation._OUTPUT_FILE_NAME
    }

    node = generate_calc_job_node(entry_point_calc_job, aiida_localhost, name, generate_inputs_default, attributes=attributes)
    parser = generate_parser(entry_point_parser)
    results, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_finished_ok, calcfunction.exit_message
    assert 'structure' in results
    assert 'parameters' in results

    data_regression.check({
        'structure': results['structure'].attributes,
        'parameters': results['parameters'].get_dict(),
    })
