# Zénit third-party components

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

LLVM, GCC, .NET SDK, JDK, Node, Rust, Go, Git, ncc and AI models are external tools with their own licenses and requirements. Credentials, model weights and a copy of the nC repository are not included. Local nC paths are device configuration.

Zénit’s original code and documentation use Apache-2.0, as provided in LICENSE and NOTICE. The independent tools/asm_worker.py retains GPL-2.0-or-later. Third-party licenses remain independent. Trademarks do not imply affiliation. Provider integrations retain their own terms. The VSIX host supports declarative contributions and a partial Node API, not the full VS Code extension host.

The baseline includes github-copilot-sdk 1.0.15 and Python dependencies, with notices in licenses/python-packages. Official Codex, Claude Code, Gemini CLI and Copilot CLI clients are installed separately; sessions and credentials are not distributed.
# Independent ASM laboratory

The source of `tools/asm_worker.py` is GPL-2.0-or-later; see
`licenses/asm-worker/GPL-2.0.txt`. It runs as an independent Python process using
Unicorn (GPL-2.0), Capstone (BSD), pyelftools (public domain) and LLVM command-line
tools (Apache-2.0 with LLVM exception). These development tools are not silently
included in the public core installer. `tools/prepare_foundation.py` prepares a
local SDK from installed tools and verified upstream downloads. Redistribution
of that SDK requires its own corresponding-source and licensing review.

TextMate highlighting uses vscode-textmate 9.2.0 (MIT) and the vscode-oniguruma 2.0.1 bindings (MIT), including their Oniguruma WASM. The underlying Oniguruma engine uses the BSD-style notice preserved in `licenses/oniguruma/COPYING`; `SOURCE.json` records the exact upstream submodule commit. The binding license notices are preserved in web/vendor/textmate and web/vendor/oniguruma. These libraries are pinned and checked against npm SHA-512 integrity at asset preparation.
