# -*- coding: utf-8 -*-
"""Workchain to run a GPAW calculation with automated error handling and restarts."""

from aiida import orm
from aiida.common import AttributeDict
from aiida.engine import while_, BaseRestartWorkChain
from aiida.plugins import CalculationFactory

AseCalculation = CalculationFactory('ase.ase')  # pylint: disable=invalid-name


class BaseGPAWWorkChain(BaseRestartWorkChain):
    # yapf: disable
    """Workchain to run a GPAW calculation with automated error handling and restarts."""

    _process_class = AseCalculation

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
        self.ctx.restart_calc = None
        self.initial_calc = True

    def validate_inputs(self):
        """Validate the inputs."""
        if not self.ctx.inputs.metadata.options.write_gpw:
            self.report('Allowing the .gpw file to be produced at the end of the calculation')
            self.ctx.inputs.metadata.options.write_gpw = True

    def prepare_process(self):
        """Prepare the calculation."""
        if self.initial_calc:
            self.ctx.inputs.structure = self.inputs.structure