"""Streamlit-native visualization layer for the ASW fixed-point sizing tutorial."""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st

from aircraft_sizing.examples.ex_05_asw.methods.sizing import (
    ASWSizingInputs,
    ASWSizingSolution,
    FixedPointIterationSettings,
    InputSensitivityResult,
    IterationStep,
    make_baseline_asw_sizing_inputs,
    make_baseline_fixed_point_iteration_settings,
    solve_asw_togw,
)

__all__ = ["render"]

_INITIALIZED_KEY = "asw_streamlit_initialized"
_APPLIED_STATE_KEY = "asw_streamlit_applied_state"
_LAST_SOLUTION_KEY = "asw_streamlit_last_solution"
_LAST_SENSITIVITY_KEY = "asw_streamlit_last_sensitivity"
_STATUS_MESSAGE_KEY = "asw_streamlit_status_message"
_STATUS_KIND_KEY = "asw_streamlit_status_kind"
_LAST_ERROR_KEY = "asw_streamlit_last_error"
_SOLUTION_STABILITY_TOLERANCE_LB = 1e-6


@dataclass(frozen=True, slots=True)
class _FieldSpec:
    name: str
    label: str
    units: str
    step: float
    sensitivity_min: float | None = None
    sensitivity_max: float | None = None
    slider_min: float | None = None
    slider_max: float | None = None

    @property
    def is_slider(self) -> bool:
        """Render as a slider when an explicit min/max range is provided."""

        return self.slider_min is not None and self.slider_max is not None


@dataclass(frozen=True, slots=True)
class _SensitivitySweepSettings:
    input_name: str = "cruise_range_one_way_nm"
    relative_span_fraction: float = 0.10
    sample_count: int = 9

    def __post_init__(self) -> None:
        valid_input_names = {field.name for field in fields(ASWSizingInputs)}
        if self.input_name not in valid_input_names:
            raise ValueError(
                f"input_name must be one of {sorted(valid_input_names)}; received {self.input_name!r}."
            )
        if self.relative_span_fraction <= 0.0:
            raise ValueError(
                "relative_span_fraction must be > 0; "
                f"received {self.relative_span_fraction}."
            )
        if self.sample_count < 3:
            raise ValueError(f"sample_count must be >= 3; received {self.sample_count}.")


@dataclass(frozen=True, slots=True)
class _PageState:
    inputs: ASWSizingInputs
    settings: FixedPointIterationSettings
    sensitivity: _SensitivitySweepSettings


def _make_baseline_page_state() -> _PageState:
    return _PageState(
        inputs=make_baseline_asw_sizing_inputs(),
        settings=make_baseline_fixed_point_iteration_settings(),
        sensitivity=_SensitivitySweepSettings(),
    )


# Only the inputs students actually drive are widgets. Everything else (cruise
# Mach, altitude, speed of sound, crew weight, prelanding loiter, the historical
# segment ratios, K_LD, the L/D factors, and the fuel/empty-weight allowances)
# stays fixed at the Raymer 3.6 baseline defined in the kernel.
_INPUT_GROUPS: tuple[tuple[str, tuple[_FieldSpec, ...]], ...] = (
    (
        "Mission",
        (
            _FieldSpec("cruise_range_one_way_nm", "One-way cruise range", "nm", 25.0, 1e-6, slider_min=500.0, slider_max=3_000.0),
            _FieldSpec("mission_equipment_weight_lb", "Mission equipment weight", "lb", 250.0, 0.0, slider_min=0.0, slider_max=30_000.0),
            _FieldSpec("loiter_on_station_endurance_hr", "On-station loiter endurance", "hr", 0.1, 1e-6, slider_min=0.5, slider_max=10.0),
        ),
    ),
    (
        "Propulsion",
        (
            _FieldSpec(
                "cruise_thrust_specific_fuel_consumption_lb_per_hr_per_lb",
                "Cruise TSFC",
                "lb/hr/lb",
                0.01,
                1e-6,
            ),
            _FieldSpec(
                "loiter_thrust_specific_fuel_consumption_lb_per_hr_per_lb",
                "Loiter TSFC",
                "lb/hr/lb",
                0.01,
                1e-6,
            ),
        ),
    ),
    (
        "Aerodynamics",
        (
            _FieldSpec("wing_aspect_ratio", "Wing aspect ratio", "unitless", 0.1, 1e-6),
            _FieldSpec(
                "wetted_area_ratio_s_wet_over_s_ref",
                "Wetted-area ratio S_wet/S_ref",
                "unitless",
                0.1,
                1e-6,
            ),
        ),
    ),
)

_INPUT_SPECS = {
    field_spec.name: field_spec
    for _, group_specs in _INPUT_GROUPS
    for field_spec in group_specs
}

