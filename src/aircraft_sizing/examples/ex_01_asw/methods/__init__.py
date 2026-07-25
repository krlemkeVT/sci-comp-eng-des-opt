"""OpenMDAO + JAX ASW conceptual-sizing model.

Public entry points:

- :class:`~.config.ASWSizingInputs` / :func:`~.config.solve` -- build inputs, solve.
- :func:`~.group.build_asw_problem` -- the underlying ``om.Problem`` (used by lessons).
- :mod:`~.disciplines` -- the pure-JAX physics.
"""

from .config import (
    ASWSizingInputs,
    ASWSizingResult,
    CallCounter,
    IterationStep,
    SegmentRatios,
    derived_quantities,
    input_sensitivity_sweep,
    mission_fractions,
    segment_ratios,
    solve,
)
from .group import ASWSizingGroup, build_asw_problem, make_nonlinear_solver, SOLVER_CHOICES

__all__ = [
    "ASWSizingInputs",
    "ASWSizingResult",
    "SegmentRatios",
    "IterationStep",
    "CallCounter",
    "solve",
    "input_sensitivity_sweep",
    "derived_quantities",
    "segment_ratios",
    "mission_fractions",
    "ASWSizingGroup",
    "build_asw_problem",
    "make_nonlinear_solver",
    "SOLVER_CHOICES",
]
