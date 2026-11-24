"""Tests for the common-emitter amplifier netlist builder and small-signal estimate."""

import math
import unittest

from amplifier import (
    AC_POINTS_PER_DECADE,
    CE_DEFAULTS,
    ac_sweep_window,
    build_ce_netlist,
    ce_parameters,
    estimate_small_signal,
    transient_timing,
)

# Lab 3 divider defaults, used as the reference CE stage.
BASE = dict(
    vcc_v=12.0,
    r1_ohm=100_000.0,
    r2_ohm=22_000.0,
    rc_ohm=2_200.0,
    re_ohm=1_000.0,
    beta=100.0,
    vin_amp_v=0.010,
    freq_hz=1_000.0,
)

# Analytical Q-point of the same circuit, from dc_bias.calculate_voltage_divider_bias.
QPOINT = {"ie_a": 1.2396e-03, "ic_a": 1.2273e-03, "vce_v": 8.05}


def _stage(**overrides):
    return ce_parameters(**{**BASE, **overrides})


def _is_float(token):
    try:
        float(token)
    except ValueError:
        return False
    return True


def _control_numbers(netlist, command):
    """Return the numeric arguments of a control-block command as floats."""
    for line in netlist.splitlines():
        parts = line.split()
        if parts and parts[0].lower() == command:
            return [float(token) for token in parts[1:] if _is_float(token)]
    raise AssertionError(f"control command {command!r} not found")


class TestTransientTiming(unittest.TestCase):
    def test_tstep_is_positive_for_every_allowed_frequency(self):
        for freq in (1.0, 10.0, 1_000.0, 20_000.0, 1e6, 1e8):
            with self.subTest(freq=freq):
                tstep, _ = transient_timing(freq)
                self.assertGreater(tstep, 0.0)

    def test_tstop_covers_five_periods(self):
        tstep, tstop = transient_timing(1_000.0)
        self.assertAlmostEqual(tstop, 5.0 / 1_000.0, places=12)
        self.assertAlmostEqual(tstep, 1.0 / 1_000.0 / 200.0, places=15)

    def test_keeps_roughly_one_thousand_samples(self):
        for freq in (1.0, 1_000.0, 1e6):
            with self.subTest(freq=freq):
                tstep, tstop = transient_timing(freq)
                self.assertAlmostEqual(tstop / tstep, 1_000.0, delta=1.0)

    def test_rejects_non_positive_frequency(self):
        for freq in (0.0, -5.0):
            with self.subTest(freq=freq):
                with self.assertRaises(ValueError) as caught:
                    transient_timing(freq)
                self.assertIn("freq_hz", str(caught.exception))

    def test_rejects_frequency_beyond_the_model_band(self):
        with self.assertRaises(ValueError) as caught:
            transient_timing(2e8)
        self.assertIn("freq_hz", str(caught.exception))


class TestAcSweepWindow(unittest.TestCase):
    def test_window_contains_the_requested_frequency(self):
        for freq in (1.0, 1_000.0, 250_000.0, 1e8):
            with self.subTest(freq=freq):
                start, stop = ac_sweep_window(freq)
                self.assertLessEqual(start, freq)
                self.assertGreaterEqual(stop, freq)

    def test_centres_two_decades_each_side(self):
        start, stop = ac_sweep_window(1_000.0)
        self.assertAlmostEqual(start, 10.0, places=9)
        self.assertAlmostEqual(stop, 100_000.0, places=6)

    def test_clamps_to_the_supported_band(self):
        start, _ = ac_sweep_window(1.0)
        _, stop = ac_sweep_window(1e8)
        self.assertGreaterEqual(start, 1.0)
        self.assertLessEqual(stop, 1e8)

    def test_window_is_wide_enough_to_read_decibels_per_decade(self):
        self.assertEqual(AC_POINTS_PER_DECADE, 10)
        start, stop = ac_sweep_window(1_000.0)
        self.assertAlmostEqual(math.log10(stop / start), 4.0, places=9)


class TestValidation(unittest.TestCase):
    def test_zero_amplitude_names_the_field(self):
        with self.assertRaises(ValueError) as caught:
            _stage(vin_amp_v=0.0)
        self.assertEqual(
            str(caught.exception), "vin_amp_v must be greater than zero."
        )

    def test_negative_input_amplitude_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            _stage(vin_amp_v=-0.01)
        self.assertIn("vin_amp_v", str(caught.exception))

    def test_amplitude_above_supply_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            _stage(vin_amp_v=13.0)
        self.assertIn("vin_amp_v", str(caught.exception))

    def test_frequency_above_one_hundred_megahertz_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            _stage(freq_hz=2e8)
        self.assertIn("freq_hz", str(caught.exception))

    def test_zero_beta_names_the_field(self):
        with self.assertRaises(ValueError) as caught:
            _stage(beta=0.0)
        self.assertIn("beta", str(caught.exception))

    def test_fixed_passives_are_the_documented_defaults(self):
        stage = _stage()
        self.assertAlmostEqual(stage.c_in_f, CE_DEFAULTS["c_in_f"], places=12)
        self.assertAlmostEqual(stage.c_e_f, CE_DEFAULTS["c_e_f"], places=12)
        self.assertAlmostEqual(stage.load_ohm, CE_DEFAULTS["load_ohm"], places=3)


