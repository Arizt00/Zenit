# Zénit 0.5.4 R11 — Calmer motion, clearer execution evidence

R11 refines Activity, profile, Settings and model selection with a restrained
uniform scale and opacity transition. Panels stay near their final position;
the complete content remains visible throughout the movement. Screen navigation
uses a short depth fade. Decorative WebGL loops pause behind overlays and screen
transitions, then resume without advancing their animation clock while paused.
Interrupted transitions, focus, canvas pixels, scroll positions and form values
remain covered by the lifecycle regression.

## Melody

- Context & drafts previews the actual selected code scope, character count and
  unsaved status. Long previews are explicitly truncated; copying context uses
  the selected scope.
- Save up to six prompt drafts per workspace in the current window. Restoring a
  draft selects Chat mode and does not send it. Drafts are session-only.
- Missing-model actions open the inline model picker. Opening and dismissal of
  that picker are interruptible and keep account management separate.
- Inspecting context temporarily hides welcome artwork and suggestion cards,
  leaving room for the evidence and composer.

## Lantern

- Follow active file can be disabled to pin the running file while inspecting
  other tabs. Edits in unrelated tabs cannot replace the pinned buffer.
- Execution revisions compare actual observed output and exit codes. The
  comparison is bounded to 200 lines per side, shows added/removed lines and
  marks truncation. It does not infer variable state or reverse execution.
- Analyze with AI opens floating Melody and sends a read-only consultation with
  bounded execution output, diagnostics and a baseline. The attached editor
  scope and the executed file are identified separately.
- The inline workbench keeps space for code. The revision drawer is optional;
  comparison work runs only while it is open. Status labels follow the UI locale.

The regression executes two real unsaved Python buffers, compares their output,
pins a session across tab changes and resumes following another buffer. AI
transport and model catalogs in tests are explicit deterministic fixtures.

This remains an unsigned Windows public preview with partial VS Code APIs.
