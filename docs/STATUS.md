# What works today

Zénit 0.5.4 R11 is a public preview. No universal VS Code parity percentage is claimed.

| Area | Available | Boundary |
| --- | --- | --- |
| Editing | Monaco, splits, shared unsaved buffers, native windows, recoverable tab controls, original nC identity | Concurrent conflicts need resolution. |
| Binary inspection | Paged hex/ASCII, byte offsets, endian and numeric interpretation | Read only; no binary editing or full media previews. |
| Debugging | Native DAP memory/disassembly and observed pause comparison | Adapter-dependent capabilities; no reverse execution or complete instruction trace. |
| Terminal | Interactive ConPTY, multiple sessions, detachable views | Full VS Code shell integration remains pending. |
| Python | Included CPython/stdlib/pip/venv, base libraries, real package management in Extensions, automatic project interpreter | Defined library set; extra index packages need internet. Custom run commands remain explicit. |
| Forge | File runtime, Python buffer, C/GDB, repeat/stop, exit status | Toolchains must be configured; history belongs to the current Forge window. |
| Melody | Inline models, scope preview, session prompt drafts, live edits, file plans, recovery/undo, five local evidence tools | Providers need configuration; drafts last for the current window; generated code needs review. |
| Lantern | Unsaved-buffer execution, pin/follow, output comparison, read-only Melody consultation | History/output are bounded; checkpoints require cooperating code. |
| Voice | Existing local Emma bridge | Requires a compatible local voice installation. |
| Search | Literal matching lines, filters, UTF-16 positions | No regex/bulk replace yet; up to 200 visible results. |
| Extensions | Factory nC package, Open VSX/VSIX, declarative contributions, authorized Node engines, file icon themes | Partial VS Code API; product icon themes remain pending. |
| Appearance | Three palettes, local profile, reduced motion, native panels | Advanced legacy workflows still have some Spanish messages. R11 presentation uses English. |
| Distribution | Verified Windows installer and portable | Current preview is unsigned; new Linux/macOS builds need platform checks. |

AI tests use deterministic transports to verify scope and file/UI behavior, not
to benchmark provider intelligence. See [historical limits](../KNOWN_LIMITATIONS.md).
