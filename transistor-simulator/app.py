"""Flask routes for the transistor DC bias simulator."""

from flask import Flask, render_template, request

from amplifier import (
    CE_DEFAULTS,
    build_ce_netlist,
    ce_parameters,
    estimate_small_signal,
)
from dc_bias import DEFAULT_VBE_V, calculate_bias, calculate_voltage_divider_bias
from plots import build_chart
from spice_runner import SpiceError, peak_to_peak, sample_at, simulate

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


# --- Common-emitter amplifier page -------------------------------------------
#
# The amplifier reuses the same bias inputs, so the form values go through
# _parse_form() and only the two new quantities are converted here.

AMPLIFIER_FIELD_NAMES = (
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
    "vin_amp_v",
    "vin_amp_v_unit",
    "freq_hz",
    "freq_hz_unit",
)

AMPLITUDE_SCALE = {"mv": 1e-3, "v": 1.0}
FREQUENCY_SCALE = {"hz": 1.0, "khz": 1e3}

AMPLIFIER_DEFAULTS = {
    "vcc_v": DEFAULT_VALUES["vcc_v"],
    "r1": DEFAULT_VALUES["r1"],
    "r1_unit": DEFAULT_VALUES["r1_unit"],
    "r2": DEFAULT_VALUES["r2"],
    "r2_unit": DEFAULT_VALUES["r2_unit"],
    "rc": DEFAULT_VALUES["rc"],
    "rc_unit": DEFAULT_VALUES["rc_unit"],
    "re": DEFAULT_VALUES["re"],
    "re_unit": DEFAULT_VALUES["re_unit"],
    "beta": DEFAULT_VALUES["beta"],
    "vin_amp_v": "10",
    "vin_amp_v_unit": "mv",
    "freq_hz": "1",
    "freq_hz_unit": "khz",
}

SPICE_STATUS = {
    "missing_binary": 503,
    "timeout": 504,
    "failed": 500,
    "no_data": 500,
}

SPICE_HINTS = {
    "missing_binary": (
        "Set the NGSPICE_CON environment variable to the full path of "
        r"ngspice_con.exe (for example C:\Users\you\Spice64\bin\ngspice_con.exe) "
        "and restart the app."
    ),
    "timeout": "The netlist was still running when the limit expired; no traces are shown.",
    "failed": "This is ngspice's own output. No simulation numbers are displayed.",
    "no_data": "ngspice finished but returned no vectors, so there is nothing to plot.",
}


def _parse_quantity(
    values: dict[str, str], field: str, scales: dict[str, float], allowed: str
) -> float:
    raw = values.get(field, "").strip()
    if not raw:
        raise ValueError(f"{field} is required.")
    value = _to_float(field, raw)
    if value < 0:
        raise ValueError(f"{field} must not be negative.")
    unit = values.get(f"{field}_unit", "").strip()
    if unit not in scales:
        raise ValueError(f"{field}_unit must be {allowed}.")
    return value * scales[unit]


def _parse_amplifier_form(values: dict[str, str]) -> dict[str, float]:
    """Return the bias inputs plus amplitude and frequency in SI units."""
    _, numbers = _parse_form({**values, "mode": "divider"})
    numbers.pop("vbe_v", None)  # the amplifier's transistor model computes V_BE
    numbers["vin_amp_v"] = _parse_quantity(
        values, "vin_amp_v", AMPLITUDE_SCALE, "mv or v"
    )
    numbers["freq_hz"] = _parse_quantity(values, "freq_hz", FREQUENCY_SCALE, "hz or khz")
    return numbers


