"""DC bias calculations for BJT bias circuits.

Voltage divider (Thevenin equivalent of the base divider):

    Vbb = Vcc * R2 / (R1 + R2)
    Rb  = R1 || R2
    Ib  = (Vbb - Vbe) / (Rb + (beta + 1) * Re)
    Ic  = beta * Ib
    Ie  = (beta + 1) * Ib
    Vce = Vcc - Ic * Rc - Ie * Re

Fixed bias (base resistor from Vcc, emitter grounded):

    Ib  = (Vcc - Vbe) / Rb
    Ic  = beta * Ib
    Ie  = (beta + 1) * Ib
    Vce = Vcc - Ic * Rc

Emitter bias (base resistor from Vcc, emitter resistor to ground):

    Ib  = (Vcc - Vbe) / (Rb + (beta + 1) * Re)
    Ic  = beta * Ib
    Ie  = (beta + 1) * Ib
    Ve  = Ie * Re
    Vce = Vcc - Ic * Rc - Ve

Assumptions: Vbe constant (default 0.7 V) and no Early effect. When the bias
equations predict Vce below VCE_SAT_V the result is clamped to the saturation
point (Ic = Ic(sat), Vce ~ 0.2 V) so the reported node voltages stay physical.
"""

VCE_SAT_V = 0.2
DEFAULT_VBE_V = 0.7


def _require_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")


def _require_positive_input(name: str, value: float) -> None:
    """Reject negative and zero values with distinct, field-named messages."""
    if value < 0:
        raise ValueError(f"{name} must not be negative.")
    if value == 0:
        raise ValueError(f"{name} must be greater than zero.")


def _validate_common(vcc_v: float, beta: float, vbe_v: float) -> None:
    _require_positive_input("vcc_v", vcc_v)
    _require_positive_input("beta", beta)
    if vbe_v < 0:
        raise ValueError("vbe_v must not be negative.")
    if vbe_v >= vcc_v:
        raise ValueError("vbe_v must be less than vcc_v.")


def calculate_voltage_divider_bias(
    vcc_v: float,
    r1_ohm: float,
    r2_ohm: float,
    rc_ohm: float,
    re_ohm: float,
    beta: float,
    vbe_v: float = DEFAULT_VBE_V,
) -> dict[str, float | str]:
    """Return the quiescent point and operating region of the circuit.

    Raises ValueError when a component value is physically impossible.
    """
    _require_positive("vcc_v", vcc_v)
    _require_positive("r1_ohm", r1_ohm)
    _require_positive("r2_ohm", r2_ohm)
    _require_positive("rc_ohm", rc_ohm)
    if re_ohm < 0:
        raise ValueError("re_ohm must not be negative.")
    _require_positive("beta", beta)
    if vbe_v < 0:
        raise ValueError("vbe_v must not be negative.")
    if vbe_v >= vcc_v:
        raise ValueError("vbe_v must be less than vcc_v.")

    vbb_v = vcc_v * r2_ohm / (r1_ohm + r2_ohm)
    rb_ohm = r1_ohm * r2_ohm / (r1_ohm + r2_ohm)
    ic_sat_a = (vcc_v - VCE_SAT_V) / (rc_ohm + re_ohm)

    if vbb_v <= vbe_v:
        return {
            "vbb_v": vbb_v,
            "rb_ohm": rb_ohm,
            "ib_a": 0.0,
            "ic_a": 0.0,
            "ie_a": 0.0,
            "vb_v": vbb_v,
            "ve_v": 0.0,
            "vc_v": vcc_v,
            "vce_v": vcc_v,
            "power_w": 0.0,
            "ic_sat_a": ic_sat_a,
            "region": "cutoff",
        }

    ib_a = (vbb_v - vbe_v) / (rb_ohm + (beta + 1) * re_ohm)
    ic_a = beta * ib_a
    ie_a = (beta + 1) * ib_a

    vb_v = vbb_v - ib_a * rb_ohm
    ve_v = ie_a * re_ohm
    vc_v = vcc_v - ic_a * rc_ohm
    vce_v = vc_v - ve_v

    region = "active"
    if vce_v < VCE_SAT_V:
        # The bias equations predict more current than the load allows.
        # Report the physically reachable point instead of negative voltages.
        region = "saturation"
        ic_a = ic_sat_a
        ie_a = ic_a + ib_a
        ve_v = ie_a * re_ohm
        vc_v = vcc_v - ic_a * rc_ohm
        vce_v = vc_v - ve_v

    return {
        "vbb_v": vbb_v,
        "rb_ohm": rb_ohm,
        "ib_a": ib_a,
        "ic_a": ic_a,
        "ie_a": ie_a,
        "vb_v": vb_v,
        "ve_v": ve_v,
        "vc_v": vc_v,
        "vce_v": vce_v,
        "power_w": vce_v * ic_a,
        "ic_sat_a": ic_sat_a,
        "region": region,
    }


