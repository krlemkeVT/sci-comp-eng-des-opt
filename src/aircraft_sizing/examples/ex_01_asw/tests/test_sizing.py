"""Tests for the OpenMDAO + JAX ASW sizing model.

These lock the Raymer 3.6 baseline numbers, confirm every nonlinear solver reaches
the same takeoff gross weight, and check that the analytic JAX gradients agree with
a finite-difference of the whole solve.
"""

import unittest

from aircraft_sizing.examples.ex_01_asw.methods.config import (
    ASWSizingInputs,
    SizingDivergedError,
    derived_quantities,
    input_sensitivity_sweep,
    mission_fractions,
    segment_ratios,
    solve,
)
from aircraft_sizing.examples.ex_01_asw.methods.group import (
    SOLVER_CHOICES,
    build_asw_problem,
)

BASELINE_TOGW_LB = 57_618.64


class BaselinePhysicsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inputs = ASWSizingInputs.baseline()

    def test_derived_quantities_match_worked_example(self) -> None:
        derived = derived_quantities(self.inputs)
        self.assertAlmostEqual(derived["wetted_aspect_ratio"], 7.0 / 5.5, places=6)
        self.assertAlmostEqual(derived["lift_to_drag_max"], 15.7941, places=3)
        self.assertAlmostEqual(derived["cruise_lift_to_drag"], 13.6777, places=3)
        self.assertAlmostEqual(derived["loiter_lift_to_drag"], 15.7941, places=3)
        self.assertAlmostEqual(derived["cruise_speed_ft_per_s"], 596.88, places=2)

    def test_segment_ratios_match_worked_example(self) -> None:
        ratios = segment_ratios(self.inputs)
        self.assertAlmostEqual(ratios.warmup_takeoff, 0.970, places=6)
        self.assertAlmostEqual(ratios.climb, 0.985, places=6)
        self.assertAlmostEqual(ratios.landing, 0.995, places=6)
        self.assertAlmostEqual(ratios.outbound_cruise, 0.8564, places=3)
        self.assertAlmostEqual(ratios.on_station_loiter, 0.9268, places=3)
        self.assertAlmostEqual(ratios.prelanding_loiter, 0.9916, places=3)
        self.assertAlmostEqual(ratios.return_cruise, ratios.outbound_cruise, places=9)

    def test_mission_fractions_match_worked_example(self) -> None:
        fractions = mission_fractions(self.inputs)
        self.assertAlmostEqual(fractions["mission_weight_fraction"], 0.6408, places=3)
        self.assertAlmostEqual(fractions["reserve_and_trapped_multiplier"], 1.06, places=6)
        self.assertAlmostEqual(fractions["fuel_weight_fraction"], 0.3808, places=3)


class SolveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inputs = ASWSizingInputs.baseline()

    def test_baseline_solution_matches_worked_example(self) -> None:
        result = solve(self.inputs)
        self.assertAlmostEqual(result.final_takeoff_gross_weight_lb, BASELINE_TOGW_LB, delta=1.0)
        self.assertAlmostEqual(result.final_empty_weight_fraction, 0.432, places=2)
        self.assertAlmostEqual(result.fixed_weight_lb, 10_800.0, places=6)
        # The closed-form fixed-point history reproduces Raymer's 7-iteration table.
        self.assertEqual(result.iteration_count, 7)
        self.assertLessEqual(abs(result.iteration_history[-1].difference_lb), 1.0)

    def test_all_solvers_reach_the_same_takeoff_weight(self) -> None:
        for solver in SOLVER_CHOICES:
            weight = solve(self.inputs, solver=solver).final_takeoff_gross_weight_lb
            self.assertAlmostEqual(weight, BASELINE_TOGW_LB, delta=1e-2, msg=f"solver={solver}")

    def test_convergence_from_multiple_initial_guesses(self) -> None:
        weights = [
            solve(self.inputs, initial_guess=guess).final_takeoff_gross_weight_lb
            for guess in (30_000.0, 50_000.0, 80_000.0)
        ]
        for weight in weights[1:]:
            self.assertAlmostEqual(weight, weights[0], places=4)

    def test_finite_difference_derivative_mode_also_converges(self) -> None:
        # Newton driven by OpenMDAO finite-difference partials (no JAX) must land
        # on the same answer as the analytic run -- just less efficiently.
        result = solve(self.inputs, solver="newton", deriv="fd")
        self.assertAlmostEqual(result.final_takeoff_gross_weight_lb, BASELINE_TOGW_LB, delta=1.0)

    def test_composite_structure_reduces_takeoff_weight(self) -> None:
        metal = solve(ASWSizingInputs(structure_material="metal"))
        composite = solve(ASWSizingInputs(structure_material="composite"))
        self.assertLess(
            composite.final_takeoff_gross_weight_lb,
            metal.final_takeoff_gross_weight_lb,
        )

    def test_input_sensitivity_sweep_is_monotonic_in_range(self) -> None:
        sweep = input_sensitivity_sweep(
            self.inputs, "cruise_range_one_way_nm", (1_400.0, 1_500.0, 1_600.0)
        )
        weights = [result.final_takeoff_gross_weight_lb for _, result in sweep]
        self.assertTrue(weights[0] < weights[1] < weights[2])

    def test_range_trade_grows_strongly_nonlinearly(self) -> None:
        # The app's range trade spans 1,000-2,000 nm precisely because the response
        # is convex, not linear: doubling the range nearly doubles the aircraft, and
        # the marginal cost per nm more than doubles across the band.
        sweep = input_sensitivity_sweep(
            self.inputs, "cruise_range_one_way_nm", (1_000.0, 1_500.0, 2_000.0)
        )
        low, middle, high = (result.final_takeoff_gross_weight_lb for _, result in sweep)
        self.assertAlmostEqual(low, 42_801.9, delta=1.0)
        self.assertAlmostEqual(middle, BASELINE_TOGW_LB, delta=1.0)
        self.assertAlmostEqual(high, 82_221.5, delta=1.0)
        # A straight line would have a zero second difference; this one is ~9,800 lb.
        self.assertGreater(high - 2.0 * middle + low, 5_000.0)
        # The second half of the band costs well over 1.5x the first half.
        self.assertGreater((high - middle) / (middle - low), 1.5)

    def test_sweep_over_the_full_app_band_stays_convex(self) -> None:
        values = tuple(1_000.0 + 125.0 * i for i in range(9))
        sweep = input_sensitivity_sweep(self.inputs, "cruise_range_one_way_nm", values)
        weights = [result.final_takeoff_gross_weight_lb for _, result in sweep]
        steps = [b - a for a, b in zip(weights, weights[1:])]
        for earlier, later in zip(steps, steps[1:]):
            self.assertGreater(later, earlier)

    def test_range_beyond_model_validity_reports_divergence(self) -> None:
        # Past ~3,000 nm the fixed point runs away from the default 50,000 lb start.
        # That must surface as a SizingDivergedError, never as a NaN weight, a
        # complex W_TO ** b, or a plausible-looking number.
        with self.assertRaises(SizingDivergedError):
            solve(self.inputs.with_value("cruise_range_one_way_nm", 3_500.0))

    def test_iteration_cap_the_solver_cannot_meet_reports_divergence(self) -> None:
        with self.assertRaises(SizingDivergedError):
            solve(self.inputs, max_iterations=3)


class GradientTests(unittest.TestCase):
    """Analytic JAX total derivatives must match a finite-difference of solve()."""

    def setUp(self) -> None:
        self.inputs = ASWSizingInputs.baseline()

    def _analytic_total(self, wrt_path: str) -> float:
        prob = build_asw_problem(self.inputs.params(), self.inputs.input_values(), solver="nlbgs")
        prob.run_model()
        totals = prob.compute_totals(of=["sizing.takeoff_gross_weight"], wrt=[wrt_path])
        return float(totals["sizing.takeoff_gross_weight", wrt_path][0, 0])

    def _central_difference(self, input_name: str, base_value: float, step: float) -> float:
        high = solve(self.inputs.with_value(input_name, base_value + step)).final_takeoff_gross_weight_lb
        low = solve(self.inputs.with_value(input_name, base_value - step)).final_takeoff_gross_weight_lb
        return (high - low) / (2.0 * step)

    def test_dwto_dwing_aspect_ratio(self) -> None:
        analytic = self._analytic_total("aero.wing_aspect_ratio")
        finite = self._central_difference("wing_aspect_ratio", 7.0, 1e-3)
        self.assertAlmostEqual(analytic / finite, 1.0, places=5)

    def test_dwto_dcruise_range(self) -> None:
        # The analytic derivative is per foot; convert the per-nm FD to per-foot.
        analytic = self._analytic_total("mission.range_ft")
        finite_per_nm = self._central_difference("cruise_range_one_way_nm", 1_500.0, 1e-2)
        finite_per_ft = finite_per_nm / 6076.0
        self.assertAlmostEqual(analytic / finite_per_ft, 1.0, places=5)


class ValidationTests(unittest.TestCase):
    def test_invalid_material_raises(self) -> None:
        with self.assertRaises(ValueError):
            ASWSizingInputs(structure_material="titanium")

    def test_nonpositive_range_raises(self) -> None:
        with self.assertRaises(ValueError):
            ASWSizingInputs(cruise_range_one_way_nm=0.0)

    def test_out_of_range_segment_ratio_raises(self) -> None:
        with self.assertRaises(ValueError):
            ASWSizingInputs(climb_weight_ratio=1.5)


if __name__ == "__main__":
    unittest.main()
