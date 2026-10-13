---
title: "Zénit: a desktop workspace for code, AI assistance and real execution"
published: false
tags: opensource, python, javascript, productivity
description: "A first look at Zénit: Monaco, shared editor windows, scoped AI context and Forge’s real execution loop."
cover_image: https://raw.githubusercontent.com/Arizt00/Zenit/main/docs/media/workspace-dark.png
---

Moving a file to a second monitor should not disconnect it from the rest of your
work. Asking an assistant about a selection should not quietly send the whole
file. And a Run button should tell you what actually happened.

Those are the workflows behind **Zénit**, a desktop coding workspace built with
a Python backend, a JavaScript frontend, Monaco and native webview windows.
I’m sharing its **0.5.4 R5 public preview**, now with Apache-2.0 licensing and a
clearer path for contributors.

![Zénit dark workspace: editing, terminal and Melody](https://raw.githubusercontent.com/Arizt00/Zenit/main/docs/media/workspace-dark.png)

## One workspace, more than one window

Zénit keeps the editor, explorer, terminals and assistance together, but it does
not force them onto one monitor. Detach an editor and its terminal sits directly
below the code. Resize it, detach the terminal separately, or use the terminal in
the main application instead.

The important part is the shared buffer. Unsaved edits and saves synchronize
between the application and the external editor. Concurrent conflicts are kept
for resolution rather than silently overwritten. Appearance and project-tree
changes also update across the views.

This takes more than rendering a second page: document revisions, shell input,
active-view terminal resizing and window ownership all need to agree.

## Melody: make the scope visible

Melody is the development assistant in the workspace. Connect a local engine or
a supported provider and model; Zénit does not bundle a hosted AI subscription.

R5 makes the request’s destination and context visible. For questions, choose
**Selection or file**, **Whole file** or **No code**. This fixes a concrete problem:
the old context selector existed, but the question path still included the file.

There is also a separate **Edit file** mode for live buffer changes. It uses the
complete file because an edit must preserve the surrounding code. A reviewed
selection suggestion, by contrast, can replace only the range captured with the
request. If the buffer changed afterwards, the stale proposal is rejected. Undo
remains available.

File plans can create, update or delete named session files with recovery copies
and review. I’m careful to separate testing that workflow from claiming that a
model is universally reliable: deterministic transport tests verify context and
file behavior, not the intelligence of a provider.

## Forge: close the execution loop

Forge is the execution workspace. Its main Run action saves the current file,
prepares the configured runtime and starts an interactive terminal. Python also
has **Run buffer** for unsaved editor content; C/GDB has its own debugging action.

![Forge after a real Python execution](https://raw.githubusercontent.com/Arizt00/Zenit/main/docs/media/forge.png)

Try this small file:

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"

print(greet("Zénit"))
```

Open it in Forge and select **Run Python**. The terminal shows the program’s
output; the execution card reports elapsed time and the real exit code.
**Run again** repeats the captured file. **Stop** ends that tracked process
without closing unrelated terminal sessions.

## Design is part of the workflow

R5 uses coordinated headers, quieter surfaces, clear primary actions and visible
keyboard focus. There are light, dark and forest palettes. Motion respects reduced
motion settings; scrolling works without permanently visible scrollbar chrome.

The welcome screen and My activity provide another route back into a project.
The screenshots here are the running application with a small demo workspace;
Forge output is real, and no simulated AI answer is presented as a model result.

![Zénit welcome](https://raw.githubusercontent.com/Arizt00/Zenit/main/docs/media/home.png)

## Try it and help shape the next iteration

The current verified binary is **Windows 10/11 x64**, with Edge WebView2. The
release offers an installer, portable ZIP, manifest and SHA-256 checksums. Preview
binaries are unsigned. The IDE has its own Python runtime; project toolchains
and AI integrations are configured separately.

Zénit is still a preview. VS Code extension compatibility is partial, regex/bulk
replace are future work, and current Linux/macOS packages need separate build
and verification. Original code and documentation use Apache-2.0; the independent
ASM worker and dependencies retain their existing licenses.

- [Explore the code and screenshots](https://github.com/Arizt00/Zenit)
- [Download the R5 preview](https://github.com/Arizt00/Zenit/releases/tag/v0.5.4-preview.5)
- [See working features and boundaries](https://github.com/Arizt00/Zenit/blob/main/docs/STATUS.md)
- [Contribute a focused improvement](https://github.com/Arizt00/Zenit/blob/main/CONTRIBUTING.md)

I’d especially like feedback on detached-window editing, terminal behavior at
different DPI settings, and whether Melody’s context controls make the request
scope understandable. What part of the edit → run → inspect loop would you improve first?
