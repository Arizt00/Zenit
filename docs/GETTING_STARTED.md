# Your first session in Zénit

## Install on Windows

Use the installer or portable ZIP from the [R9 release](https://github.com/Arizt00/Zenit/releases/tag/v0.5.4-preview.9).
The current binary target is Windows 10/11 x64 with Edge WebView2. The portable
must be fully extracted; run `Zenit/zenit.exe`. No separate Python installation
is needed to run the IDE. Project toolchains are separate.

Checksums are included in the release. Compare the downloaded installer with its
SHA-256 entry:

```powershell
Get-FileHash ./Zenit-0.5.4-R9-Windows-Setup.exe -Algorithm SHA256
```

These preview executables are unsigned. Linux/macOS packages from older releases
do not represent a newly verified R9 build on those systems.

## Open and run a project

1. Select **Open project** and choose a folder.
2. Open or create a file. A new profile begins with an empty recent-file history.
3. Configure required tools in **Settings → Languages and tools**.
4. Use **Run** or **Forge**. Forge’s main Run action saves a dirty file before
   preparation/execution. Python’s **Run buffer** action uses unsaved code instead.

An interactive program reads from the terminal. Completed Forge executions show
their exit code; **Run again** repeats that file. **Stop** ends the tracked process.

## Work across windows

Open an editor’s actions and detach it. The editor fills the external window and
has a terminal directly below it. Drag the separator to resize the terminal,
toggle it with `Ctrl+J`, or detach the terminal again. **Use Zénit terminal** hides
the exterior terminal and returns to the main application’s terminal.

Buffers, saves, appearance and project changes synchronize. A concurrent conflict
is preserved for resolution rather than silently overwriting another edit.

## Configure Melody

Use **Connect a model** to choose an integration and an actual model. Local
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
