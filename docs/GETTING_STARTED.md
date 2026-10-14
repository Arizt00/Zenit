# Your first session in Zénit

## Install on Windows

Use the installer or portable ZIP from the [R11 release](https://github.com/Arizt00/Zenit/releases/tag/v0.5.4-preview.11).
The current binary target is Windows 10/11 x64 with Edge WebView2. The portable
must be fully extracted; run `Zenit/zenit.exe`. No separate Python installation
is needed to run the IDE or Python projects. C/C++, nC and ASM tools are also
included in the Windows base; other language toolchains can be added separately.

Checksums are included in the release. Compare the downloaded installer with its
SHA-256 entry:

```powershell
Get-FileHash ./Zenit-0.5.4-R11-Windows-Setup.exe -Algorithm SHA256
```

These preview executables are unsigned. Linux/macOS packages from older releases
do not represent a newly verified R11 build on those systems.

## Open and run a project

1. Select **Open project** and choose a folder.
2. Open or create a file. A new profile begins with an empty recent-file history.
3. Configure required tools in **Settings → Languages and tools**.
4. Use **Run** or **Forge**. Forge’s main Run action saves a dirty file before
   preparation/execution. Python’s **Run buffer** action uses unsaved code instead.

An interactive program reads from the terminal. Completed Forge executions show
their exit code; **Run again** repeats that file. **Stop** ends the tracked process.

## Add Python dependencies

Windows builds include standalone CPython 3.12.10, the standard library, pip,
venv, requests, pytest, NumPy, pandas, Matplotlib, Pillow, python-lsp-server and
their dependencies. The bundled inventory is visible in **Extensions → Python**.

1. Open your project and select **Extensions → Python**.
2. Enter a package, such as `rich`, `requests>=2.32` or `httpx[http2]>=0.27`,
   then select **Install**. Alternatively, use **Install requirements.txt**.
3. The first installation prepares `.venv`, inheriting the bundled base libraries.
   The panel shows actual pip output, completion or errors, and a stop action.
4. Use Run, Forge, Lantern or built-in Python debugging. They automatically use
   the ready `.venv`, including when Lantern executes an unsaved copy.

The **Project** list supports updates and removal of local packages. Base packages
remain intact; updating one adds an override to the project. **Check dependencies**
runs pip's compatibility check. **Copy project versions** copies local package pins.
Custom run profiles with explicit commands keep those commands. An ordinary shell
requires environment activation, for example `.venv\Scripts\Activate.ps1` in
PowerShell. Installing additional packages from the index requires internet access.

## Add C, C++, nC or ASM dependencies

The Windows base includes GCC/G++, GDB, Clang/clangd, LLVM tools, CMake, Ninja,
NCC, NASM and the GNU assembler. Open **Extensions → Native** and choose a
language. Tool status uses detected executable paths.

- **C / C++ / ASM:** enter a Conan reference such as `zlib/1.3.1`. Install,
  resolve, check or remove requirements. The project has its own Conan cache
  and generated CMake files under `.lumen/dependencies`.
- **nC:** use **Initialize** only for a new package, then add a module such as
  `stoud::io`. Zénit uses NCC's own package manifest and lock/check commands.
  Existing source or manifests are preserved.
- Successful resolution updates the built-in runtime and Lantern flags and
  refreshes the affected language services. Clangd receives generated compile
  commands unless the project supplies its own. Explicit custom run/build
  commands remain under your control.

These managers use each ecosystem's real capabilities. They do not turn arbitrary
VS Code extensions into language runtimes. Additional registry packages require
internet access and may compile from source.

## Choose the extension layout

Use the three view buttons in **Extensions** for **List**, **Cards** or **Compact**.
The choice stays on this device. Transitions respect reduced motion and the
animation preference.

## Editor actions

Right-click code or press **Shift+F10**. Search actions or open submenus for
navigation, Peek, refactoring, Melody, execution and installed extension commands.
Language actions appear when the editor exposes that capability. **Project
Dependencies** opens the package panel for Python or native languages.

## Work across windows

Open an editor’s actions and detach it. The editor fills the external window and
has a terminal directly below it. Drag the separator to resize the terminal,
toggle it with `Ctrl+J`, or detach the terminal again. **Use Zénit terminal** hides
the exterior terminal and returns to the main application’s terminal.

Buffers, saves, appearance and project changes synchronize. A concurrent conflict
is preserved for resolution rather than silently overwriting another edit.

## Configure Melody

Click the **Melody** title to open its model subpanel. Choose an integration and
an actual model without leaving the conversation. **Manage account** opens
provider configuration when needed. Local
engines must be running/configured; API and official-client providers require
their own credentials or sign-in. A web subscription does not automatically
grant API access.

- **Chat:** ask questions or name intended file actions. For questions, choose
  **Selection or file**, **Whole file** or **No code**.
- **Edit file:** explicitly request live changes to the active buffer. This mode
  needs the whole file even if question context is set to a selection or no code.
- **Review selection:** apply a suggestion only to the range captured with the
  request. Editing the file afterwards invalidates the stale proposal.
- **Files and project:** request a file plan by naming paths. Review, recovery
  and undo remain available.
- **Live assistance:** enable contextual advice or next-code suggestions. The
  existing Emma speech integration requires a compatible local voice bridge.

The small tools button beside **Chat / Edit file** opens **Tools** and
**Context and memory**. It contains the extra actions, context preview and
session drafts, keeping the main conversation clear.

**Remember this file** is enabled for code-scoped requests. Successful exchanges
are stored locally, separately for each project, file and provider. Starting a
new conversation does not erase this memory; a later request still attaches the
latest editor content. The store is bounded (six exchanges per file, up to fifty
file/provider entries), and is not a complete chat archive. Disable the checkbox
to pause its use, or choose **Forget file** to erase that provider's memory and
transient conversation history for the file. **No code** sends no file memory.

Choose routine-action confirmations under **Settings → Security**. Conflict and
revision checks remain active in direct mode.

## Personalize

Choose light, dark or forest. Install a compatible file icon theme through
Extensions, then select it under Appearance. **My activity** resumes real recent
files/projects. Your profile and faded image cover remain local to the device.
English is the initial language; the language selector remains available.

## Need help?

Use [Discussions](https://github.com/Arizt00/Zenit/discussions) for questions and
the [bug form](https://github.com/Arizt00/Zenit/issues/new?template=bug_report.yml)
for reproducible failures. Include revision, OS and DPI. See [feature status](STATUS.md)
before relying on a compatibility goal.
