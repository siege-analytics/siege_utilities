# Hostile review — #1178 drop unused ast import (PR #1198)

Reviewer: general-purpose agent (in-context fallback; cross-review MCP unavailable — OpenAI quota exhausted, Anthropic/Google 1Password items missing).
Target commit: `feat/1178-phase6b-coverage-scanner` @ `9588e1e6`
Diff: single `-import ast` line in `scripts/check_symbol_test_coverage.py`.

## Verdict

SHIP

## Findings

None.

## Reviewer notes (verbatim)

> Scanner uses regex (`re`) and text scanning, not AST parsing. `ast` was genuinely orphaned. `import ast` has no side effects beyond registering the module (stdlib pure Python). No tests reference the script.
>
> The only textual "ast" occurrence in the file is inside the word "least" on line 169 ("at least one file"). Grep with `\bast\b` returns zero matches. No dynamic imports (`__import__`, `importlib.import_module`, `sys.modules`) exist in the file. The scanner uses `re` for text pattern matching, not AST parsing — the discovery/coverage logic is regex-based and never needed the `ast` module. No files under `tests/` reference this script. `import ast` from the stdlib has no import-time side effects beyond module registration, so removing it cannot affect other modules' behavior. Fix is exactly what the linter asked for and nothing more.

## Provenance

Cross-review-mcp status when review requested:
- openai: 429 insufficient_quota across gpt-4o, gpt-4o-mini, o3, o4-mini
- anthropic: 1Password item "Anthropic API Key" not found
- google: 1Password item "Google AI API Key" not found

Fallback to `general-purpose` sub-agent preserves adversarial-review discipline within the same model family (independent context window from the author agent). Cross-vendor review preferred when providers become available.
