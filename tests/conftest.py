# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name
"""Fixtures for the unit test suite."""
import collections
import re

from aiida import orm
import pytest

pytest_plugins = ['aiida.manage.tests.pytest_fixtures']  # pylint: disable=invalid-name


@pytest.fixture(scope='function')
def fixture_sandbox():
    """Return a ``SandboxFolder``."""
    from aiida.common.folders import SandboxFolder
    with SandboxFolder() as folder:
        yield folder


@pytest.fixture
def fixture_localhost(aiida_localhost):
    """Return a localhost ``Computer``."""
    localhost = aiida_localhost
    localhost.set_default_mpiprocs_per_machine(1)
    return localhost


@pytest.fixture
def generate_parser():
    """Fixture to load a parser class for testing parsers."""

    def _generate_parser(entry_point_name):
        """Fixture to load a parser class for testing parsers.

        :param entry_point_name: entry point name of the parser class
        :return: the `Parser` sub class
        """
        from aiida.plugins import ParserFactory
        return ParserFactory(entry_point_name)

    return _generate_parser


@pytest.fixture
def generate_calc_job():
    """Fixture to construct a new ``CalcJob`` instance and call ``prepare_for_submission``.

    The fixture will return the ``CalcInfo`` returned by ``prepare_for_submission`` and the temporary folder that was
    passed to it, into which the raw input files will have been written.
    """

    def _generate_calc_job(folder, entry_point_name, inputs=None):
        """Fixture to generate a mock ``CalcInfo`` for testing calculation jobs."""
        from aiida.engine.utils import instantiate_process
        from aiida.manage.manager import get_manager
        from aiida.plugins import CalculationFactory

        manager = get_manager()
        runner = manager.get_runner()

        process_class = CalculationFactory(entry_point_name)
        process = instantiate_process(runner, process_class, **inputs)

        calc_info = process.prepare_for_submission(folder)

        return calc_info

    return _generate_calc_job


@pytest.fixture
def generate_calc_job_node():
    """Fixture to generate a mock `CalcJobNode` for testing parsers."""

    def flatten_inputs(inputs, prefix=''):
        """This function follows roughly the same logic as `aiida.engine.processes.process::Process._flatten_inputs`."""
        flat_inputs = []
        for key, value in inputs.items():
            if isinstance(value, collections.abc.Mapping):
                flat_inputs.extend(flatten_inputs(value, prefix=prefix + key + '__'))
            else:
                flat_inputs.append((prefix + key, value))
        return flat_inputs

    def _generate_calc_job_node(entry_point_name, computer, test_name=None, inputs=None, attributes=None):
        """Fixture to generate a mock `CalcJobNode` for testing parsers.

        :param entry_point_name: entry point name of the calculation class
        :param computer: a `Computer` instance
        :param test_name: relative path of directory with test output files in the `fixtures/{entry_point_name}` folder.
        :param inputs: any optional nodes to add as input links to the corrent CalcJobNode
        :param attributes: any optional attributes to set on the node
        :return: `CalcJobNode` instance with an attached `FolderData` as the `retrieved` node
        """
        # pylint: disable=too-many-locals
        import os

        from aiida.common import LinkType
        from aiida.plugins.entry_point import format_entry_point_string

        entry_point = format_entry_point_string('aiida.calculations', entry_point_name)

        node = orm.CalcJobNode(computer=computer, process_type=entry_point)
        node.set_option('resources', {'num_machines': 1, 'num_mpiprocs_per_machine': 1})
        node.set_option('max_wallclock_seconds', 1800)

        if attributes:
            node.set_attribute_many(attributes)

        if inputs:
            metadata = inputs.pop('metadata', {})
            options = metadata.get('options', {})

            for name, option in options.items():
                node.set_option(name, option)

            for link_label, input_node in flatten_inputs(inputs):
                input_node.store()
                node.add_incoming(input_node, link_type=LinkType.INPUT_CALC, link_label=link_label)

        node.store()

        if test_name is not None:
            basepath = os.path.dirname(os.path.abspath(__file__))
            filepath = os.path.join(basepath, 'parsers', 'fixtures', 'ase', test_name)

            retrieved = orm.FolderData()
            retrieved.put_object_from_tree(filepath)
            retrieved.add_incoming(node, link_type=LinkType.CREATE, link_label='retrieved')
            retrieved.store()

            remote_folder = orm.RemoteData(computer=computer, remote_path='/tmp')
            remote_folder.add_incoming(node, link_type=LinkType.CREATE, link_label='remote_folder')
            remote_folder.store()

        return node

    return _generate_calc_job_node


@pytest.fixture
def generate_inputs_ase(generate_code, generate_structure, generate_kpoints_mesh):
    """Generate inputs for an ``AseCalculation``."""

    def _generate_inputs_ase():
        parameters = {
            'calculator': {
                'name': 'gpaw',
                'args': {
                    'mode': {
                        '@function': 'PW',
                        'args': {
                            'ecut': 300
                        }
                    }
                }
            },
            'atoms_getters': [
                'temperature',
                ['forces', {
                    'apply_constraint': True
                }],
                ['masses', {}],
            ],
            'calculator_getters': [
                ['potential_energy', {}],
                'spin_polarized',
                ['stress', ['atoms']],
            ],
            'optimizer': {
                'name': 'QuasiNewton',
                'args': {
                    'alpha': 0.9,
                },
                'run_args': {
                    'fmax': 0.05
                }
            },
        }
        inputs = {
            'code': generate_code('ase.ase'),
            'structure': generate_structure(),
            'kpoints': generate_kpoints_mesh(2),
            'parameters': orm.Dict(dict=parameters),
            'metadata': {
                'options': {
                    'resources': {
                        'num_machines': 1,
                    }
                }
            }
        }
        return inputs

    return _generate_inputs_ase


@pytest.fixture
def generate_code(fixture_localhost):
    """Return a ``Code`` instance configured to run calculations of given entry point on localhost ``Computer``."""

    def _generate_code(entry_point_name):
        from aiida.common import exceptions
        from aiida.orm import Code

        label = f'test.{entry_point_name}'

        try:
            return Code.objects.get(label=label)  # pylint: disable=no-member
        except exceptions.NotExistent:
            return Code(
                label=label,
                input_plugin_name=entry_point_name,
                remote_computer_exec=[fixture_localhost, '/bin/true'],
            )

    return _generate_code


@pytest.fixture
def generate_structure():
    """Return a ``StructureData``."""

    def _generate_structure(elements=('Ar',)):
        """Return a ``StructureData``."""
        from aiida.orm import StructureData

        structure = StructureData(cell=[[1, 0, 0], [0, 1, 0], [0, 0, 1]])

        for index, element in enumerate(elements):
            symbol = re.sub(r'[0-9]+', '', element)
            structure.append_atom(position=(index * 0.5, index * 0.5, index * 0.5), symbols=symbol, name=element)

        return structure

    return _generate_structure


@pytest.fixture
def generate_kpoints_mesh():
    """Return a `KpointsData` node."""

    def _generate_kpoints_mesh(npoints):
        """Return a `KpointsData` with a mesh of npoints in each direction."""
        from aiida.orm import KpointsData

        kpoints = KpointsData()
        kpoints.set_kpoints_mesh([npoints] * 3)

        return kpoints

    return _generate_kpoints_mesh