def _amplifier_context(
    stage, sim, netlist: str
) -> dict[str, object]:
    """Assemble everything the template shows, keeping the two sources apart."""
    analytical = calculate_voltage_divider_bias(
        vcc_v=stage.vcc_v,
        r1_ohm=stage.r1_ohm,
        r2_ohm=stage.r2_ohm,
        rc_ohm=stage.rc_ohm,
        re_ohm=stage.re_ohm,
        beta=stage.beta,
    )
    try:
        estimate = estimate_small_signal(stage, analytical)
    except ValueError:
        estimate = None  # cutoff: no small-signal model exists

    point = sample_at(sim.ac, stage.freq_hz)
    half = len(sim.tran["time_s"]) // 2
    status_title, status_detail = _status(analytical, "divider")

    return {
        "stage": stage,
        "sim": sim,
        "analytical": analytical,
        "estimate": estimate,
        "point": point,
        "swing_in_v": peak_to_peak(sim.tran["vin_v"][half:]),
        "swing_out_v": peak_to_peak(sim.tran["vout_v"][half:]),
        "charts": {
            "magnitude": build_chart(
                [sim.ac["gain_db"]], sim.ac["freq_hz"], x_scale="log"
            ),
            "phase": build_chart(
                [sim.ac["phase_deg"]], sim.ac["freq_hz"], x_scale="log"
            ),
            "tran_in": build_chart(
                [sim.tran["vin_v"]], sim.tran["time_s"], x_scale="linear"
            ),
            "tran_out": build_chart(
                [sim.tran["vout_v"]], sim.tran["time_s"], x_scale="linear"
            ),
        },
        "netlist": netlist,
        "status_title": status_title,
        "status_detail": status_detail,
        "region_label": REGION_LABELS[analytical["region"]],
        "fixed_passives": [
            ("C1 (input coupling)", f"{CE_DEFAULTS['c_in_f'] * 1e6:g} µF"),
            ("C2 (output coupling)", f"{CE_DEFAULTS['c_out_f'] * 1e6:g} µF"),
            ("CE (emitter bypass)", f"{CE_DEFAULTS['c_e_f'] * 1e6:g} µF"),
            ("RL (load)", f"{CE_DEFAULTS['load_ohm'] / 1e3:g} kΩ"),
        ],
        "error": None,
        "detail": None,
        "hint": None,
    }


def _render_amplifier(values: dict[str, str], **context):
    return render_template(
        "amplifier.html",
        values=values,
        unit_labels=_unit_labels(values),
        **context,
    )


def _register_filters(app: Flask) -> None:
    @app.template_filter("hz")
    def _format_hz(value: float) -> str:
        if value >= 1e6:
            return f"{value / 1e6:g} MHz"
        if value >= 1e3:
            return f"{value / 1e3:g} kHz"
        return f"{value:g} Hz"

    @app.template_filter("db")
    def _format_db(value: float) -> str:
        return f"{value:.1f} dB"

    @app.template_filter("deg")
    def _format_deg(value: float) -> str:
        return f"{value:.1f}°"

    @app.template_filter("duration")
    def _format_duration(value: float) -> str:
        if value >= 1e-3:
            return f"{value * 1e3:.2f} ms"
        if value >= 1e-6:
            return f"{value * 1e6:.1f} µs"
        return f"{value * 1e9:.1f} ns"

    @app.template_filter("volts")
    def _format_volts(value: float) -> str:
        if abs(value) >= 1:
            return f"{value:.2f} V"
        return f"{value * 1e3:.1f} mV"

    @app.template_filter("tick")
    def _format_tick(value: float) -> str:
        if abs(value) >= 100:
            return f"{value:.0f}"
        if abs(value) >= 1:
            return f"{value:.1f}"
        return f"{value:.2f}"


def create_app() -> Flask:
    app = Flask(__name__)
    _register_filters(app)

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

    @app.get("/amplifier")
    def amplifier_page():
        values = dict(AMPLIFIER_DEFAULTS)
        return _render_amplifier(values)

    @app.post("/amplifier/simulate")
    def amplifier_simulate():
        values = {name: request.form.get(name, "") for name in AMPLIFIER_FIELD_NAMES}

        try:
            numbers = _parse_amplifier_form(values)
            stage = ce_parameters(**numbers)
        except ValueError as error:
            return _render_amplifier(values, error=str(error), detail=None, hint=None), 400

        netlist = build_ce_netlist(stage)

        try:
            sim = simulate(netlist)
        except SpiceError as error:
            return (
                _render_amplifier(
                    values,
                    error=error.message,
                    detail=error.detail,
                    hint=SPICE_HINTS.get(error.kind),
                    netlist=netlist,
                ),
                SPICE_STATUS.get(error.kind, 500),
            )

        return _render_amplifier(values, **_amplifier_context(stage, sim, netlist))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
