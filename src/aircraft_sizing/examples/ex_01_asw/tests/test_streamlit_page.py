import importlib
import importlib.util
import runpy
import sys
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock


THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[5]
SRC_ROOT = REPO_ROOT / "src"
APP_FILE = REPO_ROOT / "apps" / "streamlit" / "app.py"
PAGE_MODULE_NAME = "aircraft_sizing.examples.ex_01_asw.viz.streamlit_page"
XDSM_FILE = (
    SRC_ROOT
    / "aircraft_sizing"
    / "examples"
    / "ex_01_asw"
    / "docs"
    / "assets"
    / "images"
    / "asw_sizing_xdsm.png"
)

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def _streamlit_apptest_available() -> bool:
    try:
        return importlib.util.find_spec("streamlit.testing.v1") is not None
    except ModuleNotFoundError:
        return False


STREAMLIT_APPTEST_AVAILABLE = _streamlit_apptest_available()


def _patch_apptest_image_caption_compatibility() -> None:
    """Add an ``Image.caption`` accessor to Streamlit's AppTest element tree.

    Some Streamlit AppTest builds expose image captions only via ``captions``;
    ``test_overview_uses_resolved_xdsm_resource_when_present`` reads
    ``image.caption``. This shim is test-only support, so it lives here rather
    than in the production page module.
    """
    try:
        from streamlit.testing.v1.element_tree import Image as AppTestImage
    except Exception:
        return

    if hasattr(AppTestImage, "caption"):
        return

    AppTestImage.caption = property(  # type: ignore[attr-defined]
        lambda self: self.captions[0] if getattr(self, "captions", ()) else None
    )


if STREAMLIT_APPTEST_AVAILABLE:
    from streamlit.testing.v1 import AppTest

    import aircraft_sizing.examples.ex_01_asw.viz.streamlit_page as page_module

    _patch_apptest_image_caption_compatibility()


@contextmanager
def _stubbed_visualization_dependencies():
    streamlit_stub = types.ModuleType("streamlit")
    streamlit_stub.session_state = {}

    matplotlib_stub = types.ModuleType("matplotlib")
    matplotlib_stub.use = lambda *args, **kwargs: None
    pyplot_stub = types.ModuleType("matplotlib.pyplot")
    matplotlib_stub.pyplot = pyplot_stub

    with mock.patch.dict(
        sys.modules,
        {
            "streamlit": streamlit_stub,
            "matplotlib": matplotlib_stub,
            "matplotlib.pyplot": pyplot_stub,
        },
        clear=False,
    ):
        sys.modules.pop(PAGE_MODULE_NAME, None)
        importlib.invalidate_caches()
        try:
            yield importlib.import_module(PAGE_MODULE_NAME)
        finally:
            sys.modules.pop(PAGE_MODULE_NAME, None)


class StreamlitPageSeamTests(unittest.TestCase):
    def test_canonical_streamlit_page_import_exposes_render(self) -> None:
        with _stubbed_visualization_dependencies() as module:
            self.assertEqual(module.__all__, ["render"])
            self.assertTrue(callable(module.render))

    def test_xdsm_path_resolves_to_relocated_asset(self) -> None:
        with _stubbed_visualization_dependencies() as module:
            self.assertEqual(module._resolve_xdsm_path(), XDSM_FILE)
            self.assertTrue(module._resolve_xdsm_path().is_file())

    def test_streamlit_entry_point_imports_and_calls_canonical_render(self) -> None:
        render_mock = mock.Mock()
        fake_page_module = types.ModuleType(PAGE_MODULE_NAME)
        fake_page_module.render = render_mock

        original_sys_path = sys.path[:]
        filtered_sys_path = [entry for entry in original_sys_path if Path(entry).resolve() != SRC_ROOT]
        post_run_sys_path = None

        try:
            sys.path[:] = filtered_sys_path
            with mock.patch.dict(sys.modules, {PAGE_MODULE_NAME: fake_page_module}, clear=False):
                runpy.run_path(str(APP_FILE), run_name="__main__")
                post_run_sys_path = sys.path[:]
        finally:
            sys.path[:] = original_sys_path

        render_mock.assert_called_once_with()
        self.assertIsNotNone(post_run_sys_path)
        self.assertIn(str(SRC_ROOT), post_run_sys_path)


