"""Dependency-free ASW conceptual-sizing kernel.

This module mirrors the fixed-point tutorial in ``ex_05_asw_sizing.md`` while exposing
typed, testable building blocks for mission fractions, empty-weight fraction, full
iteration history, and one-at-a-time input sensitivity sweeps.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from math import exp, isfinite
from typing import Iterable

__all__ = [
    "ASWSizingInputs",
    "FixedPointIterationSettings",
    "DerivedCruiseAerodynamicQuantities",
    "MissionSegmentRatios",
    "MissionFuelFractions",
    "IterationStep",
    "ASWSizingSolution",
    "InputSensitivityResult",
    "make_baseline_asw_sizing_inputs",
    "make_baseline_fixed_point_iteration_settings",
    "derive_cruise_aerodynamic_quantities",
    "compute_breguet_range_weight_ratio",
    "compute_breguet_endurance_weight_ratio",
    "compute_mission_segment_ratios",
    "compute_mission_and_fuel_fractions",
    "compute_empty_weight_fraction",
    "solve_asw_togw",
    "run_one_at_a_time_input_sensitivity_sweep",
]

_FEET_PER_NAUTICAL_MILE = 6076.0
_SECONDS_PER_HOUR = 3600.0
_SECONDS_PER_MINUTE = 60.0


def _as_real(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number; received {value!r}.")
    value = float(value)
    if not isfinite(value):
        raise ValueError(f"{name} must be finite; received {value!r}.")
    return value


def _require_positive(name: str, value: float, units: str) -> float:
    value = _as_real(name, value)
    if value <= 0.0:
        raise ValueError(f"{name} must be > 0 {units}; received {value} {units}.")
    return value


def _require_nonnegative(name: str, value: float, units: str) -> float:
    value = _as_real(name, value)
    if value < 0.0:
        raise ValueError(f"{name} must be >= 0 {units}; received {value} {units}.")
    return value


def _require_fraction_zero_to_one(name: str, value: float) -> float:
    value = _as_real(name, value)
    if not 0.0 < value <= 1.0:
        raise ValueError(f"{name} must satisfy 0 < value <= 1; received {value}.")
    return value


def _require_iteration_count(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer; received {value!r}.")
    if value <= 0:
        raise ValueError(f"{name} must be >= 1; received {value}.")
    return value


@dataclass(frozen=True, slots=True)
class ASWSizingInputs:
    """User-facing ASW sizing assumptions from the worked example."""

    cruise_range_one_way_nm: float = 1500.0
    cruise_mach_number: float = 0.6
    cruise_altitude_ft: float = 30_000.0
    speed_of_sound_at_cruise_altitude_ft_per_s: float = 994.8
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
    lift_to_drag_max: float = 16.0
    cruise_lift_to_drag_factor: float = 0.866
    reserve_fuel_fraction: float = 0.05
    trapped_unusable_fuel_fraction: float = 0.01
    empty_weight_fraction_coefficient: float = 0.93
    empty_weight_fraction_exponent: float = -0.07

    def __post_init__(self) -> None:
        _require_positive("cruise_range_one_way_nm", self.cruise_range_one_way_nm, "nm")
        _require_positive("cruise_mach_number", self.cruise_mach_number, "Mach")
        _require_nonnegative("cruise_altitude_ft", self.cruise_altitude_ft, "ft")
        _require_positive(
            "speed_of_sound_at_cruise_altitude_ft_per_s",
            self.speed_of_sound_at_cruise_altitude_ft_per_s,
            "ft/s",
        )
        _require_nonnegative("mission_equipment_weight_lb", self.mission_equipment_weight_lb, "lb")
        _require_nonnegative("crew_weight_lb", self.crew_weight_lb, "lb")
        if self.mission_equipment_weight_lb + self.crew_weight_lb <= 0.0:
            raise ValueError(
                "mission_equipment_weight_lb + crew_weight_lb must be > 0 lb; "
                f"received {self.mission_equipment_weight_lb + self.crew_weight_lb} lb."
            )
        _require_fraction_zero_to_one("warmup_takeoff_weight_ratio", self.warmup_takeoff_weight_ratio)
        _require_fraction_zero_to_one("climb_weight_ratio", self.climb_weight_ratio)
        _require_fraction_zero_to_one("landing_weight_ratio", self.landing_weight_ratio)
        _require_positive("loiter_on_station_endurance_hr", self.loiter_on_station_endurance_hr, "hr")
        _require_positive(
            "loiter_prelanding_endurance_min", self.loiter_prelanding_endurance_min, "min"
        )
        _require_positive(
            "cruise_thrust_specific_fuel_consumption_lb_per_hr_per_lb",
            self.cruise_thrust_specific_fuel_consumption_lb_per_hr_per_lb,
            "lb/hr/lb",
        )
        _require_positive(
            "loiter_thrust_specific_fuel_consumption_lb_per_hr_per_lb",
            self.loiter_thrust_specific_fuel_consumption_lb_per_hr_per_lb,
            "lb/hr/lb",
        )
        _require_positive("wing_aspect_ratio", self.wing_aspect_ratio, "unitless")
        _require_positive(
            "wetted_area_ratio_s_wet_over_s_ref",
            self.wetted_area_ratio_s_wet_over_s_ref,
            "unitless",
        )
        _require_positive("lift_to_drag_max", self.lift_to_drag_max, "unitless")
        _require_fraction_zero_to_one("cruise_lift_to_drag_factor", self.cruise_lift_to_drag_factor)
        _require_nonnegative("reserve_fuel_fraction", self.reserve_fuel_fraction, "unitless")
        _require_nonnegative(
            "trapped_unusable_fuel_fraction", self.trapped_unusable_fuel_fraction, "unitless"
        )
        _require_positive(
            "empty_weight_fraction_coefficient", self.empty_weight_fraction_coefficient, "unitless"
        )
        _as_real("empty_weight_fraction_exponent", self.empty_weight_fraction_exponent)


@dataclass(frozen=True, slots=True)
class FixedPointIterationSettings:
    """Iteration controls for the fixed-point TOGW solve."""

    initial_takeoff_gross_weight_guess_lb: float = 50_000.0
    convergence_tolerance_lb: float = 1.0
    maximum_iterations: int = 100

    def __post_init__(self) -> None:
        _require_positive(
            "initial_takeoff_gross_weight_guess_lb",
            self.initial_takeoff_gross_weight_guess_lb,
            "lb",
        )
        _require_positive("convergence_tolerance_lb", self.convergence_tolerance_lb, "lb")
        _require_iteration_count("maximum_iterations", self.maximum_iterations)


@dataclass(frozen=True, slots=True)
class DerivedCruiseAerodynamicQuantities:
    """Derived cruise and aerodynamic quantities used by the mission model."""

    fixed_weight_lb: float
    cruise_range_one_way_ft: float
    loiter_on_station_endurance_s: float
    loiter_prelanding_endurance_s: float
    cruise_speed_ft_per_s: float
    cruise_thrust_specific_fuel_consumption_lb_per_s_per_lb: float
    loiter_thrust_specific_fuel_consumption_lb_per_s_per_lb: float
    wetted_aspect_ratio: float
    cruise_lift_to_drag: float
    loiter_lift_to_drag: float


@dataclass(frozen=True, slots=True)
class MissionSegmentRatios:
    """Individual mission-segment weight ratios for the 1→8 mission profile."""

    warmup_takeoff_weight_ratio_w2_over_w1: float
    climb_weight_ratio_w3_over_w2: float
    outbound_cruise_weight_ratio_w4_over_w3: float
    on_station_loiter_weight_ratio_w5_over_w4: float
    return_cruise_weight_ratio_w6_over_w5: float
    prelanding_loiter_weight_ratio_w7_over_w6: float
    landing_weight_ratio_w8_over_w7: float


@dataclass(frozen=True, slots=True)
class MissionFuelFractions:
    """Mission and fuel fractions derived from the segment ratios."""

    mission_weight_fraction_w8_over_w1: float
    mission_fuel_fraction: float
    reserve_and_trapped_fuel_multiplier: float
    fuel_weight_fraction_wf_over_wto: float


@dataclass(frozen=True, slots=True)
class IterationStep:
    """One fixed-point TOGW iteration entry."""

    iteration_number: int
    guess_takeoff_gross_weight_lb: float
    fixed_weight_lb: float
    fuel_weight_fraction_wf_over_wto: float
    empty_weight_fraction_we_over_wto: float
    empty_weight_lb: float
    updated_takeoff_gross_weight_lb: float
    difference_lb: float


@dataclass(frozen=True, slots=True)
class ASWSizingSolution:
    """Complete solved state for the ASW sizing problem."""

    inputs: ASWSizingInputs
    settings: FixedPointIterationSettings
    derived_quantities: DerivedCruiseAerodynamicQuantities
    segment_ratios: MissionSegmentRatios
    mission_fractions: MissionFuelFractions
    iteration_history: tuple[IterationStep, ...]
    final_takeoff_gross_weight_lb: float
    final_empty_weight_fraction_we_over_wto: float
    final_empty_weight_lb: float

    @property
    def iteration_count(self) -> int:
        return len(self.iteration_history)


@dataclass(frozen=True, slots=True)
class InputSensitivityResult:
    """Result from rerunning the full solve after changing one input value."""

    input_name: str
    input_value: float
    final_takeoff_gross_weight_lb: float
    solution: ASWSizingSolution


def make_baseline_asw_sizing_inputs() -> ASWSizingInputs:
    """Return the worked-example ASW sizing inputs."""

    return ASWSizingInputs()


def make_baseline_fixed_point_iteration_settings() -> FixedPointIterationSettings:
    """Return the worked-example fixed-point iteration settings."""

    return FixedPointIterationSettings()


def derive_cruise_aerodynamic_quantities(
    inputs: ASWSizingInputs,
) -> DerivedCruiseAerodynamicQuantities:
    """Convert visible inputs into the cruise and aerodynamic quantities used by the solver."""

    return DerivedCruiseAerodynamicQuantities(
        fixed_weight_lb=inputs.mission_equipment_weight_lb + inputs.crew_weight_lb,
        cruise_range_one_way_ft=inputs.cruise_range_one_way_nm * _FEET_PER_NAUTICAL_MILE,
        loiter_on_station_endurance_s=inputs.loiter_on_station_endurance_hr * _SECONDS_PER_HOUR,
        loiter_prelanding_endurance_s=inputs.loiter_prelanding_endurance_min * _SECONDS_PER_MINUTE,
        cruise_speed_ft_per_s=inputs.cruise_mach_number * inputs.speed_of_sound_at_cruise_altitude_ft_per_s,
        cruise_thrust_specific_fuel_consumption_lb_per_s_per_lb=(
            inputs.cruise_thrust_specific_fuel_consumption_lb_per_hr_per_lb / _SECONDS_PER_HOUR
        ),
        loiter_thrust_specific_fuel_consumption_lb_per_s_per_lb=(
            inputs.loiter_thrust_specific_fuel_consumption_lb_per_hr_per_lb / _SECONDS_PER_HOUR
        ),
        wetted_aspect_ratio=inputs.wing_aspect_ratio / inputs.wetted_area_ratio_s_wet_over_s_ref,
        cruise_lift_to_drag=inputs.cruise_lift_to_drag_factor * inputs.lift_to_drag_max,
        loiter_lift_to_drag=inputs.lift_to_drag_max,
    )


def compute_breguet_range_weight_ratio(
    range_ft: float,
    thrust_specific_fuel_consumption_lb_per_s_per_lb: float,
    speed_ft_per_s: float,
    lift_to_drag: float,
) -> float:
    """Return a cruise-segment weight ratio from the Breguet range equation."""

    range_ft = _require_positive("range_ft", range_ft, "ft")
    thrust_specific_fuel_consumption_lb_per_s_per_lb = _require_positive(
        "thrust_specific_fuel_consumption_lb_per_s_per_lb",
        thrust_specific_fuel_consumption_lb_per_s_per_lb,
        "lb/s/lb",
    )
    speed_ft_per_s = _require_positive("speed_ft_per_s", speed_ft_per_s, "ft/s")
    lift_to_drag = _require_positive("lift_to_drag", lift_to_drag, "unitless")
    return exp(-(range_ft * thrust_specific_fuel_consumption_lb_per_s_per_lb) / (speed_ft_per_s * lift_to_drag))


def compute_breguet_endurance_weight_ratio(
    endurance_s: float,
    thrust_specific_fuel_consumption_lb_per_s_per_lb: float,
    lift_to_drag: float,
) -> float:
    """Return a loiter-segment weight ratio from the Breguet endurance equation."""

    endurance_s = _require_positive("endurance_s", endurance_s, "s")
    thrust_specific_fuel_consumption_lb_per_s_per_lb = _require_positive(
        "thrust_specific_fuel_consumption_lb_per_s_per_lb",
        thrust_specific_fuel_consumption_lb_per_s_per_lb,
        "lb/s/lb",
    )
    lift_to_drag = _require_positive("lift_to_drag", lift_to_drag, "unitless")
    return exp(-(endurance_s * thrust_specific_fuel_consumption_lb_per_s_per_lb) / lift_to_drag)


def compute_mission_segment_ratios(
    inputs: ASWSizingInputs,
    derived_quantities: DerivedCruiseAerodynamicQuantities | None = None,
) -> MissionSegmentRatios:
    """Compute the seven explicit segment ratios used in the tutorial mission profile."""

    derived_quantities = derived_quantities or derive_cruise_aerodynamic_quantities(inputs)
    cruise_ratio = compute_breguet_range_weight_ratio(
        range_ft=derived_quantities.cruise_range_one_way_ft,
        thrust_specific_fuel_consumption_lb_per_s_per_lb=(
            derived_quantities.cruise_thrust_specific_fuel_consumption_lb_per_s_per_lb
        ),
        speed_ft_per_s=derived_quantities.cruise_speed_ft_per_s,
        lift_to_drag=derived_quantities.cruise_lift_to_drag,
    )
    on_station_loiter_ratio = compute_breguet_endurance_weight_ratio(
        endurance_s=derived_quantities.loiter_on_station_endurance_s,
        thrust_specific_fuel_consumption_lb_per_s_per_lb=(
            derived_quantities.loiter_thrust_specific_fuel_consumption_lb_per_s_per_lb
        ),
        lift_to_drag=derived_quantities.loiter_lift_to_drag,
    )
    prelanding_loiter_ratio = compute_breguet_endurance_weight_ratio(
        endurance_s=derived_quantities.loiter_prelanding_endurance_s,
        thrust_specific_fuel_consumption_lb_per_s_per_lb=(
            derived_quantities.loiter_thrust_specific_fuel_consumption_lb_per_s_per_lb
        ),
        lift_to_drag=derived_quantities.loiter_lift_to_drag,
    )
    return MissionSegmentRatios(
        warmup_takeoff_weight_ratio_w2_over_w1=inputs.warmup_takeoff_weight_ratio,
        climb_weight_ratio_w3_over_w2=inputs.climb_weight_ratio,
        outbound_cruise_weight_ratio_w4_over_w3=cruise_ratio,
        on_station_loiter_weight_ratio_w5_over_w4=on_station_loiter_ratio,
        return_cruise_weight_ratio_w6_over_w5=cruise_ratio,
        prelanding_loiter_weight_ratio_w7_over_w6=prelanding_loiter_ratio,
        landing_weight_ratio_w8_over_w7=inputs.landing_weight_ratio,
    )


def compute_mission_and_fuel_fractions(
    segment_ratios: MissionSegmentRatios,
    inputs: ASWSizingInputs,
) -> MissionFuelFractions:
    """Collapse segment ratios into mission and fuel fractions."""

    for ratio_field in fields(MissionSegmentRatios):
        _require_fraction_zero_to_one(
            ratio_field.name,
            getattr(segment_ratios, ratio_field.name),
        )
    mission_weight_fraction_w8_over_w1 = (
        segment_ratios.warmup_takeoff_weight_ratio_w2_over_w1
        * segment_ratios.climb_weight_ratio_w3_over_w2
        * segment_ratios.outbound_cruise_weight_ratio_w4_over_w3
        * segment_ratios.on_station_loiter_weight_ratio_w5_over_w4
        * segment_ratios.return_cruise_weight_ratio_w6_over_w5
        * segment_ratios.prelanding_loiter_weight_ratio_w7_over_w6
        * segment_ratios.landing_weight_ratio_w8_over_w7
    )
    mission_fuel_fraction = 1.0 - mission_weight_fraction_w8_over_w1
    reserve_and_trapped_fuel_multiplier = (
        1.0 + inputs.reserve_fuel_fraction + inputs.trapped_unusable_fuel_fraction
    )
    fuel_weight_fraction_wf_over_wto = reserve_and_trapped_fuel_multiplier * mission_fuel_fraction
    if fuel_weight_fraction_wf_over_wto >= 1.0:
        raise ValueError(
            "fuel_weight_fraction_wf_over_wto must be < 1; "
            f"received {fuel_weight_fraction_wf_over_wto}."
        )
    return MissionFuelFractions(
        mission_weight_fraction_w8_over_w1=mission_weight_fraction_w8_over_w1,
        mission_fuel_fraction=mission_fuel_fraction,
        reserve_and_trapped_fuel_multiplier=reserve_and_trapped_fuel_multiplier,
        fuel_weight_fraction_wf_over_wto=fuel_weight_fraction_wf_over_wto,
    )


def compute_empty_weight_fraction(
    takeoff_gross_weight_lb: float,
    inputs: ASWSizingInputs,
) -> float:
    """Evaluate the empty-weight fraction regression, returning We/WTO."""

    takeoff_gross_weight_lb = _require_positive(
        "takeoff_gross_weight_lb", takeoff_gross_weight_lb, "lb"
    )
    empty_weight_fraction = (
        inputs.empty_weight_fraction_coefficient
        * takeoff_gross_weight_lb ** inputs.empty_weight_fraction_exponent
    )
    if not 0.0 < empty_weight_fraction < 1.0:
        raise ValueError(
            "Empty-weight regression must return 0 < We/WTO < 1; "
            f"received {empty_weight_fraction} at takeoff_gross_weight_lb="
            f"{takeoff_gross_weight_lb}."
        )
    return empty_weight_fraction


def solve_asw_togw(
    inputs: ASWSizingInputs,
    settings: FixedPointIterationSettings | None = None,
) -> ASWSizingSolution:
    """Run the tutorial fixed-point iteration to final takeoff gross weight."""

    settings = settings or FixedPointIterationSettings()
    derived_quantities = derive_cruise_aerodynamic_quantities(inputs)
    segment_ratios = compute_mission_segment_ratios(inputs, derived_quantities)
    mission_fractions = compute_mission_and_fuel_fractions(segment_ratios, inputs)

    history: list[IterationStep] = []
    current_guess_lb = settings.initial_takeoff_gross_weight_guess_lb
    for iteration_number in range(1, settings.maximum_iterations + 1):
        empty_weight_fraction_we_over_wto = compute_empty_weight_fraction(current_guess_lb, inputs)
        denominator = (
            1.0
            - mission_fractions.fuel_weight_fraction_wf_over_wto
            - empty_weight_fraction_we_over_wto
        )
        if denominator <= 0.0:
            raise ValueError(
                "Sizing denominator became non-positive during iteration: "
                "1 - fuel_weight_fraction_wf_over_wto - empty_weight_fraction_we_over_wto "
                f"= {denominator} at takeoff_gross_weight_lb={current_guess_lb}."
            )
        updated_takeoff_gross_weight_lb = derived_quantities.fixed_weight_lb / denominator
        difference_lb = updated_takeoff_gross_weight_lb - current_guess_lb
        history.append(
            IterationStep(
                iteration_number=iteration_number,
                guess_takeoff_gross_weight_lb=current_guess_lb,
                fixed_weight_lb=derived_quantities.fixed_weight_lb,
                fuel_weight_fraction_wf_over_wto=mission_fractions.fuel_weight_fraction_wf_over_wto,
                empty_weight_fraction_we_over_wto=empty_weight_fraction_we_over_wto,
                empty_weight_lb=current_guess_lb * empty_weight_fraction_we_over_wto,
                updated_takeoff_gross_weight_lb=updated_takeoff_gross_weight_lb,
                difference_lb=difference_lb,
            )
        )
        if abs(difference_lb) <= settings.convergence_tolerance_lb:
            final_takeoff_gross_weight_lb = updated_takeoff_gross_weight_lb
            final_empty_weight_fraction_we_over_wto = compute_empty_weight_fraction(
                final_takeoff_gross_weight_lb, inputs
            )
            return ASWSizingSolution(
                inputs=inputs,
                settings=settings,
                derived_quantities=derived_quantities,
                segment_ratios=segment_ratios,
                mission_fractions=mission_fractions,
                iteration_history=tuple(history),
                final_takeoff_gross_weight_lb=final_takeoff_gross_weight_lb,
                final_empty_weight_fraction_we_over_wto=final_empty_weight_fraction_we_over_wto,
                final_empty_weight_lb=(
                    final_takeoff_gross_weight_lb * final_empty_weight_fraction_we_over_wto
                ),
            )
        current_guess_lb = updated_takeoff_gross_weight_lb

    raise RuntimeError(
        "Fixed-point iteration did not converge within "
        f"{settings.maximum_iterations} iterations."
    )


def run_one_at_a_time_input_sensitivity_sweep(
    inputs: ASWSizingInputs,
    input_name: str,
    input_values: Iterable[float],
    settings: FixedPointIterationSettings | None = None,
) -> tuple[InputSensitivityResult, ...]:
    """Vary one ASW sizing input at a time and rerun the full TOGW solve for each value."""

    if input_name not in {field.name for field in fields(ASWSizingInputs)}:
        raise ValueError(
            f"input_name must be one of {[field.name for field in fields(ASWSizingInputs)]}; "
            f"received {input_name!r}."
        )

    settings = settings or FixedPointIterationSettings()
    results: list[InputSensitivityResult] = []
    for input_value in input_values:
        updated_inputs = replace(inputs, **{input_name: input_value})
        solution = solve_asw_togw(updated_inputs, settings)
        results.append(
            InputSensitivityResult(
                input_name=input_name,
                input_value=float(input_value),
                final_takeoff_gross_weight_lb=solution.final_takeoff_gross_weight_lb,
                solution=solution,
            )
        )
    return tuple(results)
