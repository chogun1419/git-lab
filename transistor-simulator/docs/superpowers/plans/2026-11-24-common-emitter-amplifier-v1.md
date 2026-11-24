# Plan: Common-Emitter Amplifier Simulator v1 (ngspice integration)

Date: 2026-11-24
Project: `transistor-simulator/`
Status: **approved 2026-11-24 — implementation in progress**

## 0. What already exists (must not change)

| File | Role | Action |
|---|---|---|
| `dc_bias.py` | 3 analytical bias modes | **untouched** |
| `app.py` | thin routes, unit conversion | extended, existing routes untouched |
| `templates/index.html` | default page | only a nav link added |
| `static/style.css` | theme | appended rules only |
| `tests/test_dc_bias.py`, `tests/test_web.py` | 40 tests | **untouched, must stay 40 OK** |

Baseline verified today: `python -m unittest discover -s tests` → `Ran 40 tests ... OK`.

## 1. Findings from inspection (facts, not assumptions)

- **No instructor-verified ngspice starter files exist.** Searched the project and all of
  `git-lab/` for `*.cir, *.sp, *.net, *.spice, *.lib, *.include` — none. The netlist will be
  generated from the lab's own divider values. **Needs the user's OK (decision D1).**
- ngspice is installed at `C:\Users\theer\Spice64\bin\ngspice.exe` and `ngspice_con.exe`
  (ngspice-47). It is **not on `PATH`**, so the binary path is resolved explicitly.
- `ngspice_con.exe -b <netlist>.cir` with a `.control` block works and writes clean numeric
  `wrdata` files. A real run of the proposed circuit produced:
  `v(base)=1.936 V`, `v(emi)=1.275 V`, `v(coll)=9.2225 V`, 101 AC rows, 5008 transient rows.
- **`git` is not installed on this machine** (no `git.exe` under Program Files, ProgramData,
  AppData; `git-lab/.git` exists but the CLI is gone). Commit/push is a **blocker (D4)**.
- Python 3.12 + Flask 3.1.3 exist at
  `C:\Users\theer\AppData\Local\Programs\Python\Python312\python.exe` (not on `PATH`).
- Superpowers is not installed as a skill in this workspace; execution follows the workflow
  trace already committed under `docs/superpowers/plans/`: plan → approval → TDD → verify.

## 2. Reference circuit (single, fixed topology)

CE voltage-divider amplifier, the same five bias parts as the Lab 3 divider mode, plus fixed
passives that are printed on the page so nothing is hidden:

```
VCC ──┬── R1 ──┬─────────────── RC ──┬── C2 ──┬── out
      │        │                │     │       │
      │        └── C1 ── in      └─────┤       RL (10 k)
      │             base            collector
      │                  Q1
      └────────────── R2 ── base ... emitter ── RE ──┬── CE (100 µF) ── gnd
                                                     └── gnd
VIN (SIN amp @ f) ── in
```

Fixed: `C1 = C2 = 1 µF`, `CE = 100 µF`, `RL = 10 kΩ`, source impedance 0, `TEMP = 27 °C`.
Variable: `VCC, R1, R2, RC, RE, β`, `V_BE` (analytical only), **amplitude**, **frequency**.

Transistor model: `.model QNPN NPN(IS=1e-14 BF=<β>)`. No `VAF`, no junction capacitances.

## 3. Expected outputs

Three real analyses from one netlist:

| Analysis | Produced by | Shown as |
|---|---|---|
| DC operating point | `.op` | V(base), V(emi), V(coll) + I(VCC), next to the analytical Q-point |
| AC response | `.ac dec 10 <f/100> <f·100>` | gain (dB) and phase (deg) vs log f, readout at the requested f |
| Transient | `.tran <period/200> <5/f>` | v(in) and v(out) waveforms, peak-to-peak, no clipping claim |

Default circuit (12 V, 100k/22k/2.2k/1k, β=100, 10 mV, 1 kHz), from the real probe run:

| Quantity | Analytical (`dc_bias.py`) | SPICE (ngspice-47) |
|---|---|---|
| V_B | 1.94 V | 1.936 V |
| V_E | 1.24 V | 1.275 V |
| V_C | 9.29 V | 9.223 V |
| V_CE | 8.05 V | 7.95 V |
| midband gain | ≈ −86.5 (−38.7 dB est.) | +38.9 dB, phase −180° |

