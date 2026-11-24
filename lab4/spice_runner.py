"""Run ngspice and read its numeric output.

This is the only module in the project that talks to the operating system: it
locates the ngspice binary, writes a netlist into a temporary directory, starts
a subprocess and parses the plain-text vectors that ``wrdata`` produced.

Nothing here invents data. If ngspice is missing, fails to converge, times out
or writes no output, a :class:`SpiceError` is raised with ngspice's own words
attached so the page can show them verbatim.

On Windows the console build (``ngspice_con.exe``) is preferred over the GUI
build: the GUI binary would pop up a window and block the request thread. The
subprocess is also started with ``CREATE_NO_WINDOW`` so no console flashes.
"""

import math
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TIMEOUT_S = 30.0

NETLIST_NAME = "ce.cir"
OUTPUT_FILES = {
    "op": "op.txt",
    "ac": "ac.txt",
    "tran": "tran.txt",
}

#: Text ngspice prints when a run is unusable even if the exit code is zero.
FAILURE_MARKERS = (
    "singular matrix",
    "stepping failed",
    "doanalyses",
    "fatal",
    "error:",
    "no such vector",
)

_BINARY_NAMES = ("ngspice_con.exe", "ngspice_con", "ngspice.exe", "ngspice")


class SpiceError(RuntimeError):
    """A simulation that did not produce trustworthy numbers.

    ``kind`` is one of ``missing_binary``, ``timeout``, ``failed`` or
    ``no_data`` so the route can choose a status code. ``detail`` holds raw
    ngspice text and is shown to the user, never swallowed.
    """

    def __init__(self, message: str, detail: str = "", kind: str = "failed"):
        super().__init__(message)
        self.message = message
        self.detail = detail
        self.kind = kind


@dataclass(frozen=True)
class SimResult:
    """One successful ngspice run: the three analyses plus raw console text."""

    op: dict[str, float]
    ac: dict[str, list[float]]
    tran: dict[str, list[float]]
    stdout: str = ""
    binary: str = ""


def default_candidates() -> list[Path]:
    """Every place the project looks for ngspice, in preference order."""
    candidates: list[Path] = []

    for variable in ("NGSPICE_CON", "NGSPICE_BIN"):
        configured = os.environ.get(variable, "").strip()
        if configured:
            candidates.append(Path(configured))

    for name in _BINARY_NAMES:
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))

    home = Path.home()
    for root in (
        home / "Spice64" / "bin",
        Path(r"C:\Spice64\bin"),
        Path(r"C:\Program Files\Spice64\bin"),
        Path(r"C:\Program Files (x86)\Spice64\bin"),
        Path("/usr/bin"),
        Path("/usr/local/bin"),
    ):
        for name in _BINARY_NAMES:
            candidates.append(root / name)

    return candidates


def _preference(path: Path) -> int:
    """Console builds sort before GUI builds so no window can appear."""
    return 0 if "ngspice_con" in path.name.lower() else 1


def find_ngspice(candidates: list[Path] | None = None) -> Path | None:
    """Return the first existing ngspice binary, preferring ``ngspice_con``."""
    paths = [Path(item) for item in (candidates if candidates is not None else default_candidates())]
    existing = [path for path in paths if path.is_file()]
    if not existing:
        return None
    return min(existing, key=_preference)


def _spawn_options() -> dict:
    if sys.platform == "win32":
        return {"creationflags": 0x08000000}  # CREATE_NO_WINDOW
    return {}


def _decode(raw: bytes | None) -> str:
    return (raw or b"").decode("utf-8", errors="replace")


def _read_table(path: Path) -> tuple[list[str], list[list[str]]]:
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        raise SpiceError(
            f"ngspice produced no data for {Path(path).name}.",
            detail=f"expected file not found: {path}",
            kind="no_data",
        ) from None

    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        raise SpiceError(
            f"ngspice produced no rows for {Path(path).name}.",
            detail=text,
            kind="no_data",
        )

    header = lines[0].split()
    rows = [line.split() for line in lines[1:]]
    return header, rows


def _column(path: Path, header: list[str], rows: list[list[str]], name: str) -> list[float]:
    names = [item.strip().lower() for item in header]
    try:
        index = names.index(name.lower())
    except ValueError:
        raise SpiceError(
            f"ngspice output for {Path(path).name} has no {name} column.",
            detail="columns found: " + ", ".join(header),
            kind="no_data",
        ) from None

    values: list[float] = []
    for row in rows:
        if len(row) <= index:
            raise SpiceError(
                f"ngspice output for {Path(path).name} has a truncated row.",
                detail=" ".join(row),
                kind="no_data",
            )
        try:
            values.append(float(row[index]))
        except ValueError:
            raise SpiceError(
                f"ngspice output for {Path(path).name} has a non-numeric value.",
                detail=" ".join(row),
                kind="no_data",
            ) from None
    return values


