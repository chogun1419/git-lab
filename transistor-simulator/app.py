"""Flask routes for the transistor DC bias simulator."""

from flask import Flask, render_template, request

from dc_bias import DEFAULT_VBE_V, calculate_bias

RESISTOR_FIELDS = {
    "r1": "r1_ohm",
    "r2": "r2_ohm",
    "rb": "rb_ohm",
    "rc": "rc_ohm",
    "re": "re_ohm",
}
UNIT_SCALE = {"ohm": 1.0, "kohm": 1000.0}

FIELD_NAMES = (
    "mode",
    "vcc_v",
    "r1",
    "r1_unit",
    "r2",
    "r2_unit",
    "rb",
    "rb_unit",
    "rc",
    "rc_unit",
    "re",
    "re_unit",
    "beta",
    "vbe_v",
)

# Fields each mode needs. Anything not listed is ignored for that mode.
MODE_FIELDS = {
    "divider": ("vcc_v", "r1", "r2", "rc", "re", "beta", "vbe_v"),
    "fixed": ("vcc_v", "rb", "rc", "beta", "vbe_v"),
    "emitter": ("vcc_v", "rb", "rc", "re", "beta", "vbe_v"),
}

MODE_LABELS = {
    "divider": "Voltage Divider Bias",
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
}

DEFAULT_VALUES = {
    "mode": "divider",
    "vcc_v": "12",
    "r1": "100",
    "r1_unit": "kohm",
    "r2": "22",
    "r2_unit": "kohm",
    "rb": "470",
    "rb_unit": "kohm",
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


def _parse_form(values: dict[str, str]) -> tuple[str, dict[str, float]]:
    """Return the selected mode and its inputs in base SI units.

    Blank fields are rejected (except V_BE, which falls back to the default),
    negative values are rejected, and resistor values are scaled from the
    chosen ohm/kohm unit.
    """
    mode = values.get("mode", "").strip() or "divider"
    if mode not in MODE_FIELDS:
        raise ValueError("mode must be divider, fixed, or emitter.")

    numbers: dict[str, float] = {}

    for name in MODE_FIELDS[mode]:
        raw = values.get(name, "").strip()
        if not raw:
            if name == "vbe_v":
                numbers[name] = DEFAULT_VBE_V
                continue
            raise ValueError(f"{name} is required.")

        value = _to_float(name, raw)
        if value < 0:
            raise ValueError(f"{name} must not be negative.")

        if name in RESISTOR_FIELDS:
            unit = values.get(f"{name}_unit", "").strip()
            if unit not in UNIT_SCALE:
                raise ValueError(f"{name}_unit must be ohm or kohm.")
            numbers[RESISTOR_FIELDS[name]] = value * UNIT_SCALE[unit]
        else:
            numbers[name] = value

    return mode, numbers


def _unit_labels(values: dict[str, str]) -> dict[str, str]:
    return {
        field: ("kΩ" if values.get(f"{field}_unit") == "kohm" else "Ω")
        for field in RESISTOR_FIELDS
    }


def _status(result: dict[str, float | str], mode: str) -> tuple[str, str]:
    region = result["region"]
    if region == "active":
        detail = (
            f"V_CE = {result['vce_v']:.2f} V > 0.2 V "
            "(transistor in active region)"
        )
    elif region == "saturation":
        limit = f"I_C limited to I_C(sat) ≈ {result['ic_sat_a'] * 1000:.2f} mA"
        if mode == "divider":
            detail = f"{limit}; V_CE ≈ 0.2 V"
        else:
            detail = f"Warning: transistor saturated; {limit}, V_CE ≤ 0.2 V"
    else:
        if mode == "divider":
            detail = "V_BB ≤ V_BE, so I_B = I_C = I_E = 0"
        else:
            detail = (
                "Warning: I_B ≤ 0, base drive too small, "
                "so I_B = I_C = I_E = 0"
            )
    return STATUS_TITLES[region], detail


def _render(values: dict[str, str], mode: str, **context):
    return render_template(
        "index.html",
        values=values,
        mode=mode,
        mode_label=MODE_LABELS[mode],
        unit_labels=_unit_labels(values),
        **context,
    )


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        values = dict(DEFAULT_VALUES)
        return _render(values, values["mode"], result=None, error=None)

    @app.post("/calculate")
    def calculate():
        values = {name: request.form.get(name, "") for name in FIELD_NAMES}

        mode = values.get("mode", "").strip()
        if mode not in MODE_FIELDS:
            mode = "divider"

        try:
            mode, numbers = _parse_form(values)
            result = calculate_bias(mode, **numbers)
        except ValueError as error:
            return _render(values, mode, result=None, error=str(error)), 400

        status_title, status_detail = _status(result, mode)
        return _render(
            values,
            mode,
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
