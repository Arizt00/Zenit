# R11 verification — 14 October 2026

- Python: 352 tests run, 347 passed and 5 platform skips.
- Node: 113 tests passed, including bounded output comparison and revision evidence.
- Frontend JavaScript syntax: 72 files passed.
- Browser workflows: 12 motion lifecycle groups, 7 new Melody/Lantern groups,
  8 existing model/nC groups, 11 profile/session groups and 12 existing workflow
  groups, plus 7 real Python package-management groups and 9 context-menu,
  layout and memory groups. Total: 66 groups.
- Native checks install a real offline Conan header package, compile C/C++,
  verify clangd hover, preserve dependencies on failed resolution, and execute
  NASM/GNU assembly. A separate network probe downloads zlib and fmt and runs
  programs linked against them; NCC package initialization, locking and execution
  are exercised with the actual compiler.
- Memory checks verify persistence, scope separation, current-source precedence
  and forget behavior across new conversations.
- Python package checks install an explicit offline wheel using real pip, import
  it through Run, Forge, Lantern and debugging, check dependencies and remove
  only the project package. Invalid requirements and pip removal are rejected.
- New execution checks use actual Python processes and unsaved buffers. They
  verify pin/follow behavior, actual output comparisons, read-only consultation
  and inline model selection without opening Settings.
- Motion checks include current-frame interruption, isolated dismissal, preserved
  canvas/scroll/control state, reduced motion, GPU pause behind overlays and
  bounded panel travel without clipping.
- Installed Windows application: 40 checks passed in a disposable profile,
  including the shared home/Melody crystal, local file memory, extension layouts,
  original language icons, packaged compiler execution and real project packages
  used by Run, Forge, Lantern and the Python debugger. The stable launcher opens
  R11; existing profile files and the shared SDK index were preserved.
- Packaged Windows application: 15 native GUI/runtime checks passed. Installer
  integrity verification checks its exact payload file set and the hashes of
  the application, launcher, uninstaller and included tool executables.

Package, installed application and publication receipts are recorded separately
in `tests/visual/evidence/windows-054-r11-*.json`. The installed verifier reports
whether the decorative canvas was running or paused when its window was covered;
paused background rendering is expected behavior.

AI tests use declared deterministic responses and catalogs. They do not certify
provider intelligence or account entitlement. Theme coverage from R8 is retained
as historical evidence; no new full theme matrix is claimed by this revision.

## Windows uninstall repair — 15 October 2026

The native toolchain includes read-only SDK files, such as
`native-mingw/lib/tcl8.6/msgs/af.msg`. The original R11 uninstaller could stop
with Windows error 5 when removing these files. Removal now clears only the
read-only attribute of a validated, installer-owned path before retrying.
Genuine sharing/permission errors still stop removal and allow a retry.

- 19 focused regression checks passed: read-only toolchain and launcher files,
  actual Windows file locks, retry after partial removal, preserved profiles and
  projects, rejected junctions, installer upgrades, and real isolated HKCU
  registration with spaces and Unicode in installation paths.
- The rebuilt standalone uninstaller passed an actual native GUI run against a
  disposable installation. It relocated itself and its working directory,
  removed the read-only SDK fixture and its own installed executable, and kept
  the profile and both internal and external projects. No JavaScript errors were
  reported.
- Registration uses the stable installation root, an explicit uninstall target,
  and visible/uninstallable Windows metadata. The legacy registry key remains
  compatible with existing installations; unsupported Modify/Repair actions are
  disabled.
- The installed R11 uninstaller was replaced with the verified binary. Windows
  Programs and Features was checked directly: Zénit 0.5.4 is listed and exposes
  Uninstall/Change, which opens the corrected review interface. The application
  was not removed as part of the repair; data deletion remains unchecked by
  default.

Verified standalone executable SHA-256:
`e3e293f0373b79fd970e32d27391446944fa9cc4bef419a5a11d881ba5fe5bc9`.

This repair rebuilds the standalone uninstaller and fixes installer source.
Previously published full R11 installer/portable downloads are unchanged.
