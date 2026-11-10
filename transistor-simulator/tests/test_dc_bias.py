import unittest

from dc_bias import calculate_voltage_divider_bias


class TestVoltageDividerBias(unittest.TestCase):
    """Known-value checks against hand calculations for the standard circuit."""

    def setUp(self):
        # Vcc = 12 V, R1 = 47k, R2 = 10k, Rc = 4.7k, Re = 1k, beta = 150
        self.result = calculate_voltage_divider_bias(
            vcc_v=12.0,
            r1_ohm=47_000.0,
            r2_ohm=10_000.0,
            rc_ohm=4_700.0,
            re_ohm=1_000.0,
            beta=150.0,
        )

    def test_thevenin_base_voltage(self):
        self.assertAlmostEqual(self.result["vbb_v"], 2.105263, places=5)

    def test_base_current(self):
        self.assertAlmostEqual(self.result["ib_a"], 8.8247e-06, delta=1e-9)

    def test_collector_and_emitter_current(self):
        self.assertAlmostEqual(self.result["ic_a"], 1.323675e-03, delta=1e-7)
        self.assertAlmostEqual(self.result["ie_a"], 1.332500e-03, delta=1e-7)

    def test_node_voltages(self):
        self.assertAlmostEqual(self.result["vb_v"], 2.03250, places=4)
        self.assertAlmostEqual(self.result["ve_v"], 1.33250, places=4)
        self.assertAlmostEqual(self.result["vc_v"], 5.77873, places=4)
        self.assertAlmostEqual(self.result["vce_v"], 4.44623, places=4)

    def test_transistor_dissipation(self):
        self.assertAlmostEqual(self.result["power_w"], 5.88536e-03, delta=1e-6)

    def test_operating_region_is_active(self):
        self.assertEqual(self.result["region"], "active")

    def test_currents_obey_transistor_relation(self):
        self.assertAlmostEqual(
            self.result["ie_a"], self.result["ib_a"] + self.result["ic_a"], places=12
        )

    def test_default_vbe_is_0_7(self):
        with_default = calculate_voltage_divider_bias(
            vcc_v=12.0,
            r1_ohm=47_000.0,
            r2_ohm=10_000.0,
            rc_ohm=4_700.0,
            re_ohm=1_000.0,
            beta=150.0,
        )
        self.assertAlmostEqual(with_default["vce_v"], self.result["vce_v"], places=12)


class TestOperatingRegions(unittest.TestCase):
    def test_cutoff_when_base_voltage_below_vbe(self):
        # R2 much smaller than R1 pulls the base below 0.7 V.
        result = calculate_voltage_divider_bias(
            vcc_v=12.0,
            r1_ohm=100_000.0,
            r2_ohm=1_000.0,
            rc_ohm=4_700.0,
            re_ohm=1_000.0,
            beta=150.0,
        )
        self.assertEqual(result["region"], "cutoff")
        self.assertEqual(result["ib_a"], 0.0)
        self.assertEqual(result["ic_a"], 0.0)
        self.assertEqual(result["ie_a"], 0.0)
        self.assertAlmostEqual(result["vce_v"], 12.0, places=6)

    def test_saturation_when_collector_resistor_too_large(self):
        # Ic * Rc drives Vc below Ve, so the transistor cannot stay in active mode.
        result = calculate_voltage_divider_bias(
            vcc_v=12.0,
            r1_ohm=47_000.0,
            r2_ohm=10_000.0,
            rc_ohm=47_000.0,
            re_ohm=100.0,
            beta=150.0,
        )
        self.assertEqual(result["region"], "saturation")
        self.assertAlmostEqual(result["vce_v"], 0.2, delta=0.01)
        self.assertGreater(result["vc_v"], 0.0)
        self.assertGreater(result["power_w"], 0.0)

    def test_saturation_current_is_clamped_to_the_physical_limit(self):
        result = calculate_voltage_divider_bias(
            vcc_v=12.0,
            r1_ohm=47_000.0,
            r2_ohm=10_000.0,
            rc_ohm=47_000.0,
            re_ohm=100.0,
            beta=150.0,
        )
        # (Vcc - Vce_sat) / (Rc + Re)
        self.assertAlmostEqual(result["ic_sat_a"], 11.8 / 47_100.0, places=9)
        self.assertAlmostEqual(result["ic_a"], result["ic_sat_a"], places=12)
        self.assertAlmostEqual(result["ie_a"], result["ic_a"] + result["ib_a"], places=12)


class TestInputValidation(unittest.TestCase):
    BASE = dict(
        vcc_v=12.0,
        r1_ohm=47_000.0,
        r2_ohm=10_000.0,
        rc_ohm=4_700.0,
        re_ohm=1_000.0,
        beta=150.0,
    )

    def test_rejects_zero_r1(self):
        with self.assertRaises(ValueError):
            calculate_voltage_divider_bias(**{**self.BASE, "r1_ohm": 0.0})

    def test_rejects_negative_r2(self):
        with self.assertRaises(ValueError):
            calculate_voltage_divider_bias(**{**self.BASE, "r2_ohm": -1.0})

    def test_rejects_zero_rc(self):
        with self.assertRaises(ValueError):
            calculate_voltage_divider_bias(**{**self.BASE, "rc_ohm": 0.0})

    def test_rejects_negative_re(self):
        with self.assertRaises(ValueError):
            calculate_voltage_divider_bias(**{**self.BASE, "re_ohm": -1.0})

    def test_rejects_zero_beta(self):
        with self.assertRaises(ValueError):
            calculate_voltage_divider_bias(**{**self.BASE, "beta": 0.0})

    def test_rejects_zero_vcc(self):
        with self.assertRaises(ValueError):
            calculate_voltage_divider_bias(**{**self.BASE, "vcc_v": 0.0})

    def test_rejects_vbe_not_below_vcc(self):
        with self.assertRaises(ValueError):
            calculate_voltage_divider_bias(**{**self.BASE, "vbe_v": 12.0})

    def test_error_message_names_the_field(self):
        with self.assertRaises(ValueError) as caught:
            calculate_voltage_divider_bias(**{**self.BASE, "beta": 0.0})
        self.assertIn("beta", str(caught.exception).lower())


if __name__ == "__main__":
    unittest.main()