# The one-at-a-time sweep is restricted to the four most instructive inputs.
_SWEEP_INPUT_NAMES: tuple[str, ...] = (
    "cruise_range_one_way_nm",
    "mission_equipment_weight_lb",
    "wing_aspect_ratio",
    "cruise_thrust_specific_fuel_consumption_lb_per_hr_per_lb",
)

_MATERIAL_KEY = "structure_material"
_MATERIAL_OPTIONS: tuple[str, ...] = ("metal", "composite")

_SETTING_SPECS: tuple[_FieldSpec, ...] = (
    _FieldSpec("initial_takeoff_gross_weight_guess_lb", "Initial TOGW guess", "lb", 500.0, 1e-6),
    _FieldSpec("convergence_tolerance_lb", "Convergence tolerance", "lb", 0.1, 1e-6),
)


def _widget_key(name: str) -> str:
    return f"asw_streamlit_{name}"


def _format_number(value: float, digits: int = 1) -> str:
    return f"{value:,.{digits}f}"


def _format_fraction(value: float, digits: int = 4) -> str:
    return f"{value:.{digits}f}"


def _format_percent(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}%}"


def _format_from_step(step: float) -> str:
    step_text = f"{step:.10f}".rstrip("0")
    if "." not in step_text:
        return "%.0f"
    decimals = len(step_text.split(".")[1])
    return f"%.{decimals}f"


def _field_label(field_spec: _FieldSpec) -> str:
    return f"{field_spec.label} [{field_spec.units}]"


def _set_form_state(state: _PageState) -> None:
    for field_spec in _INPUT_SPECS.values():
        st.session_state[_widget_key(field_spec.name)] = float(getattr(state.inputs, field_spec.name))
    st.session_state[_widget_key(_MATERIAL_KEY)] = state.inputs.structure_material
    st.session_state[_widget_key("initial_takeoff_gross_weight_guess_lb")] = float(
        state.settings.initial_takeoff_gross_weight_guess_lb
    )
    st.session_state[_widget_key("convergence_tolerance_lb")] = float(
        state.settings.convergence_tolerance_lb
    )
    st.session_state[_widget_key("maximum_iterations")] = int(state.settings.maximum_iterations)
    st.session_state[_widget_key("sensitivity_input_name")] = state.sensitivity.input_name
    st.session_state[_widget_key("sensitivity_relative_span_fraction")] = float(
        state.sensitivity.relative_span_fraction
    )
    st.session_state[_widget_key("sensitivity_sample_count")] = int(state.sensitivity.sample_count)


def _read_form_state() -> _PageState:
    # Start from the fixed Raymer 3.6 baseline and override only the widget-backed
    # inputs plus the material choice; every other assumption stays at its default.
    widget_values = {
        field_name: float(st.session_state[_widget_key(field_name)])
        for field_name in _INPUT_SPECS
    }
    inputs = replace(
        make_baseline_asw_sizing_inputs(),
        structure_material=str(st.session_state[_widget_key(_MATERIAL_KEY)]),
        **widget_values,
    )
    settings = FixedPointIterationSettings(
        initial_takeoff_gross_weight_guess_lb=float(
            st.session_state[_widget_key("initial_takeoff_gross_weight_guess_lb")]
        ),
        convergence_tolerance_lb=float(st.session_state[_widget_key("convergence_tolerance_lb")]),
        maximum_iterations=int(st.session_state[_widget_key("maximum_iterations")]),
    )
    sensitivity = _SensitivitySweepSettings(
        input_name=str(st.session_state[_widget_key("sensitivity_input_name")]),
        relative_span_fraction=float(
            st.session_state[_widget_key("sensitivity_relative_span_fraction")]
        ),
        sample_count=int(st.session_state[_widget_key("sensitivity_sample_count")]),
    )
    return _PageState(inputs=inputs, settings=settings, sensitivity=sensitivity)


