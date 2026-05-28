# Validator fixtures

These fixtures exercise the repository validators themselves.

They are not active project tasks or QA records. `scripts/test-validators.mjs`
runs the validators against these files and expects:

- files under `valid/` to pass;
- files under `invalid/` to fail.

The QA fixtures use `fixture_path` front-matter so `validate-qa.mjs` can apply
the normal canonical-path rules while the fixture files remain under `_evals/`.
