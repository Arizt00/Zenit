# Zénit 0.5.4 R11 — A calmer workspace, connected project tools

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
- The main panel keeps two concise suggestions and the composer. The duplicate
  Connect row is removed; clicking Melody opens the model picker. Tools and
  Context and memory live in one secondary panel.
- Melody uses the same larger glass crystal and inclined orbit as the home
  screen, with the same renderer, geometry and material.
- Local file memory carries successful exchanges into later conversations,
  scoped by project, file and provider. Current source always takes precedence
  over remembered code. Pause and forget controls remain visible in Context
  and memory; no-code questions bypass it.

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

## Python included, project packages in Extensions

Windows installer and portable builds include standalone CPython 3.12.10, its
standard library, pip, venv and the prepared base libraries with their actual
transitive dependencies. The base includes requests, pytest, NumPy, pandas,
Matplotlib, Pillow and python-lsp-server. `pip check` verifies the packaged base.
This is a defined library set, not every package available on PyPI.

**Extensions → Python** shows actual installed distribution metadata, supports
package names with version constraints/extras, requirements.txt installation,
updates, project-local removal, dependency checks, filtering and copying pinned
project versions. Installer output and cancellation are available in the panel.
The first installation creates `.venv` and inherits the read-only base libraries;
additional packages and overrides stay in the project. Existing incomplete
environments are preserved and reported rather than replaced.

Run, Forge, Lantern and built-in Python debugging automatically use the ready
project environment. Lantern keeps that interpreter while executing its private
unsaved source copy. Full custom run profiles retain their explicit commands.
Other language SDKs and user extension/icon choices are retained.

## Native tools and dependency integration

Windows includes GCC/G++, GDB, Clang/clangd, LLVM tools, CMake, Ninja, NCC and NASM.
Extensions → Native supports C, C++, nC and ASM. C/C++/ASM use project-local Conan
requirements and generated CMake metadata; nC uses NCC's own package commands.
Successful resolution refreshes affected language services and supplies include,
define and link flags to built-in execution and Lantern. Failed resolution keeps
the previous working dependency set. Explicit project build commands and compile
databases take priority.

The distribution retains tool licenses and the corresponding MSYS2 source
archives, patches and build recipes. Additional SDKs and user icon choices are
preserved. The base is a defined toolset, not every library in each ecosystem.

## Editor and extension workflows

- A searchable floating editor menu supports Shift+F10, nested keyboard
  navigation, real Monaco language actions, Melody drafts, execution, project
  dependencies and active extension commands. Unsupported language actions are
  omitted. This is still a partial VS Code API implementation.
- Extensions offers persistent List, Cards and Compact layouts, with
  interruptible position/opacity transitions and reduced-motion support.
- Opening an editor file now updates Melody's context immediately, even if
  keyboard focus has not entered the code area.