def _build_sensitivity_values(state: _PageState) -> tuple[float, ...]:
    field_spec = _INPUT_SPECS[state.sensitivity.input_name]
    center_value = float(getattr(state.inputs, state.sensitivity.input_name))
    if center_value == 0.0:
        low_value = -state.sensitivity.relative_span_fraction
        high_value = state.sensitivity.relative_span_fraction
    else:
        low_value = center_value * (1.0 - state.sensitivity.relative_span_fraction)
        high_value = center_value * (1.0 + state.sensitivity.relative_span_fraction)
    low_value, high_value = sorted((low_value, high_value))

    if field_spec.sensitivity_min is not None:
        low_value = max(low_value, field_spec.sensitivity_min)
        high_value = max(high_value, field_spec.sensitivity_min)
    if field_spec.sensitivity_max is not None:
        low_value = min(low_value, field_spec.sensitivity_max)
        high_value = min(high_value, field_spec.sensitivity_max)

    if high_value <= low_value:
        delta = max(
            abs(center_value) * state.sensitivity.relative_span_fraction,
            field_spec.step,
            1e-6,
        )
        low_value = center_value - delta
        high_value = center_value + delta
        low_value, high_value = sorted((low_value, high_value))
        if field_spec.sensitivity_min is not None:
            low_value = max(low_value, field_spec.sensitivity_min)
            high_value = max(high_value, field_spec.sensitivity_min)
        if field_spec.sensitivity_max is not None:
            low_value = min(low_value, field_spec.sensitivity_max)
            high_value = min(high_value, field_spec.sensitivity_max)

    spacing = (high_value - low_value) / (state.sensitivity.sample_count - 1)
    raw_values = [low_value + spacing * index for index in range(state.sensitivity.sample_count)]

    unique_values: list[float] = []
    for value in raw_values:
        if not unique_values or abs(value - unique_values[-1]) > 1e-12:
            unique_values.append(value)

    if len(unique_values) < 3:
        unique_values = [center_value - field_spec.step, center_value, center_value + field_spec.step]
        if field_spec.sensitivity_min is not None:
            unique_values = [max(value, field_spec.sensitivity_min) for value in unique_values]
        if field_spec.sensitivity_max is not None:
            unique_values = [min(value, field_spec.sensitivity_max) for value in unique_values]

    return tuple(unique_values)


def _renumber_iteration_step(step: IterationStep, iteration_number: int) -> IterationStep:
    return IterationStep(
        iteration_number=iteration_number,
        guess_takeoff_gross_weight_lb=step.guess_takeoff_gross_weight_lb,
        fixed_weight_lb=step.fixed_weight_lb,
        fuel_weight_fraction_wf_over_wto=step.fuel_weight_fraction_wf_over_wto,
        empty_weight_fraction_we_over_wto=step.empty_weight_fraction_we_over_wto,
        empty_weight_lb=step.empty_weight_lb,
        updated_takeoff_gross_weight_lb=step.updated_takeoff_gross_weight_lb,
        difference_lb=step.difference_lb,
    )


def _solve_stable_asw_togw(
    inputs: ASWSizingInputs,
    settings: FixedPointIterationSettings,
) -> ASWSizingSolution:
    solution = solve_asw_togw(inputs, settings)
    iteration_history = list(solution.iteration_history)
    current_solution = solution

    while len(iteration_history) < settings.maximum_iterations:
        stabilized_settings = replace(
            settings,
            initial_takeoff_gross_weight_guess_lb=current_solution.final_takeoff_gross_weight_lb,
            maximum_iterations=settings.maximum_iterations - len(iteration_history),
        )
        stabilized_solution = solve_asw_togw(inputs, stabilized_settings)
        for step in stabilized_solution.iteration_history:
            iteration_history.append(_renumber_iteration_step(step, len(iteration_history) + 1))
        current_solution = stabilized_solution
        if (
            abs(
                current_solution.final_takeoff_gross_weight_lb
                - solution.final_takeoff_gross_weight_lb
            )
            <= _SOLUTION_STABILITY_TOLERANCE_LB
        ):
            break
        solution = current_solution

    if len(iteration_history) == len(current_solution.iteration_history):
        return current_solution

    return ASWSizingSolution(
        inputs=current_solution.inputs,
        settings=settings,
        derived_quantities=current_solution.derived_quantities,
        segment_ratios=current_solution.segment_ratios,
        mission_fractions=current_solution.mission_fractions,
        iteration_history=tuple(iteration_history),
        final_takeoff_gross_weight_lb=current_solution.final_takeoff_gross_weight_lb,
        final_empty_weight_fraction_we_over_wto=(
            current_solution.final_empty_weight_fraction_we_over_wto
        ),
        final_empty_weight_lb=current_solution.final_empty_weight_lb,
    )


def _run_stable_input_sensitivity_sweep(
    state: _PageState,
) -> tuple[tuple[InputSensitivityResult, ...], int]:
    """Run the one-at-a-time sweep, skipping any sample that fails to solve.

    Returns the successful results plus the count of skipped (out-of-range)
    samples, so a single invalid sweep point no longer discards the whole
    recompute.
    """
    results: list[InputSensitivityResult] = []
    skipped_count = 0
    for input_value in _build_sensitivity_values(state):
        updated_inputs = replace(state.inputs, **{state.sensitivity.input_name: input_value})
        try:
            solution = _solve_stable_asw_togw(updated_inputs, state.settings)
        except (ValueError, RuntimeError):
            skipped_count += 1
            continue
        results.append(
            InputSensitivityResult(
                input_name=state.sensitivity.input_name,
                input_value=float(input_value),
                final_takeoff_gross_weight_lb=solution.final_takeoff_gross_weight_lb,
                solution=solution,
            )
        )
    return tuple(results), skipped_count


