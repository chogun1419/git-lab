"""HTTP tests for the common-emitter amplifier page.

The ngspice call is replaced with the recorded output in ``tests/fixtures`` so
these tests are fast and machine-independent. The real binary is exercised by
``tests/test_spice_integration.py``.
"""

import unittest
from pathlib import Path
from unittest import mock

from app import create_app
from spice_runner import SpiceError, SimResult, parse_ac, parse_op, parse_transient

FIXTURES = Path(__file__).parent / "fixtures"

FORM = {
    "vcc_v": "12",
    "r1": "100",
    "r1_unit": "kohm",
    "r2": "22",
    "r2_unit": "kohm",
    "rc": "2.2",
    "rc_unit": "kohm",
    "re": "1.0",
    "re_unit": "kohm",
    "beta": "100",
    "vin_amp_v": "10",
    "vin_amp_v_unit": "mv",
    "freq_hz": "1",
    "freq_hz_unit": "khz",
}


def fixture_result() -> SimResult:
    return SimResult(
        op=parse_op(FIXTURES / "op.txt"),
        ac=parse_ac(FIXTURES / "ac.txt"),
        tran=parse_transient(FIXTURES / "tran.txt"),
        stdout="ngspice-47 done",
        binary="ngspice_con.exe",
    )


class AmplifierWebCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def post(self, **overrides):
        data = {**FORM, **overrides}
        return self.client.post("/amplifier/simulate", data=data)

    def html(self, response):
        return response.get_data(as_text=True)


class TestAmplifierPage(AmplifierWebCase):
    def test_returns_200(self):
        self.assertEqual(self.client.get("/amplifier").status_code, 200)

    def test_has_the_amplitude_and_frequency_inputs(self):
        html = self.html(self.client.get("/amplifier"))
        self.assertIn('name="vin_amp_v"', html)
        self.assertIn('name="vin_amp_v_unit"', html)
        self.assertIn('name="freq_hz"', html)
        self.assertIn('name="freq_hz_unit"', html)

    def test_has_the_bias_inputs(self):
        html = self.html(self.client.get("/amplifier"))
        for field in ("vcc_v", "r1", "r2", "rc", "re", "beta"):
            self.assertIn(f'name="{field}"', html)

    def test_shows_the_circuit_and_no_results_yet(self):
        html = self.html(self.client.get("/amplifier"))
        self.assertIn('data-testid="circuit"', html)
        self.assertIn('data-testid="empty-state"', html)

    def test_links_back_to_the_dc_bias_page(self):
        html = self.html(self.client.get("/amplifier"))
        self.assertIn('href="/"', html)

    def test_dc_bias_page_links_to_the_amplifier(self):
        html = self.html(self.client.get("/"))
        self.assertIn('href="/amplifier"', html)


class TestSimulationRoute(AmplifierWebCase):
    def test_valid_submission_returns_200(self):
        with mock.patch("app.simulate", return_value=fixture_result()):
            response = self.post()
        self.assertEqual(response.status_code, 200)

    def test_labels_spice_and_analytical_results_separately(self):
        with mock.patch("app.simulate", return_value=fixture_result()):
            html = self.html(self.post())
        self.assertIn('data-source="spice"', html)
        self.assertIn('data-source="analytical"', html)

    def test_reports_the_spice_operating_point(self):
        with mock.patch("app.simulate", return_value=fixture_result()):
            html = self.html(self.post())
        self.assertIn("data-testid=\"spice-vb\"", html)
        self.assertIn("1.94", html)

    def test_shows_the_gain_at_the_requested_frequency(self):
        with mock.patch("app.simulate", return_value=fixture_result()):
            html = self.html(self.post())
        self.assertIn('data-testid="ac-gain"', html)
        self.assertIn("38.8", html)

    def test_draws_four_charts(self):
        with mock.patch("app.simulate", return_value=fixture_result()):
            html = self.html(self.post())
        for name in ("ac-magnitude", "ac-phase", "tran-input", "tran-output"):
            self.assertIn(f'data-testid="{name}"', html)

    def test_shows_the_exact_netlist_that_was_run(self):
        with mock.patch("app.simulate", return_value=fixture_result()):
            html = self.html(self.post())
        self.assertIn('data-testid="netlist"', html)
        self.assertIn(".control", html)
        self.assertIn("SIN(", html)

    def test_passes_the_netlist_to_ngspice(self):
        with mock.patch("app.simulate", return_value=fixture_result()) as runner:
            self.post()
        netlist = runner.call_args.args[0]
        self.assertIn("Q1 coll base emi QNPN", netlist)
        self.assertIn("tran ", netlist)

    def test_converts_millivolts_and_kilohertz_to_si(self):
        with mock.patch("app.simulate", return_value=fixture_result()) as runner:
            self.post(vin_amp_v="25", vin_amp_v_unit="mv", freq_hz="2", freq_hz_unit="khz")
        netlist = runner.call_args.args[0]
        self.assertIn("SIN(0 0.025 2000)", netlist)


