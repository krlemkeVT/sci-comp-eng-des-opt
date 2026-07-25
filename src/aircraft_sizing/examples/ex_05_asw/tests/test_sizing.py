import unittest
from dataclasses import replace

from aircraft_sizing.examples.ex_05_asw.methods.sizing import (
    ASWSizingInputs,
    FixedPointIterationSettings,
    compute_breguet_range_weight_ratio,
    compute_empty_weight_fraction,
    compute_mission_and_fuel_fractions,
    compute_mission_segment_ratios,
    derive_cruise_aerodynamic_quantities,
    make_baseline_asw_sizing_inputs,
    make_baseline_fixed_point_iteration_settings,
    run_one_at_a_time_input_sensitivity_sweep,
    solve_asw_togw,
)


class BaselineASWSizingTutorialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inputs = make_baseline_asw_sizing_inputs()
        self.settings = make_baseline_fixed_point_iteration_settings()

    def test_baseline_segment_ratios_and_fractions_match_worked_example(self) -> None:
        derived = derive_cruise_aerodynamic_quantities(self.inputs)
        segment_ratios = compute_mission_segment_ratios(self.inputs, derived)
        mission_fractions = compute_mission_and_fuel_fractions(segment_ratios, self.inputs)

        self.assertEqual(derived.fixed_weight_lb, 10_800.0)
        self.assertAlmostEqual(derived.cruise_range_one_way_ft, 9_114_000.0)
        self.assertAlmostEqual(derived.cruise_speed_ft_per_s, 596.88)

        # (L/D)max is computed from Raymer Eq. 3.12 (K_LD * sqrt(wetted AR)),
        # not taken as a fixed input.
        self.assertAlmostEqual(derived.wetted_aspect_ratio, 7.0 / 5.5, places=6)
        self.assertAlmostEqual(derived.lift_to_drag_max, 14.0 * (7.0 / 5.5) ** 0.5, places=6)
        self.assertAlmostEqual(derived.lift_to_drag_max, 15.7941, delta=1e-3)
        self.assertAlmostEqual(derived.cruise_lift_to_drag, 0.866 * derived.lift_to_drag_max, places=6)
        self.assertAlmostEqual(derived.loiter_lift_to_drag, derived.lift_to_drag_max, places=6)

        self.assertEqual(segment_ratios.warmup_takeoff_weight_ratio_w2_over_w1, 0.970)
        self.assertEqual(segment_ratios.climb_weight_ratio_w3_over_w2, 0.985)
        self.assertEqual(segment_ratios.landing_weight_ratio_w8_over_w7, 0.995)
        self.assertAlmostEqual(
            segment_ratios.outbound_cruise_weight_ratio_w4_over_w3,
            0.8564,
            delta=5e-4,
        )
        self.assertAlmostEqual(
            segment_ratios.on_station_loiter_weight_ratio_w5_over_w4,
            0.9268,
            delta=5e-4,
        )
        self.assertAlmostEqual(
            segment_ratios.return_cruise_weight_ratio_w6_over_w5,
            0.8564,
            delta=5e-4,
        )
        self.assertAlmostEqual(
            segment_ratios.prelanding_loiter_weight_ratio_w7_over_w6,
            0.9916,
            delta=5e-4,
        )

        self.assertAlmostEqual(
            mission_fractions.mission_weight_fraction_w8_over_w1,
            0.6408,
            delta=5e-4,
        )
        self.assertAlmostEqual(mission_fractions.reserve_and_trapped_fuel_multiplier, 1.06)
        self.assertAlmostEqual(
            mission_fractions.fuel_weight_fraction_wf_over_wto,
            0.3808,
            delta=5e-4,
        )

    def test_baseline_solver_reaches_worked_example_takeoff_weight(self) -> None:
        solution = solve_asw_togw(self.inputs, self.settings)

        self.assertEqual(solution.iteration_count, 7)
        self.assertEqual(solution.iteration_history[0].guess_takeoff_gross_weight_lb, 50_000.0)
        self.assertLessEqual(
            abs(solution.iteration_history[-1].difference_lb),
            self.settings.convergence_tolerance_lb,
        )
        self.assertEqual(round(solution.final_takeoff_gross_weight_lb, -2), 57_600.0)
        self.assertAlmostEqual(
            solution.final_empty_weight_fraction_we_over_wto,
            0.43,
            delta=0.01,
        )

    def test_fixed_point_converges_to_same_solution_from_multiple_initial_guesses(self) -> None:
        guesses = (30_000.0, 50_000.0, 80_000.0)
        settings = FixedPointIterationSettings(
            initial_takeoff_gross_weight_guess_lb=guesses[0],
            convergence_tolerance_lb=1e-9,
            maximum_iterations=100,
        )

        solutions = []
        for guess in guesses:
            solution = solve_asw_togw(
                self.inputs,
                FixedPointIterationSettings(
                    initial_takeoff_gross_weight_guess_lb=guess,
                    convergence_tolerance_lb=settings.convergence_tolerance_lb,
                    maximum_iterations=settings.maximum_iterations,
                ),
            )
            solutions.append(solution)

        reference_weight = solutions[0].final_takeoff_gross_weight_lb
        for guess, solution in zip(guesses, solutions):
            with self.subTest(initial_guess_lb=guess):
                self.assertGreater(solution.iteration_count, 1)
                self.assertAlmostEqual(
                    solution.final_takeoff_gross_weight_lb,
                    reference_weight,
                    places=6,
                )
                self.assertLessEqual(
                    abs(solution.iteration_history[-1].difference_lb),
                    settings.convergence_tolerance_lb,
                )

    def test_input_sensitivity_sweep_propagates_range_changes_into_solution(self) -> None:
        input_values = (1_400.0, 1_500.0, 1_600.0)
        results = run_one_at_a_time_input_sensitivity_sweep(
            self.inputs,
            "cruise_range_one_way_nm",
            input_values,
            self.settings,
        )

        self.assertEqual(len(results), len(input_values))
        takeoff_weights = [result.final_takeoff_gross_weight_lb for result in results]
        outbound_cruise_ratios = [
            result.solution.segment_ratios.outbound_cruise_weight_ratio_w4_over_w3
            for result in results
        ]

        for expected_value, result in zip(input_values, results):
            with self.subTest(cruise_range_one_way_nm=expected_value):
                self.assertEqual(result.input_name, "cruise_range_one_way_nm")
                self.assertEqual(result.input_value, expected_value)
                self.assertEqual(result.solution.inputs.cruise_range_one_way_nm, expected_value)

        self.assertGreater(outbound_cruise_ratios[0], outbound_cruise_ratios[1])
        self.assertGreater(outbound_cruise_ratios[1], outbound_cruise_ratios[2])
        self.assertLess(takeoff_weights[0], takeoff_weights[1])
        self.assertLess(takeoff_weights[1], takeoff_weights[2])

    def test_composite_structure_scales_empty_weight_fraction(self) -> None:
        metal_fraction = compute_empty_weight_fraction(57_000.0, self.inputs)
        composite_inputs = replace(self.inputs, structure_material="composite")
        composite_fraction = compute_empty_weight_fraction(57_000.0, composite_inputs)
        # Raymer: composite construction multiplies the empty-weight fraction by 0.95.
        self.assertAlmostEqual(composite_fraction, 0.95 * metal_fraction, places=9)

    def test_composite_material_reduces_final_takeoff_weight(self) -> None:
        metal_solution = solve_asw_togw(self.inputs, self.settings)
        composite_solution = solve_asw_togw(
            replace(self.inputs, structure_material="composite"), self.settings
        )
        self.assertLess(
            composite_solution.final_takeoff_gross_weight_lb,
            metal_solution.final_takeoff_gross_weight_lb,
        )

    def test_invalid_inputs_raise_errors(self) -> None:
        invalid_cases = (
            (
                lambda: ASWSizingInputs(warmup_takeoff_weight_ratio=0.0),
                ValueError,
                "warmup_takeoff_weight_ratio must satisfy 0 < value <= 1",
            ),
            (
                lambda: ASWSizingInputs(structure_material="titanium"),
                ValueError,
                "structure_material must be 'metal' or 'composite'",
            ),
            (
                lambda: FixedPointIterationSettings(maximum_iterations=0),
                ValueError,
                "maximum_iterations must be >= 1",
            ),
            (
                lambda: compute_breguet_range_weight_ratio(100.0, 0.1, 0.0, 10.0),
                ValueError,
                "speed_ft_per_s must be > 0",
            ),
            (
                lambda: run_one_at_a_time_input_sensitivity_sweep(
                    self.inputs,
                    "not_an_input",
                    (1.0,),
                ),
                ValueError,
                "input_name must be one of",
            ),
        )

        for call, expected_exception, expected_message in invalid_cases:
            with self.subTest(expected_message=expected_message):
                with self.assertRaisesRegex(expected_exception, expected_message):
                    call()


if __name__ == "__main__":
    unittest.main()