def _apply_state(state: _PageState, success_message: str) -> None:
    try:
        solution = _solve_stable_asw_togw(state.inputs, state.settings)
    except Exception as error:
        st.session_state[_LAST_ERROR_KEY] = str(error)
        st.session_state[_STATUS_KIND_KEY] = "warning"
        st.session_state[_STATUS_MESSAGE_KEY] = "Recompute failed. Showing the last valid result."
        return

    sensitivity_results, skipped_count = _run_stable_input_sensitivity_sweep(state)

    st.session_state[_APPLIED_STATE_KEY] = state
    st.session_state[_LAST_SOLUTION_KEY] = solution
    st.session_state[_LAST_SENSITIVITY_KEY] = sensitivity_results
    st.session_state[_LAST_ERROR_KEY] = None
    st.session_state[_STATUS_KIND_KEY] = "success"
    if skipped_count:
        st.session_state[_STATUS_MESSAGE_KEY] = (
            f"{success_message} Skipped {skipped_count} out-of-range sweep "
            f"sample{'s' if skipped_count != 1 else ''}."
        )
    else:
        st.session_state[_STATUS_MESSAGE_KEY] = success_message


def _handle_recompute() -> None:
    _apply_state(_read_form_state(), "Recomputed from the visible sidebar inputs.")


def _handle_reset() -> None:
    baseline_state = _make_baseline_page_state()
    _set_form_state(baseline_state)
    _apply_state(baseline_state, "Reset to the approved baseline and recomputed.")


def _initialize_session_state() -> None:
    if st.session_state.get(_INITIALIZED_KEY):
        return

    baseline_state = _make_baseline_page_state()
    _set_form_state(baseline_state)
    _apply_state(baseline_state, "Loaded the approved baseline configuration.")
    st.session_state[_INITIALIZED_KEY] = True


def _resolve_xdsm_path() -> Path:
    return Path(__file__).resolve().parents[1] / "docs" / "assets" / "images" / "asw_sizing_xdsm.png"


def _mission_profile_rows(solution: ASWSizingSolution) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    cumulative_ratio = 1.0
    segments = (
        ("Warmup/takeoff", "W1 → W2", solution.segment_ratios.warmup_takeoff_weight_ratio_w2_over_w1),
        ("Climb", "W2 → W3", solution.segment_ratios.climb_weight_ratio_w3_over_w2),
        ("Outbound cruise", "W3 → W4", solution.segment_ratios.outbound_cruise_weight_ratio_w4_over_w3),
        ("On-station loiter", "W4 → W5", solution.segment_ratios.on_station_loiter_weight_ratio_w5_over_w4),
        ("Return cruise", "W5 → W6", solution.segment_ratios.return_cruise_weight_ratio_w6_over_w5),
        ("Prelanding loiter", "W6 → W7", solution.segment_ratios.prelanding_loiter_weight_ratio_w7_over_w6),
        ("Landing", "W7 → W8", solution.segment_ratios.landing_weight_ratio_w8_over_w7),
    )
    for segment_name, transition, ratio in segments:
        cumulative_ratio *= ratio
        rows.append(
            {
                "Mission segment": segment_name,
                "State transition": transition,
                "Weight ratio": _format_fraction(ratio),
                "Remaining weight / W1": _format_fraction(cumulative_ratio),
            }
        )
    return rows


def _derived_rows(solution: ASWSizingSolution) -> list[dict[str, str]]:
    return [
        {"Quantity": "Fixed weight", "Value": _format_number(solution.derived_quantities.fixed_weight_lb, 1), "Units": "lb"},
        {
            "Quantity": "One-way cruise range",
            "Value": _format_number(solution.derived_quantities.cruise_range_one_way_ft, 0),
            "Units": "ft",
        },
        {
            "Quantity": "On-station loiter endurance",
            "Value": _format_number(solution.derived_quantities.loiter_on_station_endurance_s, 0),
            "Units": "s",
        },
        {
            "Quantity": "Prelanding loiter endurance",
            "Value": _format_number(solution.derived_quantities.loiter_prelanding_endurance_s, 0),
            "Units": "s",
        },
        {"Quantity": "Cruise speed", "Value": _format_number(solution.derived_quantities.cruise_speed_ft_per_s, 1), "Units": "ft/s"},
        {
            "Quantity": "Cruise TSFC",
            "Value": _format_fraction(
                solution.derived_quantities.cruise_thrust_specific_fuel_consumption_lb_per_s_per_lb,
                6,
            ),
            "Units": "lb/s/lb",
        },
        {
            "Quantity": "Loiter TSFC",
            "Value": _format_fraction(
                solution.derived_quantities.loiter_thrust_specific_fuel_consumption_lb_per_s_per_lb,
                6,
            ),
            "Units": "lb/s/lb",
        },
        {
            "Quantity": "Wetted aspect ratio",
            "Value": _format_fraction(solution.derived_quantities.wetted_aspect_ratio),
            "Units": "unitless",
        },
        {
            "Quantity": "(L/D)max = K_LD·√(AR_wet)",
            "Value": _format_fraction(solution.derived_quantities.lift_to_drag_max),
            "Units": "unitless",
        },
        {
            "Quantity": "Cruise L/D",
            "Value": _format_fraction(solution.derived_quantities.cruise_lift_to_drag),
            "Units": "unitless",
        },
        {
            "Quantity": "Loiter L/D",
            "Value": _format_fraction(solution.derived_quantities.loiter_lift_to_drag),
            "Units": "unitless",
        },
    ]


