"""Flask routes for the transistor DC bias simulator."""

from flask import Flask, render_template, request

from dc_bias import DEFAULT_VBE_V, calculate_voltage_divider_bias

RESISTOR_FIELDS = {"r1": "r1_ohm", "r2": "r2_ohm", "rc": "rc_ohm", "re": "re_ohm"}
SCALAR_FIELDS = ("vcc_v", "beta", "vbe_v")
UNIT_SCALE = {"ohm": 1.0, "kohm": 1000.0}

FIELD_NAMES = (
    "vcc_v",
    "r1",
    "r1_unit",
    "r2",
    "r2_unit",
    "rc",
    "rc_unit",
    "re",
    "re_unit",
    "beta",
    "vbe_v",
)

DEFAULT_VALUES = {
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
    "vbe_v": "0.70",
}

REGION_LABELS = {
    "active": "Active region",
    "saturation": "Saturation region",
    "cutoff": "Cutoff region",
}

STATUS_TITLES = {
    "active": "Active region OK",
    "saturation": "Saturation region",
    "cutoff": "Cutoff region",
}


def _to_float(name: str, raw: str) -> float:
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"{name} must be a number.") from None


def _parse_form(values: dict[str, str]) -> dict[str, float]:
    """Turn raw form strings into base units, naming the offending field."""
    numbers: dict[str, float] = {}

    for name in SCALAR_FIELDS:
        raw = values.get(name, "").strip()
        if not raw:
            if name == "vbe_v":
                numbers[name] = DEFAULT_VBE_V
                continue
            raise ValueError(f"{name} is required.")
        numbers[name] = _to_float(name, raw)

    for field, target in RESISTOR_FIELDS.items():
        raw = values.get(field, "").strip()
        if not raw:
            raise ValueError(f"{field} is required.")
        unit = values.get(f"{field}_unit", "").strip()
        if unit not in UNIT_SCALE:
            raise ValueError(f"{field}_unit must be ohm or kohm.")
        numbers[target] = _to_float(field, raw) * UNIT_SCALE[unit]

    return numbers


def _unit_labels(values: dict[str, str]) -> dict[str, str]:
    return {
        field: ("kΩ" if values.get(f"{field}_unit") == "kohm" else "Ω")
        for field in RESISTOR_FIELDS
    }


def _status(result: dict[str, float | str]) -> tuple[str, str]:
    region = result["region"]
    if region == "active":
        detail = (
            f"V_CE = {result['vce_v']:.2f} V > 0.2 V "
            "(transistor in active region)"
        )
    elif region == "saturation":
        detail = (
            f"I_C limited to I_C(sat) ≈ {result['ic_sat_a'] * 1000:.2f} mA; "
            "V_CE ≈ 0.2 V"
        )
    else:
        detail = "V_BB ≤ V_BE, so I_B = I_C = I_E = 0"
    return STATUS_TITLES[region], detail


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        values = dict(DEFAULT_VALUES)
        return render_template(
            "index.html",
            values=values,
            unit_labels=_unit_labels(values),
            result=None,
            error=None,
        )

    @app.post("/calculate")
    def calculate():
        values = {name: request.form.get(name, "") for name in FIELD_NAMES}
        unit_labels = _unit_labels(values)
        try:
            result = calculate_voltage_divider_bias(**_parse_form(values))
        except ValueError as error:
            return (
                render_template(
                    "index.html",
                    values=values,
                    unit_labels=unit_labels,
                    result=None,
                    error=str(error),
                ),
                400,
            )

        status_title, status_detail = _status(result)
        return render_template(
            "index.html",
            values=values,
            unit_labels=unit_labels,
            result=result,
            error=None,
            region_label=REGION_LABELS[result["region"]],
            status_title=status_title,
            status_detail=status_detail,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
