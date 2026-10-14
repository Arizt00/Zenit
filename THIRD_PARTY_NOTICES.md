# Zénit third-party components

The original nC language icon and its alternative SVG are from Arizt00/ncc.
The MIT license and provenance are retained in `web/assets/languages/nc-NOTICE.md`.
The original nC extension VSIX, with its upstream MIT OR Apache-2.0 licenses,
is bundled under `web/assets/extensions`; its factory manifest pins SHA-256.

Provider identity SVGs are from Simple Icons 13.21.0 (CC0-1.0).
Their sources and trademark notice are retained in `web/assets/providers/NOTICE.md`.

Distributions load local libraries without a frontend CDN. The table records the baseline Windows inventory. Current builds include `licenses/native-python/PACKAGE_INVENTORY.json` with actual Python package versions and licenses. Linux uses PySide6/QtWebEngine and qtpy; macOS uses PyObjC/Cocoa/WebKit. Their notices remain with the inventory and packaged runtime.

| Component | Baseline version | Source |
|---|---|---|
| Monaco Editor | 0.52.2 | npm monaco-editor / Microsoft |
| Babylon.js | 8.32.0 | npm babylonjs |
| Three.js | 0.180.0 | npm three |
| xterm.js / addon-fit | 5.5.0 / 0.10.0 | npm @xterm |
| pywebview | 6.2.1 | PyPI / pywebview |
| Main Python | 3.12.10 | python.org / PSF |
| LLDB helper Python | 3.11.9 embeddable amd64 | python.org / PSF |
| pywin32 | 312 | PyPI; Windows uninstaller integration |
| pywinpty | 3.0.5 | PyPI; includes OpenConsole and winpty-agent |
| websocket-client | 1.9.2 | PyPI |
| NetCoreDbg | 3.2.0-1092 | github.com/Samsung/netcoredbg |
| Delve | 1.27.2, built with Go 1.27.1 | github.com/go-delve/delve |

License texts are preserved beside web/vendor, in debugger-support and in licenses. Delve dependencies retain notices under licenses/delve-dependencies. Python notices are under licenses/python-packages. PyInstaller is a build tool; its bootloader license includes a distribution exception.

UI fonts come from the system. Icons are local SVGs. Existing landscape assets come from project references; a full screenshot is not used as a substitute for the interface.

.NET SDK, JDK, Node, Rust, Go, Git and AI models can be configured separately and retain their own licenses and requirements. The Windows R11 base includes LLVM, GCC, NCC and NASM with the notices described below. Credentials, model weights and a copy of the nC repository are not included. Local nC paths are device configuration.

Zénit’s original code and documentation use Apache-2.0, as provided in LICENSE and NOTICE. The independent tools/asm_worker.py retains GPL-2.0-or-later. Third-party licenses remain independent. Trademarks do not imply affiliation. Provider integrations retain their own terms. The VSIX host supports declarative contributions and a partial Node API, not the full VS Code extension host.

Windows R11 also includes standalone CPython under `sdk/foundation/python`.
Its `LICENSE.txt`, package metadata and package license files are retained.
`requirements-bundled.txt` records the actual base library versions separately
from the IDE's frozen runtime. Project packages are installed into `.venv` and
are not part of the distributed base.

The baseline includes github-copilot-sdk 1.0.15 and Python dependencies, with notices in licenses/python-packages. Official Codex, Claude Code, Gemini CLI and Copilot CLI clients are installed separately; sessions and credentials are not distributed.
# Independent ASM laboratory

The source of `tools/asm_worker.py` is GPL-2.0-or-later; see
`licenses/asm-worker/GPL-2.0.txt`. It runs as an independent Python process using
Unicorn (GPL-2.0), Capstone (BSD), pyelftools (public domain) and LLVM command-line
tools (Apache-2.0 with LLVM exception). Windows R11 includes the Python libraries
in its standalone base, with original notices and unchanged upstream source
archives for Unicorn and pycdlib under `sdk/foundation/python/sources`.
`SOURCE_INDEX.json` records their versions, upstream URLs and verified SHA-256.
`tools/prepare_foundation.py` prepares the Python base;
`tools/prepare_native_base.py` prepares the Windows native dependency closure.

TextMate highlighting uses vscode-textmate 9.2.0 (MIT) and the vscode-oniguruma 2.0.1 bindings (MIT), including their Oniguruma WASM. The underlying Oniguruma engine uses the BSD-style notice preserved in `licenses/oniguruma/COPYING`; `SOURCE.json` records the exact upstream submodule commit. The binding license notices are preserved in web/vendor/textmate and web/vendor/oniguruma. These libraries are pinned and checked against npm SHA-512 integrity at asset preparation.

## Windows native base

The native base includes LLVM 22.1.6 (Apache-2.0 with LLVM exception), GCC and
its runtime libraries (GPL-3.0 and the applicable GCC Runtime Library Exception),
GDB and GNU binutils (GPL), CMake (BSD), Ninja (Apache-2.0), NCC (MIT OR Apache-2.0)
and NASM 2.16.03 (BSD-2-Clause). Original notices remain alongside the tools.
Conan 2.21.0 (MIT) and its Python dependency notices remain in the standalone
Python environment.

`sdk/foundation/native-sources/PACKAGE_INVENTORY.json` records exact versions and
license identifiers for the 59 MSYS2 packages in the native dependency closure.
`SOURCE_INDEX.json` records the official source URLs, sizes and SHA-256 values
of 57 corresponding source archives. Those archives, including original upstream
sources, packaging recipes and patches, are distributed with the binary tools.
They can be extracted with an archive manager supporting their compression.
LLVM's original license is retained in `sdk/foundation/llvm/LICENSE.TXT`; NCC's
upstream notices and both license texts accompany its executable. No user's
project or private package cache is included in the distribution.
