# -*- coding: utf-8 -*-
"""Workchain to run a GPAW calculation with automated error handling and restarts."""

from aiida import orm
from aiida.engine import while_, BaseRestartWorkChain, process_handler, ProcessHandlerReport
from aiida.plugins import CalculationFactory
from aiida.common import AttributeDict, exceptions

AseCalculation = CalculationFactory('ase.ase')  # pylint: disable=invalid-name


class BaseGPAWWorkChain(BaseRestartWorkChain):
    # yapf: disable
    """Workchain to run a GPAW calculation with automated error handling and restarts."""

    _process_class = AseCalculation

    defaults = AttributeDict({
            'beta_default':0.05,
            'nmaxold_default':5,
            'weight_default':50.0,
            'beta_factor':0.9,
    })


    @classmethod
    def define(cls, spec):
        """Define the process specification."""
        super().define(spec)
        spec.expose_inputs(AseCalculation, namespace='gpaw', exclude=['structure'])
        spec.input('structure', valid_type=orm.StructureData, required=True,
                    help='The input structure.')

        spec.expose_outputs(AseCalculation)

        spec.outline(
            cls.setup,
            cls.validate_inputs,
            while_(cls.should_run_process)(
                cls.prepare_process,
                cls.run_process,
                cls.inspect_process,
            ),
            cls.results,
        )

        # yapf: enable

    def setup(self):
        """Set up the calculation."""
        super().setup()
        self.ctx.inputs = AttributeDict(self.inputs.gpaw)
        self.initial_calc = True

    def validate_inputs(self):
        """Validate the inputs."""
        self.ctx.inputs.metadata.options.parser_name = 'ase.gpaw'

    def prepare_process(self):
        """Prepare the calculation."""
        if self.initial_calc:
            self.ctx.inputs.structure = self.inputs.structure
            self.initial_calc = False

    @process_handler(exit_codes=[AseCalculation.exit_codes.ERROR_RELAX_NOT_COMPLETE])
    def handle_relax_not_complete(self, calculation):
        """Handle the relaxation not complete error."""
        try:
            self.ctx.inputs.structure = calculation.outputs.trajectory.get_step_structure()[-1]
            self.report_error_handled('relaxation not complete; starting from final structure')
        except exceptions.NotExistent:
            self.report_error_handled('relaxation not complete; no structure found')
        return ProcessHandlerReport(True)

    @process_handler(exit_codes=[AseCalculation.exit_codes.ERROR_SCF_NOT_COMPLETE])
    def handle_scf_not_complete(self, calculation):  # pylint: disable=unused-argument
        """Handle the SCF not complete error."""
        new_mixer = self.defaults.beta_default * self.defaults.beta_factor
        nmaxold = self.defaults.nmaxold_default
        weight = self.defaults.weight_default
        parameters = self.ctx.inputs.parameters.get_dict()
        parameters.set_default('calculation', {})['mixer'] = f'Mixer({new_mixer}, {nmaxold}, {weight})'
        parameters['extra_imports'] = ['gpaw', 'Mixer']

        self.ctx.inputs.parameters = orm.Dict(dict=parameters)
        self.report_error_handled('SCF not complete; starting from inital structure with lower mixing')
        return ProcessHandlerReport(True)

    @process_handler(exit_codes=[AseCalculation.exit_codes.ERROR_UNEXPECTED_EXCEPTION])
    def handle_unexpected_exception(self, calculation):  # pylint: disable=unused-argument
        """Handle the unexpected exception error."""
        self.report_error_handled('unexpected exception; starting from initial structure')
        return ProcessHandlerReport(True, self.AseCalculation.exit_codes.ERROR_UNEXPECTED_EXCEPTION)
