import unittest

from app import create_app

VALID_FORM = {
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
    "vbe_v": "0.7",
}


class WebTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()


class TestIndexPage(WebTestCase):
    def test_returns_200(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_contains_the_input_form(self):
        html = self.client.get("/").get_data(as_text=True)
        for field in ("vcc_v", "r1", "r2", "rc", "re", "beta", "vbe_v"):
            self.assertIn(f'name="{field}"', html)

    def test_contains_unit_selectors(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn('name="r1_unit"', html)
        self.assertIn('value="kohm"', html)
        self.assertIn('value="ohm"', html)

    def test_contains_the_circuit_diagram(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn('data-testid="circuit"', html)

    def test_circuit_shows_the_default_component_values(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("100 kΩ", html)
        self.assertIn("2.2 kΩ", html)

    def test_has_the_lab_heading(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("Lab 02", html)


class TestCalculationRoute(WebTestCase):
    def test_valid_submission_returns_200(self):
        response = self.client.post("/calculate", data=VALID_FORM)
        self.assertEqual(response.status_code, 200)

    def test_valid_submission_shows_active_region(self):
        response = self.client.post("/calculate", data=VALID_FORM)
        self.assertIn('data-region="active"', response.get_data(as_text=True))

    def test_valid_submission_shows_operating_point_values(self):
        html = self.client.post("/calculate", data=VALID_FORM).get_data(as_text=True)
        self.assertIn("8.05", html)  # Vce in volts
        self.assertIn("1.23", html)  # Ic in milliamps
        self.assertIn("12.30", html)  # Ib in microamps

    def test_kilohm_values_are_converted_before_calculation(self):
        as_kohm = self.client.post("/calculate", data=VALID_FORM).get_data(as_text=True)
        as_ohm = self.client.post(
            "/calculate", data={**VALID_FORM, "r1": "100000", "r1_unit": "ohm"}
        ).get_data(as_text=True)
        self.assertIn("8.05", as_kohm)
        self.assertIn("8.05", as_ohm)

    def test_circuit_labels_follow_the_submitted_values(self):
        form = {**VALID_FORM, "r1": "47"}
        html = self.client.post("/calculate", data=form).get_data(as_text=True)
        self.assertIn("47 kΩ", html)

    def test_cutoff_submission_is_reported(self):
        form = {**VALID_FORM, "r1": "100", "r2": "1"}
        html = self.client.post("/calculate", data=form).get_data(as_text=True)
        self.assertIn('data-region="cutoff"', html)

    def test_saturation_submission_is_reported(self):
        form = {**VALID_FORM, "rc": "47", "re": "0.1"}
        html = self.client.post("/calculate", data=form).get_data(as_text=True)
        self.assertIn('data-region="saturation"', html)

    def test_active_status_explains_the_threshold(self):
        html = self.client.post("/calculate", data=VALID_FORM).get_data(as_text=True)
        self.assertIn("0.2 V", html)


class TestInvalidInput(WebTestCase):
    def test_zero_resistance_returns_400(self):
        response = self.client.post("/calculate", data={**VALID_FORM, "r1": "0"})
        self.assertEqual(response.status_code, 400)

    def test_zero_resistance_explains_the_error(self):
        response = self.client.post("/calculate", data={**VALID_FORM, "r1": "0"})
        self.assertIn("r1", response.get_data(as_text=True))

    def test_missing_field_returns_400(self):
        form = dict(VALID_FORM)
        del form["beta"]
        response = self.client.post("/calculate", data=form)
        self.assertEqual(response.status_code, 400)

    def test_non_numeric_field_returns_400(self):
        response = self.client.post("/calculate", data={**VALID_FORM, "vcc_v": "abc"})
        self.assertEqual(response.status_code, 400)

    def test_unknown_unit_returns_400(self):
        response = self.client.post(
            "/calculate", data={**VALID_FORM, "r1_unit": "mohm"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("r1_unit", response.get_data(as_text=True))

    def test_missing_unit_returns_400(self):
        form = dict(VALID_FORM)
        del form["r1_unit"]
        response = self.client.post("/calculate", data=form)
        self.assertEqual(response.status_code, 400)

    def test_invalid_input_keeps_the_typed_values(self):
        response = self.client.post("/calculate", data={**VALID_FORM, "r1": "0"})
        html = response.get_data(as_text=True)
        self.assertIn('value="0"', html)  # the rejected value stays in the box
        self.assertIn('value="12"', html)  # untouched fields keep their values


if __name__ == "__main__":
    unittest.main()
