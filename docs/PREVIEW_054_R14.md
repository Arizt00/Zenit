# Zénit 0.5.4 R14

Detached editor windows now own their document's visible view. The main window
retains its shared in-memory model for synchronisation and undo, removes its tab
and split pane, and focuses the existing external editor when that file is opened
again. Returning or closing one window restores only that document after reading
its latest buffer. Unsaved text stays unsaved. Explorer, tab and editor menus use
this same handoff; a blank new-window command still opens a separate workspace.

The editor window has a cleaner code-window icon and the single status label
“Búfer compartido”. Run, Terminal and Use Zénit terminal begin as icons and expand
left with the same interruptible hover/focus motion as Laboratory, Forge and
Debug. Clicking or leaving collapses them; reduced motion is respected.

Extensions no longer changes the rail width or top-bar height at large window
sizes. Activity icons animate on pointer and keyboard activation without moving
their layout boxes. The catalogue has more compact headings, clearer metadata
and bounded action columns. Python, C, C++, nC and ASM package pages share an
aligned responsive two-column layout for environment setup and project packages.

Focus rings, selection and active backgrounds use quiet neutral shades in every
native theme. Compound fields have a single focus indicator. Monaco selections,
word matches and search highlights use the same shades, including when an
extension supplies the syntax theme. Branding and syntax token colours remain
independent from those interaction indicators.

## Lantern, Hilo and dependencies

- Each Python session offers a Packages action that activates its real Lantern
  interpreter and opens the package manager for that environment. The manager
  names the active session and explains how to retain its dependencies in .tern.
- Hilo caches Python inventories, invalidates them after dependency changes and
  exposes actual queued/running/completed/error counts. Completed workspace
  history can be cleared without cancelling jobs or clearing another workspace.
- Melody's text reveal retains fractional frame time instead of rounding up on
  each frame, so a high-refresh display does not accelerate the writing cadence.
- Existing Conan/ncc integration continues to supply installed dependencies to
  Run, Forge, Lantern, debugging and language services.

Lantern still supports temporary Python environments and session-owned QEMU/Arch
VM disks. Saving a .tern descriptor retains its backing directory under
.lumen/tern; unsaved environments are removed when closed. VM disk state is
retained, not guest RAM. QEMU and a prepared base image are configured from
Laboratory. This iteration does not claim complete VS Code API compatibility.
