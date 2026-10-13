# Zénit 0.5.4 R5 — A clearer coding workspace

R5 connects a renewed interface to concrete coding, assistance and execution flows.
It is a Windows public preview; it is not promoted to stable or full VS Code parity.

## Interface

- Coordinated surfaces, headers, buttons, icons, focus states and compact layouts.
- Melody’s welcome uses a smaller crystal and a two-column action grid.
- Visible model destination, new conversation, stop response, Chat/Edit file modes
  and an actionable code-context control.
- English initial language and translation of remaining common chrome labels.
- Light/dark/forest tokens, reduced motion, hidden scrollbars with scrolling intact.
- Existing welcome, My activity and faded profile covers remain supported.

## Melody

Questions now honor no-code, selection or whole-file scope. Editing always receives
the complete file. A selected-range proposal can replace only the captured range;
the rest stays intact, a changed buffer rejects the proposal, and one undo restores
the edit. Existing file plans, recovery, live editing and local Emma voice remain.
Flow tests use declared deterministic responses, not model-quality benchmarks.

## Forge

Run with the configured file runtime, or use Python’s unsaved-buffer action and
C/GDB. The dashboard shows the actual process state, elapsed time and exit code.
Run again follows the original execution’s file. Stop closes that tracked process,
leaving unrelated terminals intact. A bounded recent-execution list belongs to the
current Forge window. Context help reflects the file language.

## Public project

New English README with real screenshots, quick start, examples and current limits.
Apache-2.0 for original code/docs, with NOTICE and existing GPL/third-party exceptions.
Contribution guide, issue forms, PR template, roadmap and launch article materials.
Repository About/topics and Discussions are configured for discovery and feedback.

## Download and verification

The release contains Windows installer/portable, manifest and SHA-256 checksums.
The preview is unsigned. Verification evidence lives under `tests/visual/evidence`;
screenshots have [capture details](media/README.md). See [STATUS](STATUS.md) for the
remaining boundaries, including partial extension APIs and platform-specific builds.