def _segment_rows(solution: ASWSizingSolution) -> list[dict[str, str]]:
    return [
        {"Segment": "Warmup/takeoff W2/W1", "Weight ratio": _format_fraction(solution.segment_ratios.warmup_takeoff_weight_ratio_w2_over_w1)},
        {"Segment": "Climb W3/W2", "Weight ratio": _format_fraction(solution.segment_ratios.climb_weight_ratio_w3_over_w2)},
        {"Segment": "Outbound cruise W4/W3", "Weight ratio": _format_fraction(solution.segment_ratios.outbound_cruise_weight_ratio_w4_over_w3)},
        {"Segment": "On-station loiter W5/W4", "Weight ratio": _format_fraction(solution.segment_ratios.on_station_loiter_weight_ratio_w5_over_w4)},
        {"Segment": "Return cruise W6/W5", "Weight ratio": _format_fraction(solution.segment_ratios.return_cruise_weight_ratio_w6_over_w5)},
        {"Segment": "Prelanding loiter W7/W6", "Weight ratio": _format_fraction(solution.segment_ratios.prelanding_loiter_weight_ratio_w7_over_w6)},
        {"Segment": "Landing W8/W7", "Weight ratio": _format_fraction(solution.segment_ratios.landing_weight_ratio_w8_over_w7)},
    ]


def _mission_fraction_rows(solution: ASWSizingSolution) -> list[dict[str, str]]:
    return [
        {"Quantity": "Mission weight fraction W8/W1", "Value": _format_fraction(solution.mission_fractions.mission_weight_fraction_w8_over_w1)},
        {"Quantity": "Mission fuel fraction", "Value": _format_fraction(solution.mission_fractions.mission_fuel_fraction)},
        {"Quantity": "Reserve + trapped multiplier", "Value": _format_fraction(solution.mission_fractions.reserve_and_trapped_fuel_multiplier)},
        {"Quantity": "Fuel weight fraction Wf/WTO", "Value": _format_fraction(solution.mission_fractions.fuel_weight_fraction_wf_over_wto)},
    ]


def _final_breakdown_rows(solution: ASWSizingSolution) -> list[dict[str, str]]:
    fuel_weight_lb = solution.final_takeoff_gross_weight_lb * solution.mission_fractions.fuel_weight_fraction_wf_over_wto
    return [
        {"Quantity": "Final takeoff gross weight", "Value": _format_number(solution.final_takeoff_gross_weight_lb, 1), "Units": "lb"},
        {"Quantity": "Fixed weight", "Value": _format_number(solution.derived_quantities.fixed_weight_lb, 1), "Units": "lb"},
        {"Quantity": "Fuel weight", "Value": _format_number(fuel_weight_lb, 1), "Units": "lb"},
        {"Quantity": "Final empty weight", "Value": _format_number(solution.final_empty_weight_lb, 1), "Units": "lb"},
        {"Quantity": "Final empty-weight fraction", "Value": _format_fraction(solution.final_empty_weight_fraction_we_over_wto), "Units": "fraction"},
        {"Quantity": "Structure material", "Value": solution.inputs.structure_material.capitalize(), "Units": "-"},
        {"Quantity": "Converged iterations", "Value": str(solution.iteration_count), "Units": "count"},
    ]


def _iteration_rows(solution: ASWSizingSolution) -> list[dict[str, str]]:
    return [
        {
            "Iteration": str(step.iteration_number),
            "Guess TOGW [lb]": _format_number(step.guess_takeoff_gross_weight_lb, 1),
            "Fuel fraction": _format_fraction(step.fuel_weight_fraction_wf_over_wto),
            "Empty fraction": _format_fraction(step.empty_weight_fraction_we_over_wto),
            "Empty weight [lb]": _format_number(step.empty_weight_lb, 1),
            "Updated TOGW [lb]": _format_number(step.updated_takeoff_gross_weight_lb, 1),
            "Difference [lb]": _format_number(step.difference_lb, 1),
        }
        for step in solution.iteration_history
    ]


