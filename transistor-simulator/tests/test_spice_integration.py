"""Real ngspice round trip for the reference stage.

Skipped, and skipped loudly, when ngspice is not installed on this machine.
Nothing here is mocked: the numbers come from an actual subprocess.
"""

import unittest

from amplifier import build_ce_netlist, ce_parameters
from dc_bias import calculate_voltage_divider_bias
from spice_runner import find_ngspice, peak_to_peak, sample_at, simulate

NGSPICE = find_ngspice()

DEFAULTS = dict(
    vcc_v=12.0,
    r1_ohm=100_000.0,
    r2_ohm=22_000.0,
    rc_ohm=2_200.0,
    re_ohm=1_000.0,
    beta=100.0,
    vin_amp_v=0.010,
    freq_hz=1_000.0,
)


@unittest.skipUnless(NGSPICE, "ngspice is not installed on this machine")
class TestRealNgspiceRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage = ce_parameters(**DEFAULTS)
        cls.result = simulate(build_ce_netlist(cls.stage), binary=NGSPICE)
        cls.analytical = calculate_voltage_divider_bias(**{
            key: value
            for key, value in DEFAULTS.items()
            if key in {"vcc_v", "r1_ohm", "r2_ohm", "rc_ohm", "re_ohm", "beta"}
        })

    def assertWithin(self, actual, expected, fraction, label):
        tolerance = abs(expected) * fraction
        self.assertAlmostEqual(actual, expected, delta=tolerance, msg=label)

    def test_operating_point_agrees_with_the_analytical_bias(self):
        # The model's Vbe is computed, not fixed at 0.70 V, so a few percent
        # of drift is expected and is reported on the page rather than hidden.
        self.assertWithin(self.result.op["vb_v"], self.analytical["vb_v"], 0.05, "V_B")
        self.assertWithin(self.result.op["ve_v"], self.analytical["ve_v"], 0.05, "V_E")
        self.assertWithin(self.result.op["vc_v"], self.analytical["vc_v"], 0.05, "V_C")

    def test_analytical_q_point_is_still_the_active_region(self):
        self.assertEqual(self.analytical["region"], "active")

    def test_ac_sweep_came_back_with_data(self):
        self.assertGreater(len(self.result.ac["freq_hz"]), 10)
        self.assertEqual(
            len(self.result.ac["freq_hz"]), len(self.result.ac["gain_db"])
        )

    def test_gain_at_the_requested_frequency_is_plausible(self):
        point = sample_at(self.result.ac, DEFAULTS["freq_hz"])
        self.assertGreater(point["gain_db"], 20.0)
        self.assertLess(point["gain_db"], 60.0)
        self.assertLess(point["phase_deg"], -90.0)

    def test_transient_returned_a_full_run(self):
        self.assertGreater(len(self.result.tran["time_s"]), 100)
        self.assertAlmostEqual(
            self.result.tran["time_s"][-1], 5.0 / DEFAULTS["freq_hz"], places=9
        )
        self.assertGreater(self.result.tran["time_s"][1], 0.0)

    def test_transient_swing_matches_the_ac_gain(self):
        half = len(self.result.tran["time_s"]) // 2
        swing_out = peak_to_peak(self.result.tran["vout_v"][half:])
        swing_in = peak_to_peak(self.result.tran["vin_v"][half:])
        self.assertAlmostEqual(swing_in, 2 * DEFAULTS["vin_amp_v"], delta=1e-4)
        ac_gain = 10 ** (sample_at(self.result.ac, DEFAULTS["freq_hz"])["gain_db"] / 20)
        self.assertAlmostEqual(swing_out / swing_in, ac_gain, delta=ac_gain * 0.05)

    def test_console_output_is_kept_for_display(self):
        self.assertIn("ngspice", self.result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