@unittest.skipUnless(
    STREAMLIT_APPTEST_AVAILABLE,
    "streamlit.testing.v1 is unavailable in the current dependency environment.",
)
class StreamlitPageAppTestTests(unittest.TestCase):
    def setUp(self) -> None:
        # Each app run does the baseline solve plus a sensitivity sweep (many
        # OpenMDAO solves), so allow more than the 3s AppTest default.
        self.app = AppTest.from_file(str(APP_FILE), default_timeout=60).run()

    def _click_button(self, label: str) -> None:
        for button in self.app.button:
            if button.label == label:
                button.click()
                self.app.run()
                return
        self.fail(f"Could not find Streamlit button labeled {label!r}.")

    def test_app_starts_with_baseline_outputs(self) -> None:
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(self.app.title[0].value, "ASW fixed-point sizing tutorial")
        self.assertEqual(
            self.app.session_state[page_module._STATUS_MESSAGE_KEY],
            "Loaded the approved baseline configuration.",
        )
        self.assertGreaterEqual(len(self.app.metric), 4)
        self.assertGreaterEqual(len(self.app.dataframe), 1)
        self.assertGreater(
            self.app.session_state[page_module._LAST_SOLUTION_KEY].final_takeoff_gross_weight_lb,
            0.0,
        )

    def test_recompute_button_applies_visible_solver_controls(self) -> None:
        baseline_solution = self.app.session_state[page_module._LAST_SOLUTION_KEY]
        updated_guess = 55_000.0

        self.app.number_input(page_module._widget_key("initial_guess_lb")).set_value(updated_guess)
        self._click_button("Recompute")

        applied_state = self.app.session_state[page_module._APPLIED_STATE_KEY]
        recomputed_solution = self.app.session_state[page_module._LAST_SOLUTION_KEY]

        self.assertEqual(
            self.app.session_state[page_module._STATUS_MESSAGE_KEY],
            "Recomputed from the visible sidebar inputs.",
        )
        self.assertEqual(applied_state.initial_guess_lb, updated_guess)
        self.assertEqual(
            self.app.session_state[page_module._widget_key("initial_guess_lb")],
            updated_guess,
        )
        self.assertAlmostEqual(
            recomputed_solution.final_takeoff_gross_weight_lb,
            baseline_solution.final_takeoff_gross_weight_lb,
            places=6,
        )

    def test_recompute_button_applies_mission_parameter_slider(self) -> None:
        baseline_solution = self.app.session_state[page_module._LAST_SOLUTION_KEY]
        range_key = page_module._widget_key("cruise_range_one_way_nm")

        # The mission parameters render as sliders; dragging one and recomputing
        # must flow through to the applied inputs and the solved weight.
        self.app.slider(range_key).set_value(1_800.0)
        self._click_button("Recompute")

        applied_state = self.app.session_state[page_module._APPLIED_STATE_KEY]
        recomputed_solution = self.app.session_state[page_module._LAST_SOLUTION_KEY]

        self.assertEqual(applied_state.inputs.cruise_range_one_way_nm, 1_800.0)
        self.assertEqual(self.app.session_state[range_key], 1_800.0)
        # A longer cruise burns more fuel, so the sized aircraft gets heavier.
        self.assertGreater(
            recomputed_solution.final_takeoff_gross_weight_lb,
            baseline_solution.final_takeoff_gross_weight_lb,
        )

    def test_baseline_range_trade_spans_1000_to_2000_nm_and_is_convex(self) -> None:
        sweep_settings = self.app.session_state[page_module._APPLIED_STATE_KEY].sensitivity
        self.assertEqual(sweep_settings.input_name, "cruise_range_one_way_nm")
        self.assertEqual(sweep_settings.low_value, 1_000.0)
        self.assertEqual(sweep_settings.high_value, 2_000.0)

        sweep = self.app.session_state[page_module._LAST_SENSITIVITY_KEY]
        ranges = [value for value, _ in sweep]
        weights = [result.final_takeoff_gross_weight_lb for _, result in sweep]
        self.assertEqual(ranges[0], 1_000.0)
        self.assertEqual(ranges[-1], 2_000.0)
        # Doubling the range nearly doubles the aircraft, and each successive step
        # costs more than the one before it -- the point of widening the trade.
        self.assertGreater(weights[-1] / weights[0], 1.8)
        steps = [b - a for a, b in zip(weights, weights[1:])]
        for earlier, later in zip(steps, steps[1:]):
            self.assertGreater(later, earlier)

    def test_switching_the_sweep_input_reloads_that_inputs_band(self) -> None:
        # The band slider lives inside the sidebar form, so on the click that
        # switches inputs it still holds the previous input's endpoints. Those are
        # meaningless on the new scale and must be replaced, not carried over.
        self.app.selectbox(page_module._widget_key("sensitivity_input_name")).set_value(
            "wing_aspect_ratio"
        )
        self._click_button("Recompute")

        self.assertEqual(len(self.app.exception), 0)
        sweep_settings = self.app.session_state[page_module._APPLIED_STATE_KEY].sensitivity
        aspect_ratio_spec = page_module._INPUT_SPECS["wing_aspect_ratio"]
        self.assertEqual(sweep_settings.input_name, "wing_aspect_ratio")
        self.assertEqual(sweep_settings.low_value, aspect_ratio_spec.sweep_low)
        self.assertEqual(sweep_settings.high_value, aspect_ratio_spec.sweep_high)
        self.assertEqual(
            self.app.session_state[page_module._widget_key("sensitivity_bounds")],
            (aspect_ratio_spec.sweep_low, aspect_ratio_spec.sweep_high),
        )

    def test_unreachable_iteration_cap_warns_and_keeps_the_last_result(self) -> None:
        baseline_solution = self.app.session_state[page_module._LAST_SOLUTION_KEY]

        self.app.number_input(page_module._widget_key("maximum_iterations")).set_value(3)
        self._click_button("Recompute")

        # A solve the model cannot close must reach the student as a warning banner,
        # not as a Streamlit traceback or a silently wrong takeoff weight.
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(self.app.session_state[page_module._STATUS_KIND_KEY], "warning")
        self.assertIn("did not converge", self.app.session_state[page_module._LAST_ERROR_KEY])
        self.assertEqual(
            self.app.session_state[page_module._LAST_SOLUTION_KEY].final_takeoff_gross_weight_lb,
            baseline_solution.final_takeoff_gross_weight_lb,
        )

    def test_material_radio_switches_to_composite(self) -> None:
        baseline_solution = self.app.session_state[page_module._LAST_SOLUTION_KEY]
        material_key = page_module._widget_key(page_module._MATERIAL_KEY)

        self.app.radio(material_key).set_value("composite")
        self._click_button("Recompute")

        applied_state = self.app.session_state[page_module._APPLIED_STATE_KEY]
        recomputed_solution = self.app.session_state[page_module._LAST_SOLUTION_KEY]

        self.assertEqual(applied_state.inputs.structure_material, "composite")
        # Composite trims the empty-weight fraction, so the sized aircraft is lighter.
        self.assertLess(
            recomputed_solution.final_takeoff_gross_weight_lb,
            baseline_solution.final_takeoff_gross_weight_lb,
        )

    def test_reset_button_restores_baseline_controls_and_recomputes(self) -> None:
        baseline_state = page_module._make_baseline_page_state()

        self.app.number_input(page_module._widget_key("initial_guess_lb")).set_value(55_000.0)
        self.app.number_input(page_module._widget_key("sensitivity_sample_count")).set_value(11)
        self._click_button("Reset baseline")

        applied_state = self.app.session_state[page_module._APPLIED_STATE_KEY]

        self.assertEqual(
            self.app.session_state[page_module._STATUS_MESSAGE_KEY],
            "Reset to the approved baseline and recomputed.",
        )
        self.assertEqual(
            applied_state.initial_guess_lb,
            baseline_state.initial_guess_lb,
        )
        self.assertEqual(
            applied_state.sensitivity.sample_count,
            baseline_state.sensitivity.sample_count,
        )
        self.assertEqual(
            self.app.session_state[page_module._widget_key("initial_guess_lb")],
            baseline_state.initial_guess_lb,
        )
        self.assertEqual(
            self.app.session_state[page_module._widget_key("sensitivity_sample_count")],
            baseline_state.sensitivity.sample_count,
        )

    def test_overview_uses_resolved_xdsm_resource_when_present(self) -> None:
        resolved_path = page_module._resolve_xdsm_path()

        self.assertEqual(resolved_path, XDSM_FILE)
        if resolved_path.is_file():
            self.assertGreaterEqual(len(self.app.image), 1)
            self.assertTrue(
                any(
                    image.caption == "Figure: ASW sizing XDSM (see Lesson 1)."
                    for image in self.app.image
                )
            )
            self.assertFalse(
                any(
                    info.value == "The XDSM image is not available in this environment."
                    for info in self.app.info
                )
            )
        else:
            self.assertTrue(
                any(
                    info.value == "The XDSM image is not available in this environment."
                    for info in self.app.info
                )
            )


if __name__ == "__main__":
    unittest.main()