def _sensitivity_rows(
    state: _PageState,
    solution: ASWSizingSolution,
    sensitivity_results: tuple[InputSensitivityResult, ...],
) -> list[dict[str, str]]:
    field_spec = _INPUT_SPECS[state.sensitivity.input_name]
    baseline_weight = solution.final_takeoff_gross_weight_lb
    rows: list[dict[str, str]] = []
    for result in sensitivity_results:
        delta_lb = result.final_takeoff_gross_weight_lb - baseline_weight
        rows.append(
            {
                f"{field_spec.label} [{field_spec.units}]": _format_number(result.input_value, 3),
                "Final TOGW [lb]": _format_number(result.final_takeoff_gross_weight_lb, 1),
                "Δ TOGW [lb]": _format_number(delta_lb, 1),
                "Δ TOGW [%]": _format_percent(delta_lb / baseline_weight if baseline_weight else 0.0),
            }
        )
    return rows


def _sanity_check_rows(solution: ASWSizingSolution) -> list[dict[str, str]]:
    last_step: IterationStep = solution.iteration_history[-1]
    denominator = (
        1.0
        - solution.mission_fractions.fuel_weight_fraction_wf_over_wto
        - solution.final_empty_weight_fraction_we_over_wto
    )
    segment_values = [
        solution.segment_ratios.warmup_takeoff_weight_ratio_w2_over_w1,
        solution.segment_ratios.climb_weight_ratio_w3_over_w2,
        solution.segment_ratios.outbound_cruise_weight_ratio_w4_over_w3,
        solution.segment_ratios.on_station_loiter_weight_ratio_w5_over_w4,
        solution.segment_ratios.return_cruise_weight_ratio_w6_over_w5,
        solution.segment_ratios.prelanding_loiter_weight_ratio_w7_over_w6,
        solution.segment_ratios.landing_weight_ratio_w8_over_w7,
    ]
    checks = [
        ("Final residual within tolerance", abs(last_step.difference_lb) <= solution.settings.convergence_tolerance_lb, f"{_format_number(abs(last_step.difference_lb), 3)} lb ≤ {_format_number(solution.settings.convergence_tolerance_lb, 3)} lb"),
        ("All mission segment ratios stay in (0, 1]", all(0.0 < value <= 1.0 for value in segment_values), f"min={_format_fraction(min(segment_values))}, max={_format_fraction(max(segment_values))}"),
        ("Fuel fraction stays below 1.0", solution.mission_fractions.fuel_weight_fraction_wf_over_wto < 1.0, _format_fraction(solution.mission_fractions.fuel_weight_fraction_wf_over_wto)),
        ("Empty-weight fraction stays in (0, 1)", 0.0 < solution.final_empty_weight_fraction_we_over_wto < 1.0, _format_fraction(solution.final_empty_weight_fraction_we_over_wto)),
        ("Sizing denominator stays positive", denominator > 0.0, _format_fraction(denominator)),
        ("Cruise L/D does not exceed L/D max", solution.derived_quantities.cruise_lift_to_drag <= solution.derived_quantities.loiter_lift_to_drag, f"{_format_fraction(solution.derived_quantities.cruise_lift_to_drag)} ≤ {_format_fraction(solution.derived_quantities.loiter_lift_to_drag)}"),
    ]
    return [
        {
            "Check": name,
            "Status": "Pass" if passed else "Review",
            "Observed value": observed,
        }
        for name, passed, observed in checks
    ]


def _build_convergence_figure(solution: ASWSizingSolution) -> plt.Figure:
    iterations = [step.iteration_number for step in solution.iteration_history]
    guesses = [step.guess_takeoff_gross_weight_lb for step in solution.iteration_history]
    updates = [step.updated_takeoff_gross_weight_lb for step in solution.iteration_history]
    differences = [abs(step.difference_lb) for step in solution.iteration_history]

    figure, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    axes[0].plot(iterations, guesses, marker="o", label="Guess")
    axes[0].plot(iterations, updates, marker="s", label="Updated")
    axes[0].set_title("TOGW by iteration")
    axes[0].set_xlabel("Iteration")
    axes[0].set_ylabel("Weight [lb]")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].semilogy(iterations, differences, marker="o", color="tab:purple")
    axes[1].axhline(
        solution.settings.convergence_tolerance_lb,
        linestyle="--",
        color="tab:red",
        label="Tolerance",
    )
    axes[1].set_title("Convergence history")
    axes[1].set_xlabel("Iteration")
    axes[1].set_ylabel("|updated - guess| [lb]")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    figure.suptitle("Fixed-point convergence")
    figure.tight_layout()
    return figure


