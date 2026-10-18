# What works today

Zénit 0.5.4 R16 source is a public preview. No universal VS Code parity percentage is claimed.

| Area | Available | Boundary |
| --- | --- | --- |
| Editing | Monaco, splits, shared unsaved buffers, native windows, recoverable tab controls, original nC identity | Concurrent conflicts need resolution. |
| Binary editing | Paged hex/ASCII, local undo/redo, atomic byte patches with backups, source rebuild, native/Java execution | Fixed-size edits up to 64 KiB per save, files up to 1 GiB; rebuild needs source and a configured toolchain. Data and libraries require a host application. |
| Debugging | Native DAP memory/disassembly and observed pause comparison | Adapter-dependent capabilities; no reverse execution or complete instruction trace. |
| Terminal | Interactive ConPTY, multiple sessions, detachable views | Full VS Code shell integration remains pending. |
| Python | Included CPython/stdlib/pip/venv, base libraries, real package management in Extensions, automatic project interpreter | Defined library set; extra index packages need internet. Custom run commands remain explicit. |
| Native dependencies | Bundled GCC/LLVM/NCC/NASM base, project Conan and NCC package managers, language-service refresh | Additional registry downloads may need compilation. Custom builds remain explicit. |
| Forge | File runtime, Python buffer, C/GDB, repeat/stop, exit status | Toolchains must be configured; history belongs to the current Forge window. |
| Melody | Inline models, bounded local file memory, scope preview, session prompt drafts, live edits, file plans, recovery/undo, five local evidence tools | Providers need configuration; drafts last for the current window; generated code needs review. |
| Lantern | Unsaved-buffer execution, pin/follow, output comparison, read-only Melody consultation | History/output are bounded; checkpoints require cooperating code. |
| Internal orchestration | HILO backend subsystem registry, reverse dependency cleanup, bounded maintenance and shared discovery cache | No HILO product panel. Foreground execution remains independent of maintenance. |
| Saved spaces and recovery | Per-project panel/tab/style snapshots, split order, cursor/scroll and durable dirty text | 12 named spaces, 48 documents, 2 MiB per dirty buffer / 8 MiB total. Binary patches require explicit save. |
| Execution target | Shared persistent local/WSL/SSH target for file run/check, including CoCo host runtime plans | SSH requires files already present remotely. Cooperative checkpoints, DAP and buffer-specific Forge modes currently require local execution. VM console is separate. |
| SDK components | Reusable prepared roots and verified optional ZIP imports with exact SHA-256 manifests | Local component packages; no automatic remote component repository. Imported tools run with the current user when explicitly invoked. |
| Session environments | Real Python venvs and QEMU/Arch machines, workspace `.tern` descriptors | VM base is optional. Disk checkpoints retain backing files, not RAM. |
| Voice | Existing local Emma bridge | Requires a compatible local voice installation. |
| Search | Literal matching lines, filters, UTF-16 positions | No regex/bulk replace yet; up to 200 visible results. |
| Extensions | List/cards/compact layouts, factory nC package, Open VSX/VSIX, declarative contributions, authorized Node engines, file icon themes | Partial VS Code API; product icon themes remain pending. |
| Appearance | Three palettes, local profile, reduced motion, native panels | Advanced legacy workflows still have some Spanish messages. R11 presentation uses English. |
| Distribution | Verified Windows installer and portable | Current preview is unsigned; new Linux/macOS builds need platform checks. |

AI tests use deterministic transports to verify scope and file/UI behavior, not
to benchmark provider intelligence. See [historical limits](../KNOWN_LIMITATIONS.md).

R15 adds Co-Code (CoCo) Yjs/Yrs shared buffers, host execution and cross-IDE connectors. See [Team](TEAM.md) and [R15](PREVIEW_054_R15.md) for tested integrations and remaining API limits.

R16 moves HILO entirely behind the product UI, restores workbench sessions independently of the backend port, pauses Melody display animation in hidden windows, caches unchanged Lantern checkpoints and corrects VS Code Position/Range/Selection semantics. See [R16 notes](PREVIEW_054_R16.md).
