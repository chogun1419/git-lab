"""Engineering model of the reference common-emitter amplifier stage.

The stage is the same voltage-divider bias circuit the app already calculates
analytically, with the passives a real CE amplifier needs: an input coupling
capacitor, an output coupling capacitor, a bypassed emitter resistor and a
collector load.

    Vcc --- R1 ---+--- Rc ---+--- C2 --- out
                  |          |              RL
                 C1          Q1 collector   (to ground)
                  |          |
                 in ------- base           emitter --- Re ---||-- CE --- gnd
                                                        (parallel)

Everything in this module is pure: no Flask, no subprocess, no file I/O. It
builds SPICE netlist text and estimates the small-signal behaviour that the
SPICE run can be compared against.

Assumptions stated in docs/design-note.md: the transistor model has no Early
effect and no junction capacitances, so the AC response is flat between the
coupling-capacitor cutoffs and the model's high-frequency limit. The single
thermal voltage is taken at 27 degrees Celsius.
"""

import math
from dataclasses import dataclass

#: Thermal voltage at 27 degrees Celsius, used for the small-signal emitter resistance.
VTS_V = 0.02585

#: Passives that are fixed for v1 and printed on the page, not entered by the user.
CE_DEFAULTS = {
    "c_in_f": 1e-6,
    "c_out_f": 1e-6,
    "c_e_f": 100e-6,
    "load_ohm": 10_000.0,
}

#: AC sweep density. Ten points per decade is enough to read a corner by eye.
AC_POINTS_PER_DECADE = 10

#: Band the model is trusted over. Above this the missing junction capacitances
#: would dominate, so a request beyond it is rejected rather than drawn as flat.
MIN_FREQ_HZ = 1.0
MAX_FREQ_HZ = 1e8

#: Transient window: five periods, two hundred steps per period.
PERIODS_SIMULATED = 5
SAMPLES_PER_PERIOD = 200

#: Transistor model name used in the netlist.
MODEL_NAME = "QNPN"

#: Saturation current of the reference model.
MODEL_IS_A = 1e-14


def _require_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")


def _require_band(freq_hz: float) -> None:
    _require_positive("freq_hz", freq_hz)
    if freq_hz > MAX_FREQ_HZ:
        raise ValueError("freq_hz must not exceed 100 MHz.")


def _spice_number(value: float) -> str:
    """Format a number so SPICE reads it the same way on every locale."""
    return f"{value:.12g}"


@dataclass(frozen=True)
class CeStage:
    """Validated inputs of one common-emitter amplifier run, in base SI units."""

    vcc_v: float
    r1_ohm: float
    r2_ohm: float
    rc_ohm: float
    re_ohm: float
    beta: float
    vin_amp_v: float
    freq_hz: float
    c_in_f: float
    c_out_f: float
    c_e_f: float
    load_ohm: float

    @property
    def period_s(self) -> float:
        return 1.0 / self.freq_hz


def ce_parameters(
    vcc_v: float,
    r1_ohm: float,
    r2_ohm: float,
    rc_ohm: float,
    re_ohm: float,
    beta: float,
    vin_amp_v: float,
    freq_hz: float,
    c_in_f: float = CE_DEFAULTS["c_in_f"],
    c_out_f: float = CE_DEFAULTS["c_out_f"],
    c_e_f: float = CE_DEFAULTS["c_e_f"],
    load_ohm: float = CE_DEFAULTS["load_ohm"],
) -> CeStage:
    """Validate the stage inputs and return them unchanged in SI units."""
    _require_positive("vcc_v", vcc_v)
    _require_positive("r1_ohm", r1_ohm)
    _require_positive("r2_ohm", r2_ohm)
    _require_positive("rc_ohm", rc_ohm)
    _require_positive("re_ohm", re_ohm)
    _require_positive("beta", beta)

    _require_positive("vin_amp_v", vin_amp_v)
    if vin_amp_v > vcc_v:
        raise ValueError("vin_amp_v must not exceed vcc_v.")

    _require_band(freq_hz)

    _require_positive("c_in_f", c_in_f)
    _require_positive("c_out_f", c_out_f)
    _require_positive("c_e_f", c_e_f)
    _require_positive("load_ohm", load_ohm)

    return CeStage(
        vcc_v=vcc_v,
        r1_ohm=r1_ohm,
        r2_ohm=r2_ohm,
        rc_ohm=rc_ohm,
        re_ohm=re_ohm,
        beta=beta,
        vin_amp_v=vin_amp_v,
        freq_hz=freq_hz,
        c_in_f=c_in_f,
        c_out_f=c_out_f,
        c_e_f=c_e_f,
        load_ohm=load_ohm,
    )