def _build_sensitivity_figure(
    state: _PageState,
    solution: ASWSizingSolution,
    sensitivity_results: tuple[InputSensitivityResult, ...],
) -> plt.Figure:
    field_spec = _INPUT_SPECS[state.sensitivity.input_name]
    x_values = [result.input_value for result in sensitivity_results]
    y_values = [result.final_takeoff_gross_weight_lb for result in sensitivity_results]
    baseline_x = float(getattr(state.inputs, state.sensitivity.input_name))
    baseline_y = solution.final_takeoff_gross_weight_lb

    figure, axis = plt.subplots(figsize=(7.5, 4.2))
    axis.plot(x_values, y_values, marker="o", color="tab:blue")
    axis.scatter([baseline_x], [baseline_y], color="tab:red", s=70, label="Applied input", zorder=3)
    axis.set_title("One-at-a-time final TOGW sensitivity")
    axis.set_xlabel(f"{field_spec.label} [{field_spec.units}]")
    axis.set_ylabel("Final TOGW [lb]")
    axis.grid(True, alpha=0.3)
    axis.legend()
    figure.tight_layout()
    return figure


def _render_sidebar() -> None:
    with st.sidebar:
        st.header("ASW sizing controls")
        st.caption("Edit inputs, then click Recompute to apply them to the solver.")
        with st.form("asw_streamlit_controls", clear_on_submit=False):
            for title, field_specs in _INPUT_GROUPS:
                with st.expander(title, expanded=True):
                    for field_spec in field_specs:
                        if field_spec.is_slider:
                            st.slider(
                                _field_label(field_spec),
                                key=_widget_key(field_spec.name),
                                min_value=float(field_spec.slider_min),
                                max_value=float(field_spec.slider_max),
                                step=field_spec.step,
                                format=_format_from_step(field_spec.step),
                            )
                        else:
                            st.number_input(
                                _field_label(field_spec),
                                key=_widget_key(field_spec.name),
                                step=field_spec.step,
                                format=_format_from_step(field_spec.step),
                            )

            with st.expander("Structure", expanded=True):
                st.radio(
                    "Structure material",
                    key=_widget_key(_MATERIAL_KEY),
                    options=list(_MATERIAL_OPTIONS),
                    format_func=str.capitalize,
                    horizontal=True,
                    help="Composite construction scales the empty-weight fraction by 0.95 (Raymer).",
                )

            with st.expander("Solver controls", expanded=True):
                for field_spec in _SETTING_SPECS:
                    st.number_input(
                        _field_label(field_spec),
                        key=_widget_key(field_spec.name),
                        step=field_spec.step,
                        format=_format_from_step(field_spec.step),
                    )
                st.number_input(
                    "Maximum iterations [count]",
                    key=_widget_key("maximum_iterations"),
                    step=1,
                    format="%d",
                )

            with st.expander("One-at-a-time sensitivity sweep", expanded=True):
                st.selectbox(
                    "Sweep input",
                    key=_widget_key("sensitivity_input_name"),
                    options=list(_SWEEP_INPUT_NAMES),
                    format_func=lambda name: _field_label(_INPUT_SPECS[name]),
                )
                st.slider(
                    "Relative span [fraction]",
                    key=_widget_key("sensitivity_relative_span_fraction"),
                    min_value=0.02,
                    max_value=0.50,
                    step=0.01,
                )
                st.number_input(
                    "Sweep samples [count]",
                    key=_widget_key("sensitivity_sample_count"),
                    step=2,
                    format="%d",
                )

            recompute_column, reset_column = st.columns(2)
            with recompute_column:
                st.form_submit_button("Recompute", type="primary", use_container_width=True, on_click=_handle_recompute)
            with reset_column:
                st.form_submit_button("Reset baseline", use_container_width=True, on_click=_handle_reset)


def _render_status() -> None:
    status_kind = st.session_state.get(_STATUS_KIND_KEY, "info")
    status_message = st.session_state.get(_STATUS_MESSAGE_KEY, "")
    last_error = st.session_state.get(_LAST_ERROR_KEY)

    if status_kind == "warning":
        message = status_message
        if last_error:
            message = f"{message} {last_error}"
        st.warning(message)
    elif status_kind == "success":
        st.success(status_message)
    elif status_message:
        st.info(status_message)


