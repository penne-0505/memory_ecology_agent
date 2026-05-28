---
name: test-maintenance
description: Use while adding or updating tests so they remain mapped to intent, AC, and invariants.
---

# Test Maintenance

This skill keeps executable tests connected to the design and QA record.

## Required Procedure

1. Read the QA test-plan.
2. Inspect the existing test structure.
3. Check whether each core AC / INV has a corresponding test or verification path.
4. Add or update missing tests.
5. Avoid brittle tests that depend too heavily on implementation details.
6. For Bug fixes, add a regression test or record a no-test rationale.
7. For Refactors, prioritize behavior-preservation checks.
8. Record the AC / INV mapping in the test-plan or verification.

## Policy

- Executable tests belong in the language or framework's standard test location.
- `_docs/qa/` is for plans, traceability, and verification evidence, not test code.
- Use snapshots only when they protect intentional output and the intent is clear.
- Include `AC-001` / `INV-001` identifiers in test names or comments when practical.

## Example Test Naming

When practical, include AC or INV IDs in test names or comments.

Examples:

- `it("AC-001 rejects Medium risk tasks without QA docs", ...)`
- `it("INV-001 prevents QA docs from being archived", ...)`
- `// Covers INV-002: intent documents are permanent records`

Do not add tests that merely mirror implementation details.
Prefer tests that fail when an acceptance criterion or invariant is violated.