The V_BE gap (constant 0.7 V vs the model's ≈0.66 V at this current) is **reported, not
reconciled**. Every SPICE number is labelled as SPICE; every analytical number as analytical.

## 4. New files and functions

### `amplifier.py` — pure engineering, no Flask, no subprocess
- `CE_DEFAULTS` — the fixed passives above.
- `ce_parameters(**form_values) -> CeStage` — validates and derives `period_s`, `tstep_s`,
  `tstop_s`, `f_start_hz`, `f_stop_hz`, `sweep_points`.
- `transient_timing(freq_hz) -> tuple[float, float]` — `tstop = 5/f`, `tstep = (1/f)/200`,
  always `tstep > 0`; point count capped, `tstop` capped for very low f.
- `ac_sweep_window(freq_hz) -> tuple[float, float, int]` — `f/100 … f×100`, clamped to
  `[1 Hz, 100 MHz]`, at least 3 decades, 10 points/decade.
- `build_ce_netlist(stage) -> str` — emits `.op`, `.ac`, `.tran` and a `.control` block with
  `wrdata`; numbers formatted with `%.12g` so no locale separators reach SPICE.
- `estimate_small_signal(stage, qpoint) -> dict` — `re_prime_ohm`, `gain_midband`,
  `gain_midband_db`, `rin_ohm`, `rout_ohm` from `Vt = 25.85 mV`.

### `spice_runner.py` — the only module that touches the OS
- `SpiceError(Exception)` — carries `message`, `detail` (raw ngspice text), `kind`.
- `find_ngspice() -> Path | None` — `NGSPICE_CON` env var, then `NGSPICE_BIN`, then the Spice64
  candidates, preferring **`ngspice_con.exe`** over `ngspice.exe`.
- `run_netlist(text, timeout=30) -> dict[str, Path]` — `tempfile.mkdtemp`, ASCII LF netlist,
  `subprocess.run(..., cwd=workdir, capture_output=True, timeout=30,
  creationflags=CREATE_NO_WINDOW)`.
- `parse_op`, `parse_ac`, `parse_transient` — whitespace-split float parsers over the headers
  ngspice wrote (header-driven, so column order is never guessed).
- `simulate(text) -> SimResult` — orchestrates, and raises with ngspice's own words.

### `plots.py` — presentation geometry, stdlib only
- `line_points(xs, ys, box, x_scale="log"|"linear", y_scale=...) -> str`
- `axis_ticks(lo, hi, log=False) -> list[tuple[float, float]]`

Inline SVG generated server-side keeps the "no JavaScript build step" rule intact.

### `app.py` — thin additions
- `_parse_amplifier_form(values)` — mV/V and Hz/kHz → SI, field-named errors.
- `@app.get("/amplifier")`, `@app.post("/amplifier/simulate")`.
- Existing `/` and `/calculate` byte-identical in behaviour.

### Templates / CSS
- `templates/amplifier.html` — inputs, fixed-passives list, netlist `<pre>`, SPICE vs
  analytical tables side by side, three inline SVG charts.
- `templates/index.html` — one nav link to `/amplifier`.
- `static/style.css` — appended chart/table/nav rules.

## 5. Error paths (no silent failures, no fabricated traces)

| Condition | HTTP | What the user sees |
|---|---|---|
| blank / non-numeric amplitude or frequency | 400 | field-named message, entered values preserved |
| amplitude ≤ 0, frequency ≤ 0 | 400 | `vin_amp_v must be greater than zero.` |
| frequency above 100 MHz | 400 | `freq_hz must be at most 1e8.` |
| `ngspice_con.exe` not found | 503 | banner naming every path tried + `NGSPICE_CON`; charts and numbers absent, no placeholder curve |
| ngspice exit code ≠ 0 | 500 | raw stderr/stdout tail in a `<pre>` |
| singular matrix / gmin-stepping / source-stepping failure in stdout | 500 | ngspice's own warning text, results discarded |
| 30 s timeout | 504 | `ngspice did not finish within 30 s` + partial output |
| `wrdata` file missing or empty | 500 | `ngspice produced no data for <analysis>` |
| `.op` converged but Q-point is saturated/cutoff | 200 | both sources shown; region from `dc_bias.py` stays authoritative |
| SPICE and analytical disagree | 200 | both values shown with the delta; never averaged or overridden |

## 6. Tests (written first, all new files)

- `tests/test_amplifier.py` — netlist contains `.op`/`.ac`/`.tran`, `tstep > 0`, correct
  `tstop = 5/f`, amplitude/frequency substitution, `β` into `BF`, small-signal gain numbers
  with `places=`, validation messages.
- `tests/test_spice_runner.py` — parsers against **recorded real output** saved in
  `tests/fixtures/`; every error path above (missing exe, non-zero exit, timeout, empty file).
- `tests/test_amplifier_web.py` — new routes: 200 on GET, 400 messages, 503 when the binary is
  patched away, and a rendered page containing `data-source="spice"` and
  `data-source="analytical"` markers.
- `tests/test_spice_integration.py` — `@unittest.skipUnless(find_ngspice())`, runs the real
  default circuit and asserts the `.op` node voltages land within 5 % of `dc_bias.py`, that
  101 AC rows and >1000 transient rows came back. Skips loudly, never fakes a pass.

`tests/test_dc_bias.py` and `tests/test_web.py` are not edited; total goes from 40 to ~70.

## 7. Execution order (Superpowers workflow)

1. Failing tests for `amplifier.py` → implement → green.
2. Failing tests for `spice_runner.py` + fixtures recorded from real runs → implement → green.
3. Failing tests for the two new routes → implement `app.py` + template → green.
4. Full suite; confirm the original 40 still pass and `dc_bias.py` is untouched.
5. Real browser demo via the Playwright MCP at `127.0.0.1:5000/amplifier`; screenshot.
6. Update `docs/design-note.md` (why ngspice, model limits, why a second calculation module),
   `docs/validation.md` (analytical vs SPICE table), `README.md`, `docs/test-log.txt`, and amend
   the `AGENTS.md` formula-location rule to name `amplifier.py`.
7. Commit on `main`.

## 8. Decisions needed before coding

- **D1 — netlist provenance.** No instructor-verified starter files exist. OK to generate the
  netlist from the lab's divider values (as above), or will you supply the starter file first?
- **D2 — model.** `.model QNPN NPN(IS=1e-14 BF=β)` with no `VAF`/capacitances, so the AC sweep
  is flat to 1 MHz. Acceptable as v1, or should it carry a named 2N2222 model?
- **D3 — layout.** Separate `/amplifier` page with a nav link (recommended, zero risk to the
  40 existing tests), or a fourth mode inside the existing single page?
- **D4 — git.** `git.exe` is absent from this machine. OK to install it
  (`winget install --id Git.Git -e`), or will you commit yourself? Push also needs GitHub
  credentials; if none are available I commit locally and hand you the push command.
