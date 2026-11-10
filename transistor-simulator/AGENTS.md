# AGENTS.md — AI coding conventions

Guidelines for any AI assistant working in `transistor-simulator/`.

## Architecture rules

- **Engineering logic lives in `dc_bias.py` only.** Routes and templates must not
  contain formulas, thresholds, or unit conversions. They format and display.
- **`dc_bias.py` stays framework-free.** No Flask imports, no I/O, no printing.
  It must remain importable and testable on its own.
- **Routes stay thin.** `app.py` parses the form, calls `dc_bias.py`, and renders.
  Any new calculation goes behind a function in `dc_bias.py` with its own tests.
- **`create_app()` factory** is the public entry point for tests; the module-level
  `app` exists for `flask run` and `python app.py`.

## Testing

- Write the test first, watch it fail, then implement (TDD).
- Use the standard library `unittest`; no pytest dependency.
- Run the whole suite from the project root before claiming work is done:
  `python -m unittest discover -s tests -v`
- Unit tests assert on numeric results with an explicit tolerance (`delta` or
  `places`), never on rounded display strings.
- HTTP tests use Flask's `test_client()` and assert on status code plus rendered
  markers such as `data-region="active"`.

## Code style

- Python 3.10+ type hints on public functions.
- Raise `ValueError` with a message that names the offending field
  (`"beta must be greater than zero."`).
- Keep returned dict keys suffixed with their unit (`ic_a`, `vce_v`, `rb_ohm`).
- Thai user-facing text in templates; English identifiers, docstrings, and errors.

## Presentation

- Templates receive a `values` dict so user input survives validation errors.
- Use the existing CSS variables in `static/style.css`; do not add inline styles.
- Every result that depends on a physical assumption must say so in the footer or
  in `docs/design-note.md`.

## Scope discipline

- Do not add a database, JavaScript build step, or new dependency without a stated
  reason in `docs/design-note.md`.
- New bias topologies (fixed, collector-feedback) require a new function and tests;
  do not overload `calculate_voltage_divider_bias`.
