# Zénit 0.5.4 R6 — A connected workbench

R6 fixes specific interface and workflow failures reported in R5.

- The active document tab has rounded upper corners and joins the editor sheet.
  Heavy accent underlines and tinted header bands are replaced by quieter surfaces.
- Extensions uses the available workspace without Project, Melody or terminal
  distractions. Hidden panels become inert; their saved layout is preserved.
- Debug’s Ask Melody opens the existing assistant as a floating panel and sends
  the debugger snapshot. It remains a read-only consultation even in Edit mode.
  A missing model opens connection settings and retains the prepared question.
- Melody has provider identities, diagnostics review and focused test planning.
  A configured model is no longer displayed as a verified account connection.
- Forge can send its captured terminal output and exit status to Melody.
- Laboratory explains environment readiness for the active file, opens Forge,
  and can send the detected tool inventory to Melody. Its terminal remains visible.
- Malformed LSP ranges cannot crash diagnostic rendering. Preference refresh
  waits for the captured write and rejects a read overtaken by a newer change.
- Built-in themes are visually verified; extension theme foregrounds use their
  actual editor/field/selection surfaces. Cached themes retain the new tokens.

Account access uses the existing official Codex, Claude Code, Gemini CLI and
Copilot clients. API destinations use provider credentials; Emma and Ollama are
local connections. Sign-in and model availability depend on the installed client
and account. Zénit does not collect consumer-site passwords or browser cookies.

Provider identities: Simple Icons 13.21.0, CC0-1.0. Brand trademarks remain with
their owners. See `web/assets/providers/NOTICE.md`.

This is an unsigned Windows public preview. AI regression transports are explicit
fixtures; passing workflow tests does not certify model intelligence or account
access. VS Code APIs and compatibility remain partial.