def _render_summary_metrics(solution: ASWSizingSolution) -> None:
    fuel_weight_lb = solution.final_takeoff_gross_weight_lb * solution.mission_fractions.fuel_weight_fraction_wf_over_wto
    metric_columns = st.columns(4)
    metric_columns[0].metric("Final TOGW [lb]", _format_number(solution.final_takeoff_gross_weight_lb, 0))
    metric_columns[1].metric("Fuel weight [lb]", _format_number(fuel_weight_lb, 0))
    metric_columns[2].metric("Empty weight [lb]", _format_number(solution.final_empty_weight_lb, 0))
    metric_columns[3].metric("Iterations [count]", str(solution.iteration_count))


def _render_table(title: str, caption: str, rows: list[dict[str, str]]) -> None:
    st.subheader(title)
    st.caption(caption)
    st.dataframe(rows, hide_index=True, use_container_width=True)


def render() -> None:
    """Render the ASW Streamlit tutorial page."""

    st.set_page_config(page_title="ASW fixed-point sizing tutorial", layout="wide")
    _initialize_session_state()
    _render_sidebar()

    solution: ASWSizingSolution = st.session_state[_LAST_SOLUTION_KEY]
    applied_state: _PageState = st.session_state[_APPLIED_STATE_KEY]
    sensitivity_results: tuple[InputSensitivityResult, ...] = st.session_state[_LAST_SENSITIVITY_KEY]

    st.title("ASW fixed-point sizing tutorial")
    st.caption(
        "Streamlit-native fixed-point aircraft sizing using the relocated ASW sizing kernel. "
        "Results update only when you explicitly recompute."
    )
    _render_status()
    _render_summary_metrics(solution)

    overview_tab, intermediate_tab, convergence_tab, sensitivity_tab = st.tabs(
        ["Overview", "Intermediate calculations", "Convergence", "Sensitivity & sanity checks"]
    )

    with overview_tab:
        overview_left, overview_right = st.columns((3, 2))
        with overview_left:
            _render_table(
                "Mission profile overview",
                "Table: Segment-by-segment mission progression and cumulative retained weight relative to W1.",
                _mission_profile_rows(solution),
            )
        with overview_right:
            st.subheader("Sizing XDSM")
            xdsm_path = _resolve_xdsm_path()
            if xdsm_path.is_file():
                st.image(
                    str(xdsm_path),
                    caption="Figure: Relocated ASW sizing XDSM used by the Streamlit overview.",
                    use_container_width=True,
                )
            else:
                st.info("The relocated XDSM image is not available in this environment.")

    with intermediate_tab:
        top_left, top_right = st.columns(2)
        with top_left:
            _render_table(
                "Derived values",
                "Table: Cruise, endurance, and aerodynamic quantities derived from the current applied inputs.",
                _derived_rows(solution),
            )
            _render_table(
                "Mission and fuel fractions",
                "Table: Fuel-related fractions computed from the explicit mission ratios.",
                _mission_fraction_rows(solution),
            )
        with top_right:
            _render_table(
                "Mission segment ratios",
                "Table: Explicit W-ratio values for the seven-step mission profile.",
                _segment_rows(solution),
            )
            _render_table(
                "Final TOGW breakdown",
                "Table: Final mass breakdown at the converged solution.",
                _final_breakdown_rows(solution),
            )

    with convergence_tab:
        st.subheader("Fixed-point convergence")
        st.caption("Figure: Guess, updated TOGW, and residual magnitude across the fixed-point iteration.")
        convergence_figure = _build_convergence_figure(solution)
        st.pyplot(convergence_figure, use_container_width=True)
        plt.close(convergence_figure)
        st.caption("Table: Iteration-by-iteration convergence history for the current applied inputs.")
        st.dataframe(_iteration_rows(solution), hide_index=True, use_container_width=True)

    with sensitivity_tab:
        field_spec = _INPUT_SPECS[applied_state.sensitivity.input_name]
        st.subheader("One-at-a-time final TOGW sensitivity")
        st.caption(
            f"Figure and table: ±{applied_state.sensitivity.relative_span_fraction:.0%} sweep around "
            f"{field_spec.label.lower()} with {applied_state.sensitivity.sample_count} samples."
        )
        sensitivity_figure = _build_sensitivity_figure(applied_state, solution, sensitivity_results)
        st.pyplot(sensitivity_figure, use_container_width=True)
        plt.close(sensitivity_figure)
        sensitivity_left, sensitivity_right = st.columns(2)
        with sensitivity_left:
            st.caption("Table: Final TOGW response across the selected one-at-a-time sweep.")
            st.dataframe(
                _sensitivity_rows(applied_state, solution, sensitivity_results),
                hide_index=True,
                use_container_width=True,
            )
        with sensitivity_right:
            st.caption("Table: Sanity checks for the current converged solution.")
            st.dataframe(_sanity_check_rows(solution), hide_index=True, use_container_width=True)
