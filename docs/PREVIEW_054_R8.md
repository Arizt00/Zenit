# Zénit 0.5.4 R8 — Evidence and machine inspection

R8 delivers the R7 interface work and addresses the clipped Settings controls, unreadable extension surfaces and
profile hover reported in R6. It adds useful inspection workflows without
claiming universal VS Code parity or globally unique AI capabilities.

- Clicking Melody or its destination opens an inline model panel with provider
  selection, a real catalog, search, cached results and keyboard navigation.
  Settings opens only through Manage account. A catalog does not imply a
  verified account or a successful generation.
- The unchanged nC VSIX is included and installed once on first launch. Existing
  versions and later removal are respected. Its engine still requires workspace
  authorization; grammar and snippets load declaratively. The actual original
  Node engine registers hover, completion, symbols, formatting, rename and
  semantic token providers without unsupported API calls in the regression.
  Existing icon preferences and icons for other languages remain unchanged.
- Opening Activity keeps the home scene's parallax position while the overlay
  covers it. Entering the IDE and returning through the Zénit wordmark share a
  source-connected view transition. The IDE profile uses the same modal morph.

- Settings navigation has a bounded footer; imports and exports stay inside the
  sidebar. Theme and icon summaries have separate spacing. Appearance, Terminals,
  Extensions and Hardware use the same scrolling and control hierarchy.
- Extension cards use the available width with wrapped actions. Shell text,
  fields, selected items and buttons retain readable foregrounds; transparent or
  barely visible theme borders receive a minimal contrast adjustment.
- Drag a lateral panel 36 pixels beyond its minimum to collapse it. Its contents
  and prior useful width remain available through the collapsed rail. Keyboard
  resizing can also collapse a panel at its limit. Cancelled drags restore width.
- Welcome shows an avatar at rest and expands its label on hover or keyboard
  focus, without turning white. My activity opens from the avatar with a 380 ms
  clipped surface reveal. It follows the continuity principles in Samsung's
  public One UI motion guidance; it is not an exact One UI 9 implementation.
  Reduced motion bypasses the transition. Activity has quiet surfaces and a
  visible, scrollable result list.
- Binary files open in normal tabs with a read-only paged byte viewer: offsets,
  hex, ASCII, endian selection and numeric interpretations. Each page reads 512
  bytes, and the backend caps requests at 4096. Save, Save As, text edits and text
  buffer sharing cannot write through this viewer. Large files are never loaded
  wholesale. This is byte inspection, not execution or a full media previewer.
- nC uses the original icon declared by its VS Code extension in Arizt00/ncc,
  copied byte-for-byte. The alternative hexagonal SVG and MIT terms are retained.
- Editor tabs support Ctrl+PageUp/PageDown, arrow/Home/End navigation, middle
  click close, close others/right, and Ctrl+Shift+T to reopen. Bulk close stops at
  a cancelled unsaved-file prompt. Reopening reads the current file from disk.

## Five Melody evidence tools

| Tool | What it actually does |
| --- | --- |
| Evidence capsule | Freezes the unsaved text, source hash, diagnostics and captured execution output locally in the project. Keeps at most 12 capsules. |
| Drift lens | Computes a unified source diff against the latest capsule for this file. Does not change source. |
| Reference weave | Scans up to 120 source files for Python AST imports and literal references in other languages. Evidence links open the exact source line; dynamic relationships are not inferred. |
| Fault atlas | Groups actual diagnostics and captured error/exception output into inspectable evidence. It does not claim a proven root cause. |
| Handoff brief | Creates an editable Markdown brief of source identity, diagnostics and execution evidence. Copy it or ask Melody to interpret it. |

Calculations run locally before optional AI consultation. Capsules reside in
`.lumen/melody/capsules.json` inside the project. Each source capture is capped at
300 kB. Binary and external project files cannot enter the text evidence store.
Ask Melody remains read-only, including when the composer was previously in
Edit mode. Account/model configuration is still required for provider responses.

## Debugger: three backend capabilities, two programmer tools

The backend now offers bounded, capability-checked DAP `readMemory` and
`disassemble` requests plus a deduplicated ring of 24 observed pause snapshots.
The Machine inspector displays actual bytes or native instructions. Pause
comparison shows changed variable values between a selected baseline and the
latest observed pause. Python and other adapters report unsupported native
operations explicitly. The history is an observed-state record, not reverse
execution or an exhaustive CPU instruction trace. A resumed or replaced session
invalidates an in-flight machine result.

The development checks include an actual GCC/LLDB process, disassembly and
memory reads; actual Python pauses and value comparisons; all 69 currently
installed theme variants; real file I/O and the five local calculations. AI
regressions use an explicit deterministic transport and do not measure model
intelligence. Packaged Windows verification is recorded separately.

This remains an unsigned Windows public preview with partial VS Code APIs.
See [feature boundaries](STATUS.md), [screenshots](media/r7/README.md), and the
[public One UI motion guidance](https://developer.samsung.com/one-ui/motion/basic.html).