def calculate_fixed_bias(
    vcc_v: float,
    rb_ohm: float,
    rc_ohm: float,
    beta: float,
    vbe_v: float = DEFAULT_VBE_V,
) -> dict[str, float | str]:
    """Fixed bias: Rb from Vcc to the base, emitter tied to ground."""
    _validate_common(vcc_v, beta, vbe_v)
    _require_positive_input("rb_ohm", rb_ohm)
    _require_positive_input("rc_ohm", rc_ohm)

    ic_sat_a = (vcc_v - VCE_SAT_V) / rc_ohm
    ib_a = (vcc_v - vbe_v) / rb_ohm

    if ib_a <= 0:
        return {
            "vbb_v": vcc_v,
            "rb_ohm": rb_ohm,
            "ib_a": 0.0,
            "ic_a": 0.0,
            "ie_a": 0.0,
            "vb_v": vbe_v,
            "ve_v": 0.0,
            "vc_v": vcc_v,
            "vce_v": vcc_v,
            "power_w": 0.0,
            "ic_sat_a": ic_sat_a,
            "region": "cutoff",
        }

    ic_a = beta * ib_a
    ie_a = (beta + 1) * ib_a
    vb_v = vbe_v
    ve_v = 0.0
    vc_v = vcc_v - ic_a * rc_ohm
    vce_v = vc_v - ve_v

    region = "active"
    if vce_v <= VCE_SAT_V:
        region = "saturation"
        ic_a = ic_sat_a
        ie_a = ic_a + ib_a
        vc_v = vcc_v - ic_a * rc_ohm
        vce_v = vc_v - ve_v

    return {
        "vbb_v": vcc_v,
        "rb_ohm": rb_ohm,
        "ib_a": ib_a,
        "ic_a": ic_a,
        "ie_a": ie_a,
        "vb_v": vb_v,
        "ve_v": ve_v,
        "vc_v": vc_v,
        "vce_v": vce_v,
        "power_w": vce_v * ic_a,
        "ic_sat_a": ic_sat_a,
        "region": region,
    }


def calculate_emitter_bias(
    vcc_v: float,
    rb_ohm: float,
    rc_ohm: float,
    re_ohm: float,
    beta: float,
    vbe_v: float = DEFAULT_VBE_V,
) -> dict[str, float | str]:
    """Emitter bias: Rb from Vcc to the base, Re from emitter to ground."""
    _validate_common(vcc_v, beta, vbe_v)
    _require_positive_input("rb_ohm", rb_ohm)
    _require_positive_input("rc_ohm", rc_ohm)
    _require_positive_input("re_ohm", re_ohm)

    ic_sat_a = (vcc_v - VCE_SAT_V) / (rc_ohm + re_ohm)
    ib_a = (vcc_v - vbe_v) / (rb_ohm + (beta + 1) * re_ohm)

    if ib_a <= 0:
        return {
            "vbb_v": vcc_v,
            "rb_ohm": rb_ohm,
            "ib_a": 0.0,
            "ic_a": 0.0,
            "ie_a": 0.0,
            "vb_v": vbe_v,
            "ve_v": 0.0,
            "vc_v": vcc_v,
            "vce_v": vcc_v,
            "power_w": 0.0,
            "ic_sat_a": ic_sat_a,
            "region": "cutoff",
        }

    ic_a = beta * ib_a
    ie_a = (beta + 1) * ib_a
    ve_v = ie_a * re_ohm
    vb_v = vbe_v + ve_v
    vc_v = vcc_v - ic_a * rc_ohm
    vce_v = vc_v - ve_v

    region = "active"
    if vce_v <= VCE_SAT_V:
        region = "saturation"
        ic_a = ic_sat_a
        ie_a = ic_a + ib_a
        ve_v = ie_a * re_ohm
        vc_v = vcc_v - ic_a * rc_ohm
        vce_v = vc_v - ve_v

    return {
        "vbb_v": vcc_v,
        "rb_ohm": rb_ohm,
        "ib_a": ib_a,
        "ic_a": ic_a,
        "ie_a": ie_a,
        "vb_v": vb_v,
        "ve_v": ve_v,
        "vc_v": vc_v,
        "vce_v": vce_v,
        "power_w": vce_v * ic_a,
        "ic_sat_a": ic_sat_a,
        "region": region,
    }


BIAS_FUNCTIONS = {
    "divider": calculate_voltage_divider_bias,
    "fixed": calculate_fixed_bias,
    "emitter": calculate_emitter_bias,
}


def calculate_bias(mode: str, **values: float) -> dict[str, float | str]:
    """Dispatch to the bias function selected by ``mode``."""
    try:
        function = BIAS_FUNCTIONS[mode]
    except KeyError:
        raise ValueError("mode must be divider, fixed, or emitter.") from None
    return function(**values)
