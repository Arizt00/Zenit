# Zénit 0.5.4 R13

First-run setup now owns an opaque, accessible screen instead of drawing over
the welcome page. It uses the active theme, retains drafts when navigating back,
keeps personalisation labels and descriptions separate, and transitions to Home
through the same interruptible screen motion used by the workspace. A local
language preview no longer gets overwritten by the legacy chrome translator.

Laboratory, Forge and Debug form a compact toolbar. Each expands to the left
with a fixed right edge; the search field resizes continuously. The buttons
collapse after clicking and respect reduced motion. Melody's header keeps New
conversation, Float and More visible; voice and desktop detachment are in More.
The floating-panel glyph now depicts an inset window, separate from desktop
detachment. Language icons are unchanged.

## Lantern and Hilo

- Choose a Python environment with Zénit's bundled packages or a clean venv.
- Choose 1/2/4/8 GB RAM and 1/2/4 virtual CPUs for an Arch VM. Resource choices
  are validated and retained in the `.tern` checkpoint.
- Hilo reports preparation phase, queue position and elapsed time. A cancelled
  operation is displayed as cancelled, rather than as successfully completed.
- Failed Hilo work can be sent to Melody with its actual error and environment
  inventory. This is an explicit review action; it does not run a proposed fix.

Saved `.tern` files refer to their workspace-owned backing environment under
`.lumen/tern`. Keep that folder when moving a saved workspace. Closing an unsaved
environment removes it; closing a saved environment retains it. VM checkpoints
retain disk contents, not the running machine's RAM. QEMU and a prepared Arch
base remain prerequisites configured from Laboratory; no elevation is needed.

## Melody and connections

Streaming uses elapsed frame time so its reveal cadence follows 60/120/144 Hz
displays. It preserves the reader's scroll position and flushes the complete
response on completion. Reduced motion reveals updates immediately. Evidence
tools use the inline model picker when a provider is not selected.

Connections remain in Settings. Interactive Codex launches detect support for
`--no-daemon` from the installed client's help and use it when available. This
avoids relying on a shared server package absent from some desktop CLI bundles;
older clients retain their original command line. No account credentials or
approval/sandbox settings are changed. Reference: [official CLI commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli).

This iteration improves specific workspace workflows; it does not claim complete
VS Code extension/API compatibility or a general-purpose hypervisor.
