# Zénit 0.5.4 R12 — Session environments and a quieter workspace

Editor splits can now be joined by dragging an open tab or pane title into the
center of the editor, or using **Join editors** in the pane header. Both unsaved
buffers are retained. Edge drops still create a split.

## Interface

- Settings removes the top divider and visible scrollbars while preserving
  wheel, touchpad and keyboard scrolling. Long fields wrap within the sheet.
- Collapsed Project and Melody rails retain the panels' rounded outline.
- Laboratory and Forge start as icons, reveal their labels on hover or keyboard
  focus, and return to their original size after opening or pointer exit.
- Editor submenus have a 12 px separation and flip inward at the window edge.
- Repository controls, action groups and badges have consistent spacing.
- Detach actions use a restrained overlapping-window symbol. Extension artwork
  has consistent padding and framing. Language icons, including nC, are retained.
- Files and Commands use a stable palette height and a short opacity transition.
- Motion-disabled and system reduced-motion preferences remain supported.

## Melody

Live responses append text at display cadence without rebuilding the complete
message on every poll. Large provider chunks catch up over several frames;
Unicode surrogate pairs remain intact. Scrolling upward stops automatic following.
The completed response retains the existing Markdown rendering and review flow.
This improves presentation work, not the provider's inference speed.

**Ask Melody** in Lantern supplies the actual environment and application
inventory with the current file, so setup advice can identify missing tools.
The model picker, file memory and existing chat/edit capabilities stay in place;
the main conversation panel does not gain another permanent toolbar.

## Lantern and Hilo

**Laboratory → Lantern** creates temporary Python environments or real Arch Linux
QEMU machines. Save a `.tern` descriptor in the workspace to retain the backing
environment and reopen it later. Unsaved environments are removed when their
session ends normally. See [the environment guide](SESSION_ENVIRONMENTS.md) for
storage, interpreter switching and VM prerequisites.

Hilo starts automatically in the backend without elevation. It serializes
project package work, provides a bounded maintenance queue with cancellation,
and caches tool discovery for a short interval. Foreground runs do not wait
behind queued package jobs. It is an application scheduler, not a system service
or a claim that all editing and I/O operations are now asynchronous.

**Settings → Connections** detects seven explicit adapters. Connection management
is kept out of the IDE and Laboratory panels:

| Application | Implemented action |
| --- | --- |
| Codex / ChatGPT | Open the official Codex CLI in the current workspace and Melody's account profile. |
| Claude Code | Open the official CLI in the project with its provider profile. |
| Gemini | Open the official CLI in the project with its provider profile. |
| Blender | Open a saved `.blend`, or run the active saved Python script in Blender's background process. |
| Unity | Open a Unity project containing `ProjectSettings`. |
| Unreal Engine | Open the active saved `.uproject`. |
| GitHub | Read repository metadata with `gh repo view`. |

These actions require the relevant application. Detection does not mean that
an account is signed in. Sign-in, subscription limits and tool permissions stay
with each official client. They do not send an implicit prompt, publish a change,
or provide unrestricted agent control of these applications.

## Reliability and compatibility

Changing Python environments restarts the affected language service using the
new interpreter. Late requests to retired sessions no longer produce a spurious
“unknown LSP session” notification. Package process failures remain failures in
Hilo instead of appearing as completed maintenance.

This build also includes the Windows uninstaller repair: read-only owned SDK
files can be removed, failed cleanup can be retried, and installation registration
keeps Zénit visible in Windows' installed application list.

VS Code parity advances through usable editor groups, language-service refresh,
context menus and project environments. The extension API remains partial;
complete VS Code compatibility is not claimed.
