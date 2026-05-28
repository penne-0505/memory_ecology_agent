#!/usr/bin/env bash
set -euo pipefail

deno fmt --check scripts/*.mjs
deno run --allow-read scripts/validate-frontmatter.mjs
deno run --allow-read scripts/validate-todo.mjs
deno run --allow-read scripts/validate-doc-links.mjs
deno run --allow-read scripts/validate-qa.mjs
deno run --allow-read --allow-run scripts/test-validators.mjs
