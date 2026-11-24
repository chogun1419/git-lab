# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Primary:** an electrical-engineering undergraduate working in `transistor-simulator/` for the
ENG29 2121 lab sequence ("Computer Programming for Electrical Engineers"). They are at a laptop,
usually mid-assignment, with the lab sheet beside them and a handful of component values to check
against a hand calculation. They want the Q-point and the operating region without re-deriving
five formulas each time. *(Confirmed by the user.)*

**Secondary:** the course instructor, who opens the same app to check that a submission's numbers,
its error handling, and its boundary cases actually hold up. *(Confirmed by the user.)*

## Product Purpose

A DC bias calculator for a single NPN BJT in three topologies — voltage divider, fixed, and
emitter bias. It reports I_B, I_C, I_E, V_B, V_E, V_C, V_CE and P_D, classifies the operating point
as active / saturation / cutoff, draws the matching schematic with the submitted values in its
labels, and rejects invalid input with a message that names the offending field.

Success means: a student's hand calculation and the screen agree to the displayed digits; the
region readout is right, including the saturation clamp; and an instructor grading the work finds
no contradiction between the equations in `docs/` and the numbers on the page.

## Positioning

The engineering is a separate, framework-free Python module with its own unit tests, and the page
is plain server-rendered HTML with no JavaScript. The physics can therefore be verified without
touching the web layer, and every number on screen — including the values drawn inside the inline
SVG schematic — comes from the same function the tests assert on. A demo that inlines formulas
into a route or recomputes labels in the template cannot truthfully claim either property.

## Operating Context

- Built for ENG29 2121 lab work; the page header still reads "Lab 02: BJT DC Bias Web App" while
  `README.md` and `docs/design-note.md` document the Lab 3 extension (fixed and emitter bias).
  The mismatch is real and currently preserved; it is not a decision.
- Runs locally only: `python app.py` → <http://127.0.0.1:5000>. It is not deployed publicly and
  has no accounts, storage, or history.
- Resistance values are entered in Ω or kΩ per field; the rest of the quantities are unitless or
  in V.
- The student's own written record (`README.md`, `docs/design-note.md`, `docs/validation.md`,
  `docs/reflection.md`) is in Thai. The app's user-facing text and every identifier, docstring, and
  error message are English — that split is deliberate (`AGENTS.md`).

## Capabilities and Constraints

**Confirmed behaviour**

- Three bias modes behind one form. Divider: V_CC, R1, R2, R_C, R_E, β, V_BE. Fixed: V_CC, R_B,
  R_C, β, V_BE. Emitter: adds R_E. Only the selected mode's fields are submitted.
- Unit conversion happens once, in `app.py`, before the calculation module is called; `dc_bias.py`
  only ever sees ohms, volts, and amperes.
- Results and the SVG schematic labels both render from the submitted values, so what is drawn and
  what is reported cannot drift apart within one response.
- Validation rejects blank fields (except V_BE, which defaults to 0.7 V), non-numeric text,
  negative values, zero where zero is invalid, and V_BE ≥ V_CC. Each error is an HTTP 400 with a
  message naming the field, and the entered values survive the error.
- Region logic: cutoff when base drive collapses; saturation when V_CE would fall below 0.2 V, in
  which case I_C is clamped to I_C(sat) and node voltages recomputed so nothing goes negative;
  active otherwise. The divider mode keeps its original status wording, while fixed and emitter
  prefix any non-active result with "Warning:".
- Deliberate modelling limits: ideal BJT, constant V_BE, no Early effect, no temperature sweep, no
  AC analysis, no load line. These are stated in `docs/design-note.md` and must stay stated.
- 40 `unittest` tests: 19 on the formulas, 21 on the HTTP routes.

**Architecture rules, binding (`AGENTS.md`)**

- Formulas live only in `dc_bias.py`; routes and templates parse, format, and display.
- `dc_bias.py` stays framework-free: importable and testable on its own.
- Routes stay thin; `create_app()` is the entry point tests use.
- No new dependency, database, or JavaScript build step without a stated reason in
  `docs/design-note.md`.

**Undecided / open**

- The app is expected to keep growing past Lab 3 — load line with a Q-point marker, more
  topologies, CSV/PDF export, β comparison are all named as future work, none of them committed
  scope. *(Confirmed: "core rules plus room to grow.")*
- No deploy target, no hosting, no public URL.

## Brand Commitments

- Name: "Transistor DC Bias Simulator" (repository, `README.md`). The page itself presents as a
  course lab app, with the course line "ENG29 2121 – Common Emitter (Divider / Fixed / Emitter
  Bias)" and a course badge in the header.
- Voice: instructional and plain. No marketing claims.
- Notation: electrical symbols stay in engineering form (V_CC, R_B, β, kΩ), never spelled out as
  prose.
- No logo, wordmark, font, or colour asset exists outside the inline SVG icons and
  `static/style.css`.

## Evidence on Hand

- Hand-checked reference table for the default divider case (V_BB = 2.16393 V, V_CE = 8.05216 V)
  plus cutoff, saturation, and invalid-input cases: `docs/validation.md`.
- Recorded test output, 40 tests OK: `docs/test-log.txt`.
- A real browser screenshot of the fixed-bias result: `docs/evidence/a2-fixed-bias.jpeg`.
- The saturation bug and its fix, written up as a lesson: `docs/reflection.md`.
- **Absent, and must not be invented:** testimonials, student counts, benchmarks, pricing,
  licensing statements, deployment claims, or measured accuracy against hardware.

## Product Principles

1. **The formula is the product.** Every displayed number traces to a tested function in
   `dc_bias.py` and to a hand calculation in the documentation.
2. **Impossible physics is flagged, not printed.** A point outside forward-active is labelled, and
   saturation is clamped rather than shown as a negative node voltage.
3. **Never cost the user their input.** An error message leaves every value they already typed in
   place.
4. **Plain web, no machinery.** Server-rendered HTML and CSS carry the job; JavaScript, storage, or
   a build step has to earn its place in writing.
5. **Show the circuit while showing the answer.** The schematic's labels and the results table
   answer the same question, so they must always agree.

## Accessibility & Inclusion

- Must stay usable on a phone: three columns collapse to one below roughly 1000 px and the form
  and table remain legible below 560 px.
- No formal standard (e.g. a WCAG level) has been agreed. Existing labels and ARIA attributes in
  the template are good practice, not a recorded commitment.
