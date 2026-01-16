# InfraCrawl – AI Change Rules (TDD-First)

If you are an AI assistant making changes in this repository, you must follow this file.

## Default Mode: Strict TDD
When implementing a change, follow **Red → Green → Refactor**.

### Step 1 — RED (tests only)
- Add or update tests **only** (no production code changes).
- Run the full test suite: `./test.sh`
- Report:
  - Which tests were added/changed (file paths)
  - The failing test name(s)
  - Why it fails (expected vs actual)

### Step 2 — GREEN (minimal production change)
- Make the **smallest** code change that makes the new/updated tests pass.
- Do **not** refactor yet.
- Run: `./test.sh`
- Report pass/fail.

### Step 3 — REFACTOR (optional)
- Refactor for clarity/simplicity **only if needed**.
- No behavior changes beyond the tests.
- Run: `./test.sh` again.

## Change Hygiene
- Keep diffs small; change only what the tests require.
- No unrelated formatting, drive-by cleanups, or opportunistic refactors.
- No backwards-compatibility shims unless explicitly requested.
- Prefer existing test patterns and existing test files when possible.
- If mocking is used, explain why it is necessary.

## Questions
- Ask **at most one** clarifying question if blocked.
- Otherwise choose the simplest maintainable behavior consistent with existing code.

## Reporting Format (each iteration)
- Files changed
- Commands run (exact)
- Test results summary

## Definition of Done
- `./test.sh` passes
- New behavior is covered by tests
- Code is readable and consistent with repository style
