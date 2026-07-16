# claudex-router — BUILD drafting moves to GPT-5.6 sol in the Claude Code harness

Machine-facing plan (SELF-DIRECTED lane). Pete's direction, 2026-07-16: install claudex
(CLIProxyAPI + Codex OAuth, per Theo's "claudex" setup) and make ship:router dispatch
BUILD drafting via `claudex -p` instead of `codex exec`. Rationale: same model
(gpt-5.6-sol), same ChatGPT-subscription billing, but the worker runs in the Claude
Code harness — it inherits Pete's CLAUDE.md, skills, and MCP natively, and Theo's
side-by-sides show sol performs better in this harness than in Codex.

## Scope

- **Machine setup (not repo):** install claudex via DocksDocks/claudex wizard —
  loopback-only CLIProxyAPI on 127.0.0.1, Codex OAuth credential, `claudex` wrapper
  in ~/.local/bin.
- **Repo change:** `plugins/ship/skills/router/SKILL.md` — BUILD drafting dispatches
  become `claudex -p`; `codex exec` stays as the documented fallback when the proxy
  path is down. Scope stops at BUILD: review (`codex exec review`), verify walks,
  browser/Playwright work, and DISCOVER recon stay on codex exec — Pete scoped this
  to the build stage.
- **Memory:** engine-ladder + a claudex reference memory after merge.

## Tasks

1. Run `install.sh --yes` (reviewed first — checksummed release, loopback bind,
   owner-only creds). Codex OAuth browser flow needs Pete's one click.
2. Smoke test: headless `claudex -p` from a scratch dir — confirm gpt-5.6-sol via the
   proxy, a real file edit, and that nested invocation (claude inside Claude Code)
   works. Determine the right permission flag for worker dispatches.
3. Rewrite router SKILL.md quick-reference + engine table: claudex invoke pattern
   (result file, tag line, background, stall budget adapted), codex exec demoted to
   fallback, billing note (proxy → ChatGPT sub, never Anthropic credits — the
   "no claude -p on API credits" rule is satisfied because the proxy path never
   touches Anthropic).
4. Review (codex exec review --base main) + a live claudex dispatch as the verify
   surface, wt merge, plugin-cache hand-deploy per CLAUDE.md, memory updates.

## Not doing (ponytail cut-list)

- No pipeline SKILL.md rewrite — it defers engine mechanics to router already; its
  codex-exec mentions (recon/review/browser) are out of scope by Pete's framing.
- No head-to-head benchmark harness — Pete skipped it; the ledger will show hit-rates.
- No launchd service for the proxy — the wrapper auto-starts it per invocation.