def transient_timing(freq_hz: float) -> tuple[float, float]:
    """Return ``(tstep_s, tstop_s)`` for a five-period transient at ``freq_hz``.

    ``tstep`` is always strictly positive because it is derived from a period
    that positive validation already guarantees.
    """
    _require_band(freq_hz)
    period_s = 1.0 / freq_hz
    tstep_s = period_s / SAMPLES_PER_PERIOD
    tstop_s = period_s * PERIODS_SIMULATED
    return tstep_s, tstop_s


def ac_sweep_window(freq_hz: float) -> tuple[float, float]:
    """Return the AC sweep band: two decades either side of ``freq_hz``, clamped."""
    _require_band(freq_hz)
    start_hz = max(MIN_FREQ_HZ, freq_hz / 100.0)
    stop_hz = min(MAX_FREQ_HZ, freq_hz * 100.0)
    return start_hz, stop_hz


def build_ce_netlist(stage: CeStage) -> str:
    """Return the ngspice netlist for one operating-point, AC and transient run.

    The control block writes three plain-text files next to the netlist
    (``op.txt``, ``ac.txt``, ``tran.txt``) so the parser reads numbers instead
    of screen-formatted tables.
    """
    tstep_s, tstop_s = transient_timing(stage.freq_hz)
    start_hz, stop_hz = ac_sweep_window(stage.freq_hz)

    lines = [
        "* Common-emitter amplifier (voltage-divider bias)",
        "* generated by transistor-simulator; all values are SI units",
        f"VCC vcc 0 {_spice_number(stage.vcc_v)}",
        f"R1 vcc base {_spice_number(stage.r1_ohm)}",
        f"R2 base 0 {_spice_number(stage.r2_ohm)}",
        f"RC vcc coll {_spice_number(stage.rc_ohm)}",
        f"RE emi 0 {_spice_number(stage.re_ohm)}",
        f"Q1 coll base emi {MODEL_NAME}",
        f"C1 in base {_spice_number(stage.c_in_f)}",
        f"C2 coll out {_spice_number(stage.c_out_f)}",
        f"CE emi 0 {_spice_number(stage.c_e_f)}",
        f"RL out 0 {_spice_number(stage.load_ohm)}",
        (
            f"VIN in 0 DC 0 AC 1 SIN(0 {_spice_number(stage.vin_amp_v)} "
            f"{_spice_number(stage.freq_hz)})"
        ),
        (
            f".model {MODEL_NAME} NPN(IS={_spice_number(MODEL_IS_A)} "
            f"BF={_spice_number(stage.beta)})"
        ),
        ".control",
        "set wr_singlescale",
        "set wr_vecnames",
        "op",
        "wrdata op.txt v(vcc) v(base) v(coll) v(emi) i(VCC)",
        f"ac dec {AC_POINTS_PER_DECADE} {_spice_number(start_hz)} "
        f"{_spice_number(stop_hz)}",
        "wrdata ac.txt vdb(out) vp(out)",
        f"tran {_spice_number(tstep_s)} {_spice_number(tstop_s)}",
        "wrdata tran.txt v(in) v(out)",
        "quit",
        ".endc",
        ".end",
    ]
    return "\n".join(lines) + "\n"


def _parallel(*resistances: float) -> float:
    return 1.0 / sum(1.0 / value for value in resistances)


def estimate_small_signal(
    stage: CeStage, qpoint: dict[str, float]
) -> dict[str, float]:
    """Return the midband small-signal estimate for comparison with SPICE.

    The emitter resistor is assumed fully bypassed at midband, so the gain is
    ``-(Rc || RL) / re'`` with ``re' = Vt / I_E``. This is an estimate, not a
    substitute for the SPICE result; the page shows both.
    """
    ie_a = qpoint["ie_a"]
    if ie_a <= 0:
        raise ValueError(
            "ie_a must be greater than zero to estimate small-signal gain."
        )

    re_prime_ohm = VTS_V / ie_a
    collector_load_ohm = _parallel(stage.rc_ohm, stage.load_ohm)
    gain_midband = -collector_load_ohm / re_prime_ohm
    base_input_ohm = (stage.beta + 1.0) * re_prime_ohm

    return {
        "re_prime_ohm": re_prime_ohm,
        "gain_midband": gain_midband,
        "gain_midband_db": 20.0 * math.log10(abs(gain_midband)),
        "rin_ohm": _parallel(stage.r1_ohm, stage.r2_ohm, base_input_ohm),
        "rout_ohm": stage.rc_ohm,
    }