class TestNetlist(unittest.TestCase):
    def setUp(self):
        self.netlist = build_ce_netlist(_stage())

    def test_runs_a_control_block_with_all_three_analyses(self):
        self.assertIn(".control", self.netlist)
        self.assertIn("\nop\n", self.netlist)
        self.assertIn("\nac dec ", self.netlist)
        self.assertIn("\ntran ", self.netlist)

    def test_transient_command_has_positive_tstep(self):
        tstep, tstop = _control_numbers(self.netlist, "tran")
        self.assertGreater(tstep, 0.0)
        self.assertAlmostEqual(tstop, 5.0 / BASE["freq_hz"], places=12)

    def test_transient_step_is_one_two_hundredth_of_a_period(self):
        tstep, _ = _control_numbers(self.netlist, "tran")
        self.assertAlmostEqual(tstep, 1.0 / BASE["freq_hz"] / 200.0, places=15)

    def test_ac_command_uses_the_computed_window(self):
        numbers = _control_numbers(self.netlist, "ac")
        start, stop = ac_sweep_window(BASE["freq_hz"])
        self.assertEqual(numbers[0], float(AC_POINTS_PER_DECADE))
        self.assertAlmostEqual(numbers[1] / start, 1.0, places=6)
        self.assertAlmostEqual(numbers[2] / stop, 1.0, places=6)

    def test_wires_the_bias_parts_with_their_values(self):
        self.assertIn("R1 vcc base 100000", self.netlist)
        self.assertIn("R2 base 0 22000", self.netlist)
        self.assertIn("RC vcc coll 2200", self.netlist)
        self.assertIn("RE emi 0 1000", self.netlist)
        self.assertIn("Q1 coll base emi QNPN", self.netlist)

    def test_installs_the_coupling_and_bypass_capacitors(self):
        self.assertIn("C1 in base ", self.netlist)
        self.assertIn("C2 coll out ", self.netlist)
        self.assertIn("CE emi 0 ", self.netlist)

    def test_carries_beta_into_the_transistor_model(self):
        self.assertIn("BF=100", self.netlist)

    def test_source_carries_amplitude_and_frequency(self):
        line = next(l for l in self.netlist.splitlines() if l.startswith("VIN "))
        self.assertIn("SIN(", line)
        amplitude, frequency = line.split("SIN(")[1].rstrip(")").split()[1:]
        self.assertAlmostEqual(float(amplitude), BASE["vin_amp_v"], places=12)
        self.assertAlmostEqual(float(frequency), BASE["freq_hz"], places=9)

    def test_uses_no_locale_separators(self):
        self.assertNotIn(",", self.netlist)

    def test_is_pure_ascii(self):
        self.netlist.encode("ascii")

    def test_terminates_with_end_card(self):
        self.assertEqual(self.netlist.strip().splitlines()[-1], ".end")


class TestSmallSignalEstimate(unittest.TestCase):
    def setUp(self):
        self.estimate = estimate_small_signal(_stage(), QPOINT)

    def test_emitter_resistance_matches_vt_over_ie(self):
        self.assertAlmostEqual(self.estimate["re_prime_ohm"], 20.85, delta=0.1)

    def test_midband_gain_is_inverting(self):
        self.assertLess(self.estimate["gain_midband"], 0.0)

    def test_midband_gain_matches_rc_parallel_rl_over_re_prime(self):
        self.assertAlmostEqual(self.estimate["gain_midband"], -86.5, delta=1.0)

    def test_midband_gain_in_decibels(self):
        self.assertAlmostEqual(self.estimate["gain_midband_db"], 38.74, delta=0.15)

    def test_input_resistance_is_the_parallel_base_path(self):
        # R1 || R2 || (beta + 1) * re'  ~= 1.9 kOhm
        self.assertAlmostEqual(self.estimate["rin_ohm"], 1_893.0, delta=40.0)

    def test_output_resistance_is_the_collector_resistor(self):
        self.assertAlmostEqual(self.estimate["rout_ohm"], 2_200.0, places=6)

    def test_estimate_refuses_a_dead_emitter_current(self):
        with self.assertRaises(ValueError) as caught:
            estimate_small_signal(_stage(), {"ie_a": 0.0, "ic_a": 0.0, "vce_v": 12.0})
        self.assertIn("ie_a", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
