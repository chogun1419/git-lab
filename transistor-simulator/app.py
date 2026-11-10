"""Flask routes for the transistor DC bias simulator."""

from flask import Flask, render_template, request

from dc_bias import DEFAULT_VBE_V, calculate_voltage_divider_bias

FIELD_NAMES = ("vcc_v", "r1_ohm", "r2_ohm", "rc_ohm", "re_ohm", "beta", "vbe_v")

DEFAULT_VALUES = {
    "vcc_v": "12",
    "r1_ohm": "47000",
    "r2_ohm": "10000",
    "rc_ohm": "4700",
    "re_ohm": "1000",
    "beta": "150",
    "vbe_v": str(DEFAULT_VBE_V),
}

REGION_LABELS = {
    "active": "Active — ช่วงขยายสัญญาณ",
    "saturation": "Saturation — อิ่มตัว",
    "cutoff": "Cutoff — ตัดขาด",
}


def _parse_form(values: dict[str, str]) -> dict[str, float]:
    """Turn the raw form strings into floats, naming the offending field."""
    numbers: dict[str, float] = {}
    for name in FIELD_NAMES:
        raw = values.get(name, "").strip()
        if not raw:
            if name == "vbe_v":
                numbers[name] = DEFAULT_VBE_V
                continue
            raise ValueError(f"{name} is required.")
        try:
            numbers[name] = float(raw)
        except ValueError:
            raise ValueError(f"{name} must be a number.") from None
    return numbers


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template(
            "index.html", values=DEFAULT_VALUES, result=None, error=None
        )

    @app.post("/calculate")
    def calculate():
        values = {name: request.form.get(name, "") for name in FIELD_NAMES}
        try:
            result = calculate_voltage_divider_bias(**_parse_form(values))
        except ValueError as error:
            return (
                render_template(
                    "index.html", values=values, result=None, error=str(error)
                ),
                400,
            )

        return render_template(
            "index.html",
            values=values,
            result=result,
            error=None,
            region_label=REGION_LABELS[result["region"]],
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
