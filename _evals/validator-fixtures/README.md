# Validator fixtures

These fixtures exercise the repository validators themselves.

They are not active project tasks or QA records. `scripts/test-validators.mjs`
runs the validators against these files and expects:

- files under `valid/` to pass;
- files under `invalid/` to fail.

The frontmatter, intent, and QA fixtures run through their validators with `--fixture` and
use `fixture_path` front matter so the validators can apply the normal
canonical-path rules while the fixture files remain under `_evals/`.

Frontmatter fixtures cover correct type-specific schema markers, a marker on the
wrong document type, an unknown schema marker, and duplicate frontmatter keys.

The QA invalid fixture without `qa_schema` also verifies legacy compatibility:
legacy plans still require an `INV-*`, while schema v2 accepts `None`.
