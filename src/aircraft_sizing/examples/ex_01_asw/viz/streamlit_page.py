"""Streamlit page for the ASW sizing example, backed by the OpenMDAO + JAX model.

The page lets students drive the headline mission / aero / propulsion / structure
inputs, pick the nonlinear solver, and watch the sized takeoff gross weight, the
fixed-point convergence, and a one-at-a-time sensitivity sweep respond.  All of the
numbers come from :func:`aircraft_sizing.examples.ex_01_asw.methods.config.solve`,
i.e. the same OpenMDAO group the two lessons dissect.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless backend: safe under Streamlit and AppTest threads
import matplotlib.pyplot as plt
import streamlit as st

from aircraft_sizing.examples.ex_01_asw.methods.config import (
    ASWSizingInputs,
    ASWSizingResult,
    IterationStep,
    solve,
)
from aircraft_sizing.examples.ex_01_asw.methods.group import SOLVER_CHOICES

__all__ = ["render"]

_INITIALIZED_KEY = "asw_streamlit_initialized"
_APPLIED_STATE_KEY = "asw_streamlit_applied_state"
_LAST_SOLUTION_KEY = "asw_streamlit_last_solution"
_LAST_SENSITIVITY_KEY = "asw_streamlit_last_sensitivity"
_STATUS_MESSAGE_KEY = "asw_streamlit_status_message"
_STATUS_KIND_KEY = "asw_streamlit_status_kind"
_LAST_ERROR_KEY = "asw_streamlit_last_error"

_SOLVER_LABELS = {
    "nlbgs": "Fixed point (NL block Gauss-Seidel)",
    "nlbgs_aitken": "Fixed point + Aitken acceleration",
    "newton": "Newton (JAX Jacobian)",
    "broyden": "Broyden (quasi-Newton)",
}


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
        return self.slider_min is not None and self.slider_max is not None


@dataclass(frozen=True, slots=True)
class _SensitivitySweepSettings:
    input_name: str = "cruise_range_one_way_nm"
    relative_span_fraction: float = 0.10
    sample_count: int = 9

    def __post_init__(self) -> None:
        valid = {field.name for field in fields(ASWSizingInputs)}
        if self.input_name not in valid:
            raise ValueError(f"input_name must be one of {sorted(valid)}; got {self.input_name!r}.")
        if self.relative_span_fraction <= 0.0:
            raise ValueError("relative_span_fraction must be > 0.")
        if self.sample_count < 3:
            raise ValueError("sample_count must be >= 3.")


@dataclass(frozen=True, slots=True)
class _PageState:
    inputs: ASWSizingInputs
    solver: str
    initial_guess_lb: float
    convergence_tolerance_lb: float
    maximum_iterations: int
    sensitivity: _SensitivitySweepSettings

    def solve_kwargs(self) -> dict:
        return {
            "solver": self.solver,
            "initial_guess": self.initial_guess_lb,
            "convergence_tolerance_lb": self.convergence_tolerance_lb,
            "max_iterations": self.maximum_iterations,
        }


def _make_baseline_page_state() -> _PageState:
    return _PageState(
        inputs=ASWSizingInputs.baseline(),
        solver="nlbgs",
        initial_guess_lb=50_000.0,
        convergence_tolerance_lb=1.0,
        maximum_iterations=100,
        sensitivity=_SensitivitySweepSettings(),
    )


# Only the inputs students actually drive are widgets. Everything else (cruise
# Mach, altitude, speed of sound, crew weight, prelanding loiter, the historical
# segment ratios, K_LD, the L/D factors, and the fuel/empty-weight allowances)
# stays fixed at the Raymer 3.6 baseline defined in the model.
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
            _FieldSpec("cruise_thrust_specific_fuel_consumption_lb_per_hr_per_lb", "Cruise TSFC", "lb/hr/lb", 0.01, 1e-6),
            _FieldSpec("loiter_thrust_specific_fuel_consumption_lb_per_hr_per_lb", "Loiter TSFC", "lb/hr/lb", 0.01, 1e-6),
        ),
    ),
    (
        "Aerodynamics",
        (
            _FieldSpec("wing_aspect_ratio", "Wing aspect ratio", "unitless", 0.1, 1e-6),
            _FieldSpec("wetted_area_ratio_s_wet_over_s_ref", "Wetted-area ratio S_wet/S_ref", "unitless", 0.1, 1e-6),
        ),
    ),
)

_INPUT_SPECS = {spec.name: spec for _, specs in _INPUT_GROUPS for spec in specs}

# The one-at-a-time sweep is restricted to the four most instructive inputs.
_SWEEP_INPUT_NAMES: tuple[str, ...] = (
    "cruise_range_one_way_nm",
    "mission_equipment_weight_lb",
    "wing_aspect_ratio",
    "cruise_thrust_specific_fuel_consumption_lb_per_hr_per_lb",
)

_MATERIAL_KEY = "structure_material"
_MATERIAL_OPTIONS: tuple[str, ...] = ("metal", "composite")


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
    return f"%.{len(step_text.split('.')[1])}f"


def _field_label(spec: _FieldSpec) -> str:
    return f"{spec.label} [{spec.units}]"


# --------------------------------------------------------------------------- #
# Widget <-> state plumbing
# --------------------------------------------------------------------------- #
def _set_form_state(state: _PageState) -> None:
    for spec in _INPUT_SPECS.values():
        st.session_state[_widget_key(spec.name)] = float(getattr(state.inputs, spec.name))
    st.session_state[_widget_key(_MATERIAL_KEY)] = state.inputs.structure_material
    st.session_state[_widget_key("solver")] = state.solver
    st.session_state[_widget_key("initial_guess_lb")] = float(state.initial_guess_lb)
    st.session_state[_widget_key("convergence_tolerance_lb")] = float(state.convergence_tolerance_lb)
    st.session_state[_widget_key("maximum_iterations")] = int(state.maximum_iterations)
    st.session_state[_widget_key("sensitivity_input_name")] = state.sensitivity.input_name
    st.session_state[_widget_key("sensitivity_relative_span_fraction")] = float(state.sensitivity.relative_span_fraction)
    st.session_state[_widget_key("sensitivity_sample_count")] = int(state.sensitivity.sample_count)


def _read_form_state() -> _PageState:
    widget_values = {name: float(st.session_state[_widget_key(name)]) for name in _INPUT_SPECS}
    inputs = replace(
        ASWSizingInputs.baseline(),
        structure_material=str(st.session_state[_widget_key(_MATERIAL_KEY)]),
        **widget_values,
    )
    return _PageState(
        inputs=inputs,
        solver=str(st.session_state[_widget_key("solver")]),
        initial_guess_lb=float(st.session_state[_widget_key("initial_guess_lb")]),
        convergence_tolerance_lb=float(st.session_state[_widget_key("convergence_tolerance_lb")]),
        maximum_iterations=int(st.session_state[_widget_key("maximum_iterations")]),
        sensitivity=_SensitivitySweepSettings(
            input_name=str(st.session_state[_widget_key("sensitivity_input_name")]),
            relative_span_fraction=float(st.session_state[_widget_key("sensitivity_relative_span_fraction")]),
            sample_count=int(st.session_state[_widget_key("sensitivity_sample_count")]),
        ),
    )


def _build_sensitivity_values(state: _PageState) -> tuple[float, ...]:
    spec = _INPUT_SPECS[state.sensitivity.input_name]
    center = float(getattr(state.inputs, state.sensitivity.input_name))
    span = state.sensitivity.relative_span_fraction
    if center == 0.0:
        low, high = -span, span
    else:
        low, high = center * (1.0 - span), center * (1.0 + span)
    low, high = sorted((low, high))
    if spec.sensitivity_min is not None:
        low, high = max(low, spec.sensitivity_min), max(high, spec.sensitivity_min)
    if spec.sensitivity_max is not None:
        low, high = min(low, spec.sensitivity_max), min(high, spec.sensitivity_max)
    if high <= low:
        delta = max(abs(center) * span, spec.step, 1e-6)
        low, high = center - delta, center + delta
    spacing = (high - low) / (state.sensitivity.sample_count - 1)
    values = [low + spacing * i for i in range(state.sensitivity.sample_count)]
    unique = []
    for value in values:
        if not unique or abs(value - unique[-1]) > 1e-12:
            unique.append(value)
    return tuple(unique)


# --------------------------------------------------------------------------- #
# Solve orchestration
# --------------------------------------------------------------------------- #
def _run_sensitivity_sweep(state: _PageState) -> tuple[tuple[tuple[float, ASWSizingResult], ...], int]:
    results: list[tuple[float, ASWSizingResult]] = []
    skipped = 0
    for value in _build_sensitivity_values(state):
        try:
            result = solve(state.inputs.with_value(state.sensitivity.input_name, value), **state.solve_kwargs())
        except (ValueError, RuntimeError):
            skipped += 1
            continue
        results.append((float(value), result))
    return tuple(results), skipped


def _apply_state(state: _PageState, success_message: str) -> None:
    try:
        solution = solve(state.inputs, **state.solve_kwargs())
    except Exception as error:  # noqa: BLE001 - surface any solve failure to the user
        st.session_state[_LAST_ERROR_KEY] = str(error)
        st.session_state[_STATUS_KIND_KEY] = "warning"
        st.session_state[_STATUS_MESSAGE_KEY] = "Recompute failed. Showing the last valid result."
        return

    sensitivity_results, skipped = _run_sensitivity_sweep(state)
    st.session_state[_APPLIED_STATE_KEY] = state
    st.session_state[_LAST_SOLUTION_KEY] = solution
    st.session_state[_LAST_SENSITIVITY_KEY] = sensitivity_results
    st.session_state[_LAST_ERROR_KEY] = None
    st.session_state[_STATUS_KIND_KEY] = "success"
    if skipped:
        st.session_state[_STATUS_MESSAGE_KEY] = (
            f"{success_message} Skipped {skipped} out-of-range sweep sample{'s' if skipped != 1 else ''}."
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


# --------------------------------------------------------------------------- #
# Table / figure builders
# --------------------------------------------------------------------------- #
def _mission_profile_rows(result: ASWSizingResult) -> list[dict[str, str]]:
    ratios = result.segment_ratios
    segments = (
        ("Warmup/takeoff", "W1 -> W2", ratios.warmup_takeoff),
        ("Climb", "W2 -> W3", ratios.climb),
        ("Outbound cruise", "W3 -> W4", ratios.outbound_cruise),
        ("On-station loiter", "W4 -> W5", ratios.on_station_loiter),
        ("Return cruise", "W5 -> W6", ratios.return_cruise),
        ("Prelanding loiter", "W6 -> W7", ratios.prelanding_loiter),
        ("Landing", "W7 -> W8", ratios.landing),
    )
    rows = []
    cumulative = 1.0
    for name, transition, ratio in segments:
        cumulative *= ratio
        rows.append(
            {
                "Mission segment": name,
                "State transition": transition,
                "Weight ratio": _format_fraction(ratio),
                "Remaining weight / W1": _format_fraction(cumulative),
            }
        )
    return rows


def _derived_rows(result: ASWSizingResult) -> list[dict[str, str]]:
    return [
        {"Quantity": "Fixed weight", "Value": _format_number(result.fixed_weight_lb, 1), "Units": "lb"},
        {"Quantity": "One-way cruise range", "Value": _format_number(result.cruise_range_ft, 0), "Units": "ft"},
        {"Quantity": "On-station loiter endurance", "Value": _format_number(result.loiter_on_station_s, 0), "Units": "s"},
        {"Quantity": "Prelanding loiter endurance", "Value": _format_number(result.loiter_prelanding_s, 0), "Units": "s"},
        {"Quantity": "Cruise speed", "Value": _format_number(result.cruise_speed_ft_per_s, 1), "Units": "ft/s"},
        {"Quantity": "Cruise TSFC", "Value": _format_fraction(result.sfc_cruise_per_s, 6), "Units": "lb/s/lb"},
        {"Quantity": "Loiter TSFC", "Value": _format_fraction(result.sfc_loiter_per_s, 6), "Units": "lb/s/lb"},
        {"Quantity": "Wetted aspect ratio", "Value": _format_fraction(result.wetted_aspect_ratio), "Units": "unitless"},
        {"Quantity": "(L/D)max = K_LD*sqrt(AR_wet)", "Value": _format_fraction(result.lift_to_drag_max), "Units": "unitless"},
        {"Quantity": "Cruise L/D", "Value": _format_fraction(result.cruise_lift_to_drag), "Units": "unitless"},
        {"Quantity": "Loiter L/D", "Value": _format_fraction(result.loiter_lift_to_drag), "Units": "unitless"},
    ]


def _segment_rows(result: ASWSizingResult) -> list[dict[str, str]]:
    ratios = result.segment_ratios
    labels = (
        ("Warmup/takeoff W2/W1", ratios.warmup_takeoff),
        ("Climb W3/W2", ratios.climb),
        ("Outbound cruise W4/W3", ratios.outbound_cruise),
        ("On-station loiter W5/W4", ratios.on_station_loiter),
        ("Return cruise W6/W5", ratios.return_cruise),
        ("Prelanding loiter W7/W6", ratios.prelanding_loiter),
        ("Landing W8/W7", ratios.landing),
    )
    return [{"Segment": name, "Weight ratio": _format_fraction(value)} for name, value in labels]


def _mission_fraction_rows(result: ASWSizingResult) -> list[dict[str, str]]:
    return [
        {"Quantity": "Mission weight fraction W8/W1", "Value": _format_fraction(result.mission_weight_fraction)},
        {"Quantity": "Mission fuel fraction", "Value": _format_fraction(result.mission_fuel_fraction)},
        {"Quantity": "Reserve + trapped multiplier", "Value": _format_fraction(result.reserve_and_trapped_multiplier)},
        {"Quantity": "Fuel weight fraction Wf/WTO", "Value": _format_fraction(result.fuel_weight_fraction)},
    ]


def _final_breakdown_rows(result: ASWSizingResult) -> list[dict[str, str]]:
    return [
        {"Quantity": "Final takeoff gross weight", "Value": _format_number(result.final_takeoff_gross_weight_lb, 1), "Units": "lb"},
        {"Quantity": "Fixed weight", "Value": _format_number(result.fixed_weight_lb, 1), "Units": "lb"},
        {"Quantity": "Fuel weight", "Value": _format_number(result.fuel_weight_lb, 1), "Units": "lb"},
        {"Quantity": "Final empty weight", "Value": _format_number(result.final_empty_weight_lb, 1), "Units": "lb"},
        {"Quantity": "Final empty-weight fraction", "Value": _format_fraction(result.final_empty_weight_fraction), "Units": "fraction"},
        {"Quantity": "Structure material", "Value": result.inputs.structure_material.capitalize(), "Units": "-"},
        {"Quantity": "Fixed-point steps", "Value": str(result.iteration_count), "Units": "count"},
    ]


def _iteration_rows(result: ASWSizingResult) -> list[dict[str, str]]:
    return [
        {
            "Iteration": str(step.iteration_number),
            "Guess TOGW [lb]": _format_number(step.guess_takeoff_gross_weight_lb, 1),
            "Fuel fraction": _format_fraction(step.fuel_weight_fraction),
            "Empty fraction": _format_fraction(step.empty_weight_fraction),
            "Empty weight [lb]": _format_number(step.empty_weight_lb, 1),
            "Updated TOGW [lb]": _format_number(step.updated_takeoff_gross_weight_lb, 1),
            "Difference [lb]": _format_number(step.difference_lb, 1),
        }
        for step in result.iteration_history
    ]


def _sensitivity_rows(state: _PageState, result: ASWSizingResult, sweep: tuple[tuple[float, ASWSizingResult], ...]) -> list[dict[str, str]]:
    spec = _INPUT_SPECS[state.sensitivity.input_name]
    baseline_weight = result.final_takeoff_gross_weight_lb
    rows = []
    for value, swept in sweep:
        delta = swept.final_takeoff_gross_weight_lb - baseline_weight
        rows.append(
            {
                f"{spec.label} [{spec.units}]": _format_number(value, 3),
                "Final TOGW [lb]": _format_number(swept.final_takeoff_gross_weight_lb, 1),
                "delta TOGW [lb]": _format_number(delta, 1),
                "delta TOGW [%]": _format_percent(delta / baseline_weight if baseline_weight else 0.0),
            }
        )
    return rows


def _sanity_check_rows(state: _PageState, result: ASWSizingResult) -> list[dict[str, str]]:
    last_step = result.iteration_history[-1]
    denominator = 1.0 - result.fuel_weight_fraction - result.final_empty_weight_fraction
    ratios = result.segment_ratios
    segment_values = [getattr(ratios, f.name) for f in fields(ratios)]
    checks = [
        ("Fixed-point step within tolerance", abs(last_step.difference_lb) <= state.convergence_tolerance_lb, f"{_format_number(abs(last_step.difference_lb), 3)} lb <= {_format_number(state.convergence_tolerance_lb, 3)} lb"),
        ("All mission segment ratios stay in (0, 1]", all(0.0 < v <= 1.0 for v in segment_values), f"min={_format_fraction(min(segment_values))}, max={_format_fraction(max(segment_values))}"),
        ("Fuel fraction stays below 1.0", result.fuel_weight_fraction < 1.0, _format_fraction(result.fuel_weight_fraction)),
        ("Empty-weight fraction stays in (0, 1)", 0.0 < result.final_empty_weight_fraction < 1.0, _format_fraction(result.final_empty_weight_fraction)),
        ("Sizing denominator stays positive", denominator > 0.0, _format_fraction(denominator)),
        ("Cruise L/D does not exceed L/D max", result.cruise_lift_to_drag <= result.loiter_lift_to_drag, f"{_format_fraction(result.cruise_lift_to_drag)} <= {_format_fraction(result.loiter_lift_to_drag)}"),
    ]
    return [{"Check": name, "Status": "Pass" if ok else "Review", "Observed value": obs} for name, ok, obs in checks]


def _build_convergence_figure(state: _PageState, result: ASWSizingResult) -> plt.Figure:
    steps = result.iteration_history
    iterations = [s.iteration_number for s in steps]
    guesses = [s.guess_takeoff_gross_weight_lb for s in steps]
    updates = [s.updated_takeoff_gross_weight_lb for s in steps]
    differences = [abs(s.difference_lb) for s in steps]

    figure, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    axes[0].plot(iterations, guesses, marker="o", label="Guess")
    axes[0].plot(iterations, updates, marker="s", label="Updated")
    axes[0].set_title("TOGW by iteration")
    axes[0].set_xlabel("Iteration")
    axes[0].set_ylabel("Weight [lb]")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].semilogy(iterations, differences, marker="o", color="tab:purple")
    axes[1].axhline(state.convergence_tolerance_lb, linestyle="--", color="tab:red", label="Tolerance")
    axes[1].set_title("Convergence history")
    axes[1].set_xlabel("Iteration")
    axes[1].set_ylabel("|updated - guess| [lb]")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    figure.suptitle("Fixed-point convergence")
    figure.tight_layout()
    return figure


def _build_sensitivity_figure(state: _PageState, result: ASWSizingResult, sweep: tuple[tuple[float, ASWSizingResult], ...]) -> plt.Figure:
    spec = _INPUT_SPECS[state.sensitivity.input_name]
    x_values = [value for value, _ in sweep]
    y_values = [swept.final_takeoff_gross_weight_lb for _, swept in sweep]
    baseline_x = float(getattr(state.inputs, state.sensitivity.input_name))
    baseline_y = result.final_takeoff_gross_weight_lb

    figure, axis = plt.subplots(figsize=(7.5, 4.2))
    axis.plot(x_values, y_values, marker="o", color="tab:blue")
    axis.scatter([baseline_x], [baseline_y], color="tab:red", s=70, label="Applied input", zorder=3)
    axis.set_title("One-at-a-time final TOGW sensitivity")
    axis.set_xlabel(f"{spec.label} [{spec.units}]")
    axis.set_ylabel("Final TOGW [lb]")
    axis.grid(True, alpha=0.3)
    axis.legend()
    figure.tight_layout()
    return figure


# --------------------------------------------------------------------------- #
# Layout
# --------------------------------------------------------------------------- #
def _render_sidebar() -> None:
    with st.sidebar:
        st.header("ASW sizing controls")
        st.caption("Edit inputs, then click Recompute to apply them to the solver.")
        with st.form("asw_streamlit_controls", clear_on_submit=False):
            for title, specs in _INPUT_GROUPS:
                with st.expander(title, expanded=True):
                    for spec in specs:
                        if spec.is_slider:
                            st.slider(
                                _field_label(spec),
                                key=_widget_key(spec.name),
                                min_value=float(spec.slider_min),
                                max_value=float(spec.slider_max),
                                step=spec.step,
                                format=_format_from_step(spec.step),
                            )
                        else:
                            st.number_input(
                                _field_label(spec),
                                key=_widget_key(spec.name),
                                step=spec.step,
                                format=_format_from_step(spec.step),
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
                st.selectbox(
                    "Nonlinear solver",
                    key=_widget_key("solver"),
                    options=list(SOLVER_CHOICES),
                    format_func=lambda name: _SOLVER_LABELS.get(name, name),
                    help="All solvers converge to the same TOGW; Lesson 2 compares their cost.",
                )
                st.number_input("Initial TOGW guess [lb]", key=_widget_key("initial_guess_lb"), step=500.0, format="%.1f")
                st.number_input("Convergence tolerance [lb]", key=_widget_key("convergence_tolerance_lb"), step=0.1, format="%.1f")
                st.number_input("Maximum iterations [count]", key=_widget_key("maximum_iterations"), step=1, format="%d")

            with st.expander("One-at-a-time sensitivity sweep", expanded=True):
                st.selectbox(
                    "Sweep input",
                    key=_widget_key("sensitivity_input_name"),
                    options=list(_SWEEP_INPUT_NAMES),
                    format_func=lambda name: _field_label(_INPUT_SPECS[name]),
                )
                st.slider("Relative span [fraction]", key=_widget_key("sensitivity_relative_span_fraction"), min_value=0.02, max_value=0.50, step=0.01)
                st.number_input("Sweep samples [count]", key=_widget_key("sensitivity_sample_count"), step=2, format="%d")

            recompute_column, reset_column = st.columns(2)
            with recompute_column:
                st.form_submit_button("Recompute", type="primary", width="stretch", on_click=_handle_recompute)
            with reset_column:
                st.form_submit_button("Reset baseline", width="stretch", on_click=_handle_reset)


def _render_status() -> None:
    kind = st.session_state.get(_STATUS_KIND_KEY, "info")
    message = st.session_state.get(_STATUS_MESSAGE_KEY, "")
    last_error = st.session_state.get(_LAST_ERROR_KEY)
    if kind == "warning":
        st.warning(f"{message} {last_error}" if last_error else message)
    elif kind == "success":
        st.success(message)
    elif message:
        st.info(message)


def _render_summary_metrics(state: _PageState, result: ASWSizingResult) -> None:
    columns = st.columns(4)
    columns[0].metric("Final TOGW [lb]", _format_number(result.final_takeoff_gross_weight_lb, 0))
    columns[1].metric("Fuel weight [lb]", _format_number(result.fuel_weight_lb, 0))
    columns[2].metric("Empty weight [lb]", _format_number(result.final_empty_weight_lb, 0))
    columns[3].metric(
        "Solver iterations",
        str(result.solver_iterations),
        help=f"OpenMDAO {_SOLVER_LABELS.get(result.solver, result.solver)} iterations to tight tolerance.",
    )


def _render_table(title: str, caption: str, rows: list[dict[str, str]]) -> None:
    st.subheader(title)
    st.caption(caption)
    st.dataframe(rows, hide_index=True, width="stretch")


def render() -> None:
    """Render the ASW Streamlit tutorial page."""
    st.set_page_config(page_title="ASW fixed-point sizing tutorial", layout="wide")
    _initialize_session_state()
    _render_sidebar()

    result: ASWSizingResult = st.session_state[_LAST_SOLUTION_KEY]
    applied_state: _PageState = st.session_state[_APPLIED_STATE_KEY]
    sweep: tuple[tuple[float, ASWSizingResult], ...] = st.session_state[_LAST_SENSITIVITY_KEY]

    st.title("ASW fixed-point sizing tutorial")
    st.caption(
        "Conceptual ASW aircraft sizing solved with an OpenMDAO + JAX model "
        "(the same model dissected in Lessons 1 and 2). Results update only when you recompute."
    )
    _render_status()
    _render_summary_metrics(applied_state, result)

    overview_tab, intermediate_tab, convergence_tab, sensitivity_tab = st.tabs(
        ["Overview", "Intermediate calculations", "Convergence", "Sensitivity & sanity checks"]
    )

    with overview_tab:
        overview_left, overview_right = st.columns((3, 2))
        with overview_left:
            _render_table(
                "Mission profile overview",
                "Table: Segment-by-segment mission progression and cumulative retained weight relative to W1.",
                _mission_profile_rows(result),
            )
        with overview_right:
            st.subheader("Sizing XDSM")
            xdsm_path = _resolve_xdsm_path()
            if xdsm_path.is_file():
                st.image(str(xdsm_path), caption="Figure: ASW sizing XDSM (see Lesson 1).", width="stretch")
            else:
                st.info("The XDSM image is not available in this environment.")

    with intermediate_tab:
        top_left, top_right = st.columns(2)
        with top_left:
            _render_table("Derived values", "Table: Cruise, endurance, and aerodynamic quantities from the current inputs.", _derived_rows(result))
            _render_table("Mission and fuel fractions", "Table: Fuel-related fractions computed from the mission ratios.", _mission_fraction_rows(result))
        with top_right:
            _render_table("Mission segment ratios", "Table: Explicit W-ratio values for the seven-step mission profile.", _segment_rows(result))
            _render_table("Final TOGW breakdown", "Table: Final mass breakdown at the converged solution.", _final_breakdown_rows(result))

    with convergence_tab:
        st.subheader("Fixed-point convergence")
        st.caption(
            f"OpenMDAO's {_SOLVER_LABELS.get(result.solver, result.solver)} converged in "
            f"{result.solver_iterations} iterations. The plot and table below replay the classic Raymer "
            "fixed-point map (identical iterates, shown to the chosen lb tolerance)."
        )
        convergence_figure = _build_convergence_figure(applied_state, result)
        st.pyplot(convergence_figure, width="stretch")
        plt.close(convergence_figure)
        st.caption("Table: Iteration-by-iteration fixed-point history for the current inputs.")
        st.dataframe(_iteration_rows(result), hide_index=True, width="stretch")

    with sensitivity_tab:
        spec = _INPUT_SPECS[applied_state.sensitivity.input_name]
        st.subheader("One-at-a-time final TOGW sensitivity")
        st.caption(
            f"Figure and table: +/-{applied_state.sensitivity.relative_span_fraction:.0%} sweep around "
            f"{spec.label.lower()} with {applied_state.sensitivity.sample_count} samples."
        )
        sensitivity_figure = _build_sensitivity_figure(applied_state, result, sweep)
        st.pyplot(sensitivity_figure, width="stretch")
        plt.close(sensitivity_figure)
        sensitivity_left, sensitivity_right = st.columns(2)
        with sensitivity_left:
            st.caption("Table: Final TOGW response across the selected one-at-a-time sweep.")
            st.dataframe(_sensitivity_rows(applied_state, result, sweep), hide_index=True, width="stretch")
        with sensitivity_right:
            st.caption("Table: Sanity checks for the current converged solution.")
            st.dataframe(_sanity_check_rows(applied_state, result), hide_index=True, width="stretch")
