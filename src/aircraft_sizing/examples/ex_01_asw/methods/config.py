"""User-facing inputs, results, and the ``solve`` entry point for ASW sizing.

This is the clean public surface of the example: build an :class:`ASWSizingInputs`
(``ASWSizingInputs.baseline()`` reproduces the Raymer 3.6 tutorial), call
:func:`solve`, and read a flat :class:`ASWSizingResult`.  The heavy lifting is done
by the OpenMDAO + JAX model in ``group.py`` / ``components.py`` / ``disciplines.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from math import isfinite
from typing import Iterable

import numpy as np
import openmdao.api as om

from . import disciplines as D
from .atmosphere import AtmosphereState, standard_atmosphere
from .components import CallCounter
from .group import build_asw_problem

__all__ = [
    "ASWSizingInputs",
    "AtmosphereState",
    "SegmentRatios",
    "IterationStep",
    "ASWSizingResult",
    "SizingDivergedError",
    "solve",
    "input_sensitivity_sweep",
    "derived_quantities",
    "segment_ratios",
    "mission_fractions",
    "CallCounter",
]


class SizingDivergedError(RuntimeError):
    """The sizing loop did not close on a physically meaningful takeoff weight.

    Raised rather than letting a broken solve escape as a NaN weight or a complex
    ``W_TO ** b``.  The usual cause is a mission the historical empty-weight
    regression cannot carry: once ``Wf/WTO + We/WTO`` reaches 1 no positive
    ``W_TO`` satisfies ``WTO*(1 - Wf/WTO - We/WTO) = W_fixed`` from the given
    starting guess, and the iteration runs away instead of converging.  For the
    Raymer 3.6 baseline that happens a little beyond a 3,000 nm one-way cruise.
    """


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class ASWSizingInputs:
    """All visible ASW sizing assumptions (defaults == Raymer 3.6 baseline)."""

    cruise_range_one_way_nm: float = 1500.0
    cruise_mach_number: float = 0.6
    cruise_altitude_ft: float = 30_000.0
    mission_equipment_weight_lb: float = 10_000.0
    crew_weight_lb: float = 800.0
    warmup_takeoff_weight_ratio: float = 0.970
    climb_weight_ratio: float = 0.985
    landing_weight_ratio: float = 0.995
    loiter_on_station_endurance_hr: float = 3.0
    loiter_prelanding_endurance_min: float = 20.0
    cruise_thrust_specific_fuel_consumption_lb_per_hr_per_lb: float = 0.5
    loiter_thrust_specific_fuel_consumption_lb_per_hr_per_lb: float = 0.4
    wing_aspect_ratio: float = 7.0
    wetted_area_ratio_s_wet_over_s_ref: float = 5.5
    lift_to_drag_max_k_factor: float = 14.0
    cruise_lift_to_drag_factor: float = 0.866
    reserve_fuel_fraction: float = 0.05
    trapped_unusable_fuel_fraction: float = 0.01
    empty_weight_fraction_coefficient: float = 0.93
    empty_weight_fraction_exponent: float = -0.07
    structure_material: str = "metal"

    # -- construction helpers ------------------------------------------- #
    @classmethod
    def baseline(cls) -> "ASWSizingInputs":
        return cls()

    def with_value(self, name: str, value: float) -> "ASWSizingInputs":
        """Return a copy with one field replaced (used by the sweep helper)."""
        if name not in {f.name for f in fields(self)}:
            raise ValueError(f"Unknown input {name!r}.")
        return replace(self, **{name: value})

    # -- derived scalars ------------------------------------------------- #
    @property
    def atmosphere(self) -> AtmosphereState:
        """Standard-atmosphere state at ``cruise_altitude_ft``.

        Cruise altitude used to sit beside a hand-entered speed of sound, so the
        two could disagree and altitude changed nothing.  Every atmospheric
        property now comes from here, so altitude is the single source of truth.
        """
        return standard_atmosphere(self.cruise_altitude_ft)

    @property
    def speed_of_sound_at_cruise_altitude_ft_per_s(self) -> float:
        """ISA speed of sound at cruise altitude -- the one property the loop uses."""
        return self.atmosphere.speed_of_sound_ft_per_s

    @property
    def fixed_weight_lb(self) -> float:
        return self.mission_equipment_weight_lb + self.crew_weight_lb

    @property
    def material_factor(self) -> float:
        # Raymer: composite construction trims the empty-weight fraction ~5%.
        return 0.95 if self.structure_material == "composite" else 1.0

    # -- mapping onto the OpenMDAO model -------------------------------- #
    def params(self) -> dict:
        """Discipline constants passed to :class:`~.group.ASWSizingGroup`."""
        return {
            "k_ld": self.lift_to_drag_max_k_factor,
            "cruise_ld_factor": self.cruise_lift_to_drag_factor,
            "warmup": self.warmup_takeoff_weight_ratio,
            "climb": self.climb_weight_ratio,
            "landing": self.landing_weight_ratio,
            "reserve": self.reserve_fuel_fraction,
            "trapped": self.trapped_unusable_fuel_fraction,
            "coefficient": self.empty_weight_fraction_coefficient,
            "exponent": self.empty_weight_fraction_exponent,
            "material_factor": self.material_factor,
        }

    def input_values(self) -> dict:
        """Top-level model input values, keyed by full component path."""
        return {
            "aero.wing_aspect_ratio": self.wing_aspect_ratio,
            "aero.wetted_area_ratio": self.wetted_area_ratio_s_wet_over_s_ref,
            "prop.mach": self.cruise_mach_number,
            "prop.speed_of_sound": self.speed_of_sound_at_cruise_altitude_ft_per_s,
            "prop.tsfc_cruise_per_hr": self.cruise_thrust_specific_fuel_consumption_lb_per_hr_per_lb,
            "prop.tsfc_loiter_per_hr": self.loiter_thrust_specific_fuel_consumption_lb_per_hr_per_lb,
            "mission.range_ft": self.cruise_range_one_way_nm * D.FEET_PER_NAUTICAL_MILE,
            "mission.station_endurance_s": self.loiter_on_station_endurance_hr * D.SECONDS_PER_HOUR,
            "mission.preland_endurance_s": self.loiter_prelanding_endurance_min * D.SECONDS_PER_MINUTE,
            "sizing.fixed_weight": self.fixed_weight_lb,
        }

    def __post_init__(self) -> None:
        _validate_inputs(self)


@dataclass(frozen=True, slots=True)
class SegmentRatios:
    """The seven mission-segment weight ratios W2/W1 ... W8/W7."""

    warmup_takeoff: float
    climb: float
    outbound_cruise: float
    on_station_loiter: float
    return_cruise: float
    prelanding_loiter: float
    landing: float

    @property
    def mission_weight_fraction(self) -> float:
        product = 1.0
        for f in fields(self):
            product *= getattr(self, f.name)
        return product


@dataclass(frozen=True, slots=True)
class IterationStep:
    """One fixed-point iterate for the convergence view."""

    iteration_number: int
    guess_takeoff_gross_weight_lb: float
    fuel_weight_fraction: float
    empty_weight_fraction: float
    empty_weight_lb: float
    updated_takeoff_gross_weight_lb: float
    difference_lb: float


@dataclass(frozen=True, slots=True)
class ASWSizingResult:
    """Everything the app / tests need from one converged solve."""

    inputs: ASWSizingInputs
    solver: str
    solver_iterations: int

    final_takeoff_gross_weight_lb: float
    final_empty_weight_fraction: float
    final_empty_weight_lb: float
    fuel_weight_lb: float
    fixed_weight_lb: float

    fuel_weight_fraction: float
    mission_weight_fraction: float
    mission_fuel_fraction: float
    reserve_and_trapped_multiplier: float

    wetted_aspect_ratio: float
    lift_to_drag_max: float
    cruise_lift_to_drag: float
    loiter_lift_to_drag: float

    cruise_altitude_ft: float
    speed_of_sound_ft_per_s: float
    air_density_slug_per_ft3: float
    air_temperature_rankine: float
    air_pressure_lb_per_ft2: float
    cruise_speed_ft_per_s: float
    cruise_dynamic_pressure_lb_per_ft2: float
    sfc_cruise_per_s: float
    sfc_loiter_per_s: float
    cruise_range_ft: float
    loiter_on_station_s: float
    loiter_prelanding_s: float

    segment_ratios: SegmentRatios
    iteration_history: tuple[IterationStep, ...]

    @property
    def iteration_count(self) -> int:
        return len(self.iteration_history)


# --------------------------------------------------------------------------- #
# Pure post-processing helpers (W_TO-independent; read straight from disciplines)
# --------------------------------------------------------------------------- #
def derived_quantities(inputs: ASWSizingInputs) -> dict:
    """Aero + propulsion + mission quantities that do not depend on W_TO.

    Density, temperature, and pressure are reported for context only: Raymer 3.6
    sizes the aircraft from weight fractions alone, so the speed of sound is the
    single atmospheric property that reaches the sizing loop (through the cruise
    true airspeed in the Breguet range equation).
    """
    atmosphere = inputs.atmosphere
    ld_max, ld_cruise, ld_loiter = (
        float(v)
        for v in D.aerodynamics(
            inputs.wing_aspect_ratio,
            inputs.wetted_area_ratio_s_wet_over_s_ref,
            inputs.lift_to_drag_max_k_factor,
            inputs.cruise_lift_to_drag_factor,
        )
    )
    cruise_speed, sfc_cruise, sfc_loiter = (
        float(v)
        for v in D.propulsion(
            inputs.cruise_mach_number,
            inputs.speed_of_sound_at_cruise_altitude_ft_per_s,
            inputs.cruise_thrust_specific_fuel_consumption_lb_per_hr_per_lb,
            inputs.loiter_thrust_specific_fuel_consumption_lb_per_hr_per_lb,
        )
    )
    return {
        "wetted_aspect_ratio": inputs.wing_aspect_ratio / inputs.wetted_area_ratio_s_wet_over_s_ref,
        "lift_to_drag_max": ld_max,
        "cruise_lift_to_drag": ld_cruise,
        "loiter_lift_to_drag": ld_loiter,
        "cruise_altitude_ft": atmosphere.altitude_ft,
        "speed_of_sound_ft_per_s": atmosphere.speed_of_sound_ft_per_s,
        "air_density_slug_per_ft3": atmosphere.density_slug_per_ft3,
        "air_temperature_rankine": atmosphere.temperature_rankine,
        "air_pressure_lb_per_ft2": atmosphere.pressure_lb_per_ft2,
        "cruise_speed_ft_per_s": cruise_speed,
        "cruise_dynamic_pressure_lb_per_ft2": atmosphere.dynamic_pressure_lb_per_ft2(
            cruise_speed
        ),
        "sfc_cruise_per_s": sfc_cruise,
        "sfc_loiter_per_s": sfc_loiter,
        "cruise_range_ft": inputs.cruise_range_one_way_nm * D.FEET_PER_NAUTICAL_MILE,
        "loiter_on_station_s": inputs.loiter_on_station_endurance_hr * D.SECONDS_PER_HOUR,
        "loiter_prelanding_s": inputs.loiter_prelanding_endurance_min * D.SECONDS_PER_MINUTE,
    }


def segment_ratios(inputs: ASWSizingInputs) -> SegmentRatios:
    dq = derived_quantities(inputs)
    ratios = D.mission_segment_ratios(
        dq["cruise_lift_to_drag"],
        dq["loiter_lift_to_drag"],
        dq["cruise_speed_ft_per_s"],
        dq["sfc_cruise_per_s"],
        dq["sfc_loiter_per_s"],
        dq["cruise_range_ft"],
        dq["loiter_on_station_s"],
        dq["loiter_prelanding_s"],
        inputs.warmup_takeoff_weight_ratio,
        inputs.climb_weight_ratio,
        inputs.landing_weight_ratio,
    )
    return SegmentRatios(*(float(r) for r in ratios))


def mission_fractions(inputs: ASWSizingInputs) -> dict:
    ratios = segment_ratios(inputs)
    mission_weight_fraction = ratios.mission_weight_fraction
    mission_fuel_fraction = 1.0 - mission_weight_fraction
    multiplier = 1.0 + inputs.reserve_fuel_fraction + inputs.trapped_unusable_fuel_fraction
    return {
        "mission_weight_fraction": mission_weight_fraction,
        "mission_fuel_fraction": mission_fuel_fraction,
        "reserve_and_trapped_multiplier": multiplier,
        "fuel_weight_fraction": multiplier * mission_fuel_fraction,
    }


def _fixed_point_history(
    initial_guess, fixed_weight, fuel_weight_fraction, coefficient, exponent, material_factor,
    tolerance, max_iterations,
) -> tuple[IterationStep, ...]:
    """Replay the closed-form fixed-point map for the convergence view.

    This is identical to the iterates a Group ``NonlinearBlockGS`` produces,
    because the fuel weight fraction does not depend on W_TO -- so the only moving
    part is ``We/WTO(W_TO)``.
    """
    steps: list[IterationStep] = []
    guess = float(initial_guess)
    for k in range(1, int(max_iterations) + 1):
        empty_fraction = float(
            D.empty_weight_fraction(guess, coefficient, exponent, material_factor)
        )
        denominator = 1.0 - fuel_weight_fraction - empty_fraction
        if denominator < D.MINIMUM_SIZING_DENOMINATOR:
            # Wf/WTO + We/WTO has reached 1: the next iterate would be negative and
            # ``negative ** -0.07`` is complex.  Stop with a diagnosis instead.
            raise SizingDivergedError(
                f"The sizing fixed point ran away at iteration {k}: "
                f"Wf/WTO = {fuel_weight_fraction:.4f} and We/WTO = {empty_fraction:.4f} "
                f"leave {denominator:.4f} of the aircraft for the fixed weight. "
                "Shorten the mission, cut the fixed weight, or start from a heavier guess."
            )
        updated = fixed_weight / denominator
        difference = updated - guess
        steps.append(
            IterationStep(
                iteration_number=k,
                guess_takeoff_gross_weight_lb=guess,
                fuel_weight_fraction=fuel_weight_fraction,
                empty_weight_fraction=empty_fraction,
                empty_weight_lb=guess * empty_fraction,
                updated_takeoff_gross_weight_lb=updated,
                difference_lb=difference,
            )
        )
        if abs(difference) <= tolerance:
            break
        guess = updated
    return tuple(steps)


# --------------------------------------------------------------------------- #
# Solve
# --------------------------------------------------------------------------- #
def solve(
    inputs: ASWSizingInputs,
    *,
    solver: str = "nlbgs",
    deriv: str = "jax",
    initial_guess: float = 50_000.0,
    convergence_tolerance_lb: float = 1.0,
    max_iterations: int = 100,
    counter: CallCounter | None = None,
) -> ASWSizingResult:
    """Converge the ASW sizing loop and return a flat result.

    ``solver`` selects the Group nonlinear solver ("nlbgs" == the classic Raymer
    fixed point; also "nlbgs_aitken", "newton", "broyden").  ``deriv`` selects
    analytic JAX partials ("jax") or OpenMDAO finite difference ("fd").
    ``max_iterations`` caps the nonlinear solver (and the replayed fixed-point
    history); ``convergence_tolerance_lb`` is the acceptance tolerance on the
    sizing residual ``WTO*(1 - Wf/WTO - We/WTO) - W_fixed``, which is in pounds.

    Raises :class:`SizingDivergedError` when the loop does not close -- a diverged
    solve must never be returned as if it were an answer.
    """
    prob = build_asw_problem(
        inputs.params(),
        inputs.input_values(),
        solver=solver,
        deriv=deriv,
        counter=counter,
        initial_guess=initial_guess,
        maxiter=max_iterations,
    )
    # Broyden's convergence-ratio check divides by a zero residual norm once it
    # converges exactly; ignore that harmless numpy warning.
    try:
        with np.errstate(divide="ignore", invalid="ignore"):
            prob.run_model()
    except om.AnalysisError as error:
        # Past roughly 3,000 nm the baseline genuinely runs away from a light start;
        # below that a non-convergence is almost always just too tight a cap.
        hint = (
            "Fuel plus empty weight consume the whole takeoff weight at this range, so the "
            "iteration runs away from a light start; try a much heavier initial guess."
            if inputs.cruise_range_one_way_nm > 2_800.0
            else "Raise the iteration cap, or start from a different initial guess."
        )
        raise SizingDivergedError(
            f"The {solver} solver did not converge in {max_iterations} iterations for a "
            f"{inputs.cruise_range_one_way_nm:,.0f} nm cruise ({error}). {hint}"
        ) from error

    w_to = float(prob.get_val("sizing.takeoff_gross_weight")[0])
    fuel_fraction = float(prob.get_val("mission.fuel_weight_fraction")[0])
    if not isfinite(w_to) or w_to <= 0.0:
        raise SizingDivergedError(
            f"The {solver} solver produced a non-physical takeoff gross weight "
            f"({w_to!r} lb) for a {inputs.cruise_range_one_way_nm:,.0f} nm cruise, with "
            f"Wf/WTO = {fuel_fraction:.4f}."
        )

    # Re-evaluate We/WTO at the returned W_TO instead of reading the fraction the
    # solver left in ``struct``: under NonlinearBlockGS that stored value is one
    # iterate stale, and since ``Sizing.solve_nonlinear`` inverts the identity with
    # exactly that stale fraction, a residual formed from it is identically zero
    # even for a run that never converged.
    empty_fraction = float(
        D.empty_weight_fraction(
            w_to,
            inputs.empty_weight_fraction_coefficient,
            inputs.empty_weight_fraction_exponent,
            inputs.material_factor,
        )
    )
    residual = w_to * (1.0 - fuel_fraction - empty_fraction) - inputs.fixed_weight_lb
    if not isfinite(residual) or abs(residual) > convergence_tolerance_lb:
        raise SizingDivergedError(
            f"The {solver} solver stopped {abs(residual):,.3f} lb from closing the sizing "
            f"identity WTO*(1 - Wf/WTO - We/WTO) = W_fixed, outside the "
            f"{convergence_tolerance_lb:,.3f} lb tolerance. Raise the iteration cap or the "
            "tolerance, or start from a different initial guess."
        )

    dq = derived_quantities(inputs)
    ratios = segment_ratios(inputs)
    fractions = mission_fractions(inputs)
    history = _fixed_point_history(
        initial_guess,
        inputs.fixed_weight_lb,
        fuel_fraction,
        inputs.empty_weight_fraction_coefficient,
        inputs.empty_weight_fraction_exponent,
        inputs.material_factor,
        convergence_tolerance_lb,
        max_iterations,
    )
    solver_iterations = int(getattr(prob.model.nonlinear_solver, "_iter_count", 0))

    return ASWSizingResult(
        inputs=inputs,
        solver=solver,
        solver_iterations=solver_iterations,
        final_takeoff_gross_weight_lb=w_to,
        final_empty_weight_fraction=empty_fraction,
        final_empty_weight_lb=w_to * empty_fraction,
        fuel_weight_lb=w_to * fuel_fraction,
        fixed_weight_lb=inputs.fixed_weight_lb,
        fuel_weight_fraction=fuel_fraction,
        mission_weight_fraction=fractions["mission_weight_fraction"],
        mission_fuel_fraction=fractions["mission_fuel_fraction"],
        reserve_and_trapped_multiplier=fractions["reserve_and_trapped_multiplier"],
        wetted_aspect_ratio=dq["wetted_aspect_ratio"],
        lift_to_drag_max=dq["lift_to_drag_max"],
        cruise_lift_to_drag=dq["cruise_lift_to_drag"],
        loiter_lift_to_drag=dq["loiter_lift_to_drag"],
        cruise_altitude_ft=dq["cruise_altitude_ft"],
        speed_of_sound_ft_per_s=dq["speed_of_sound_ft_per_s"],
        air_density_slug_per_ft3=dq["air_density_slug_per_ft3"],
        air_temperature_rankine=dq["air_temperature_rankine"],
        air_pressure_lb_per_ft2=dq["air_pressure_lb_per_ft2"],
        cruise_speed_ft_per_s=dq["cruise_speed_ft_per_s"],
        cruise_dynamic_pressure_lb_per_ft2=dq["cruise_dynamic_pressure_lb_per_ft2"],
        sfc_cruise_per_s=dq["sfc_cruise_per_s"],
        sfc_loiter_per_s=dq["sfc_loiter_per_s"],
        cruise_range_ft=dq["cruise_range_ft"],
        loiter_on_station_s=dq["loiter_on_station_s"],
        loiter_prelanding_s=dq["loiter_prelanding_s"],
        segment_ratios=ratios,
        iteration_history=history,
    )


def input_sensitivity_sweep(
    inputs: ASWSizingInputs,
    input_name: str,
    input_values: Iterable[float],
    **solve_kwargs,
) -> tuple[tuple[float, ASWSizingResult], ...]:
    """Vary one input at a time and re-solve, returning ``(value, result)`` pairs."""
    results = []
    for value in input_values:
        result = solve(inputs.with_value(input_name, float(value)), **solve_kwargs)
        results.append((float(value), result))
    return tuple(results)


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def _positive(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be a positive, finite number; got {value!r}.")


def _fraction(name: str, value: float) -> None:
    if not (isinstance(value, (int, float)) and 0.0 < float(value) <= 1.0):
        raise ValueError(f"{name} must satisfy 0 < value <= 1; got {value!r}.")


def _validate_inputs(inputs: ASWSizingInputs) -> None:
    for name in (
        "cruise_range_one_way_nm",
        "cruise_mach_number",
        "loiter_on_station_endurance_hr",
        "loiter_prelanding_endurance_min",
        "cruise_thrust_specific_fuel_consumption_lb_per_hr_per_lb",
        "loiter_thrust_specific_fuel_consumption_lb_per_hr_per_lb",
        "wing_aspect_ratio",
        "wetted_area_ratio_s_wet_over_s_ref",
        "lift_to_drag_max_k_factor",
        "empty_weight_fraction_coefficient",
    ):
        _positive(name, getattr(inputs, name))
    # Altitude may legitimately be zero or negative (Dead Sea airfields), so it is
    # range-checked against the standard atmosphere rather than required positive.
    standard_atmosphere(inputs.cruise_altitude_ft)
    for name in ("warmup_takeoff_weight_ratio", "climb_weight_ratio", "landing_weight_ratio", "cruise_lift_to_drag_factor"):
        _fraction(name, getattr(inputs, name))
    if inputs.mission_equipment_weight_lb < 0 or inputs.crew_weight_lb < 0:
        raise ValueError("Equipment and crew weights must be non-negative.")
    if inputs.fixed_weight_lb <= 0:
        raise ValueError("mission_equipment_weight_lb + crew_weight_lb must be > 0.")
    if inputs.structure_material not in ("metal", "composite"):
        raise ValueError(f"structure_material must be 'metal' or 'composite'; got {inputs.structure_material!r}.")
