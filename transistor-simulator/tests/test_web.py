import unittest

from app import create_app

VALID_FORM = {
    "vcc_v": "12",
    "r1_ohm": "47000",
    "r2_ohm": "10000",
    "rc_ohm": "4700",
    "re_ohm": "1000",
    "beta": "150",
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
        response = self.client.get("/")
        for field in ("vcc_v", "r1_ohm", "r2_ohm", "rc_ohm", "re_ohm", "beta"):
            self.assertIn(f'name="{field}"', response.get_data(as_text=True))


class TestCalculationRoute(WebTestCase):
    def test_valid_submission_returns_200(self):
        response = self.client.post("/calculate", data=VALID_FORM)
        self.assertEqual(response.status_code, 200)

    def test_valid_submission_shows_active_region(self):
        response = self.client.post("/calculate", data=VALID_FORM)
        self.assertIn('data-region="active"', response.get_data(as_text=True))

    def test_valid_submission_shows_operating_point_values(self):
        html = self.client.post("/calculate", data=VALID_FORM).get_data(as_text=True)
        self.assertIn("4.446", html)  # Vce in volts
        self.assertIn("1.324", html)  # Ic in milliamps
        self.assertIn("8.825", html)  # Ib in microamps

    def test_cutoff_submission_is_reported(self):
        form = {**VALID_FORM, "r1_ohm": "100000", "r2_ohm": "1000"}
        html = self.client.post("/calculate", data=form).get_data(as_text=True)
        self.assertIn('data-region="cutoff"', html)

    def test_saturation_submission_is_reported(self):
        form = {**VALID_FORM, "rc_ohm": "47000", "re_ohm": "100"}
        html = self.client.post("/calculate", data=form).get_data(as_text=True)
        self.assertIn('data-region="saturation"', html)


class TestInvalidInput(WebTestCase):
    def test_zero_resistance_returns_400(self):
        response = self.client.post("/calculate", data={**VALID_FORM, "r1_ohm": "0"})
        self.assertEqual(response.status_code, 400)

    def test_zero_resistance_explains_the_error(self):
        response = self.client.post("/calculate", data={**VALID_FORM, "r1_ohm": "0"})
        self.assertIn("r1_ohm", response.get_data(as_text=True))

    def test_missing_field_returns_400(self):
        form = dict(VALID_FORM)
        del form["beta"]
        response = self.client.post("/calculate", data=form)
        self.assertEqual(response.status_code, 400)

    def test_non_numeric_field_returns_400(self):
        response = self.client.post("/calculate", data={**VALID_FORM, "vcc_v": "abc"})
        self.assertEqual(response.status_code, 400)

    def test_invalid_input_keeps_the_typed_values(self):
        response = self.client.post("/calculate", data={**VALID_FORM, "r1_ohm": "0"})
        html = response.get_data(as_text=True)
        self.assertIn('value="0"', html)  # the rejected value stays in the box
        self.assertIn('value="12"', html)  # untouched fields keep their values


if __name__ == "__main__":
    unittest.main()