class TestAmplifierValidation(AmplifierWebCase):
    def test_blank_amplitude_is_rejected_by_name(self):
        response = self.post(vin_amp_v="")
        self.assertEqual(response.status_code, 400)
        self.assertIn("vin_amp_v is required.", self.html(response))

    def test_zero_amplitude_is_rejected_by_name(self):
        response = self.post(vin_amp_v="0")
        self.assertEqual(response.status_code, 400)
        self.assertIn("vin_amp_v must be greater than zero.", self.html(response))

    def test_non_numeric_frequency_is_rejected_by_name(self):
        response = self.post(freq_hz="abc")
        self.assertEqual(response.status_code, 400)
        self.assertIn("freq_hz must be a number.", self.html(response))

    def test_unknown_frequency_unit_is_rejected(self):
        response = self.post(freq_hz_unit="mhz")
        self.assertEqual(response.status_code, 400)
        self.assertIn("freq_hz_unit", self.html(response))

    def test_amplitude_above_supply_is_rejected(self):
        response = self.post(vin_amp_v="20", vin_amp_v_unit="v")
        self.assertEqual(response.status_code, 400)
        self.assertIn("vin_amp_v must not exceed vcc_v.", self.html(response))

    def test_input_survives_a_validation_error(self):
        html = self.html(self.post(vin_amp_v="0", freq_hz="5"))
        self.assertIn('value="5"', html)
        self.assertIn('value="100"', html)

    def test_ngspice_is_not_started_when_input_is_invalid(self):
        with mock.patch("app.simulate", return_value=fixture_result()) as runner:
            self.post(vin_amp_v="0")
        runner.assert_not_called()


class TestSpiceFailureReporting(AmplifierWebCase):
    def test_missing_binary_returns_503_and_says_what_to_set(self):
        error = SpiceError("ngspice_con.exe was not found.", kind="missing_binary")
        with mock.patch("app.simulate", side_effect=error):
            response = self.post()
        self.assertEqual(response.status_code, 503)
        html = self.html(response)
        self.assertIn("ngspice_con.exe was not found.", html)
        self.assertIn("NGSPICE_CON", html)

    def test_timeout_returns_504(self):
        error = SpiceError("ngspice did not finish within 30 s.", kind="timeout")
        with mock.patch("app.simulate", side_effect=error):
            response = self.post()
        self.assertEqual(response.status_code, 504)

    def test_ngspice_text_is_shown_verbatim(self):
        error = SpiceError(
            "ngspice reported a problem.",
            detail="Warning: singular matrix:  check node out",
            kind="failed",
        )
        with mock.patch("app.simulate", side_effect=error):
            response = self.post()
        self.assertEqual(response.status_code, 500)
        self.assertIn("singular matrix", self.html(response))

    def test_a_failed_run_shows_no_fabricated_numbers(self):
        error = SpiceError("ngspice reported a problem.", kind="failed")
        with mock.patch("app.simulate", side_effect=error):
            response = self.post()
        html = self.html(response)
        self.assertNotIn('data-source="spice"', html)
        self.assertNotIn('data-testid="ac-gain"', html)

    def test_missing_output_is_reported(self):
        error = SpiceError("ngspice produced no data for op.txt.", kind="no_data")
        with mock.patch("app.simulate", side_effect=error):
            response = self.post()
        self.assertEqual(response.status_code, 500)
        self.assertIn("produced no data", self.html(response))


if __name__ == "__main__":
    unittest.main()