def parse_op(path: Path) -> dict[str, float]:
    """Read the single operating-point row into named node voltages."""
    header, rows = _read_table(path)
    vcc = _column(path, header, rows, "v(vcc)")
    base = _column(path, header, rows, "v(base)")
    coll = _column(path, header, rows, "v(coll)")
    emi = _column(path, header, rows, "v(emi)")
    supply = _column(path, header, rows, "i(vcc)")
    return {
        "vcc_v": vcc[0],
        "vb_v": base[0],
        "ve_v": emi[0],
        "vc_v": coll[0],
        "i_vcc_a": supply[0],
    }


def parse_ac(path: Path) -> dict[str, list[float]]:
    """Read the AC sweep into frequency, gain in dB and phase in degrees.

    ngspice's ``vp()`` vector is in radians; it is converted once here so no
    template or route has to do trigonometry.
    """
    header, rows = _read_table(path)
    return {
        "freq_hz": _column(path, header, rows, "frequency"),
        "gain_db": _column(path, header, rows, "vdb(out)"),
        "phase_deg": [
            math.degrees(value)
            for value in _column(path, header, rows, "vp(out)")
        ],
    }


def parse_transient(path: Path) -> dict[str, list[float]]:
    """Read the transient run into time, input and output waveforms."""
    header, rows = _read_table(path)
    return {
        "time_s": _column(path, header, rows, "time"),
        "vin_v": _column(path, header, rows, "v(in)"),
        "vout_v": _column(path, header, rows, "v(out)"),
    }


def sample_at(ac: dict[str, list[float]], freq_hz: float) -> dict[str, float]:
    """Return the sweep point closest to ``freq_hz`` (log distance)."""
    frequencies = ac.get("freq_hz") or []
    if not frequencies:
        raise SpiceError("the AC sweep is empty.", kind="no_data")
    if freq_hz <= 0:
        raise SpiceError("freq_hz must be greater than zero.", kind="no_data")

    target = math.log10(freq_hz)
    index = min(
        range(len(frequencies)),
        key=lambda i: abs(math.log10(frequencies[i]) - target),
    )
    return {
        "freq_hz": frequencies[index],
        "gain_db": ac["gain_db"][index],
        "phase_deg": ac["phase_deg"][index],
    }


def peak_to_peak(values: list[float]) -> float:
    """Return ``max - min`` for a waveform, or zero when there is no data."""
    if not values:
        return 0.0
    return max(values) - min(values)


def simulate(
    netlist_text: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    binary: Path | None = None,
) -> SimResult:
    """Run ``netlist_text`` and return the three parsed analyses.

    Raises :class:`SpiceError` for every failure mode; a failed run never
    returns partial results that could be mistaken for a real simulation.
    """
    executable = Path(binary) if binary is not None else find_ngspice()
    if executable is None:
        tried = "\n".join(str(path) for path in default_candidates())
        raise SpiceError(
            "ngspice_con.exe was not found. Install ngspice or set NGSPICE_CON "
            "to the console binary.",
            detail="paths tried:\n" + tried,
            kind="missing_binary",
        )
    if not executable.is_file():
        raise SpiceError(
            f"ngspice binary not found at {executable}.",
            detail=f"expected ngspice_con.exe at: {executable}",
            kind="missing_binary",
        )

    workdir = Path(tempfile.mkdtemp(prefix="ce-sim-"))
    netlist_path = workdir / NETLIST_NAME
    netlist_path.write_text(netlist_text, encoding="ascii", newline="\n")

    try:
        completed = subprocess.run(
            [str(executable), "-b", NETLIST_NAME],
            cwd=workdir,
            capture_output=True,
            timeout=timeout_s,
            check=False,
            **_spawn_options(),
        )
    except subprocess.TimeoutExpired as expired:
        detail = _decode(expired.stdout) + _decode(expired.stderr)
        raise SpiceError(
            f"ngspice did not finish within {timeout_s:g} s.",
            detail=detail,
            kind="timeout",
        ) from None

    stdout = _decode(completed.stdout)
    stderr = _decode(completed.stderr)
    detail = (stdout + "\n" + stderr).strip()

    if completed.returncode != 0:
        raise SpiceError(
            f"ngspice exited with code {completed.returncode}.",
            detail=detail,
            kind="failed",
        )

    lowered = detail.lower()
    for marker in FAILURE_MARKERS:
        if marker in lowered:
            raise SpiceError(
                f"ngspice reported a problem: {marker}.",
                detail=detail,
                kind="failed",
            )

    return SimResult(
        op=parse_op(workdir / OUTPUT_FILES["op"]),
        ac=parse_ac(workdir / OUTPUT_FILES["ac"]),
        tran=parse_transient(workdir / OUTPUT_FILES["tran"]),
        stdout=detail,
        binary=str(executable),
    )
