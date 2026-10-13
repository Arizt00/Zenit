# R5 final verification

- 325 Python tests: 320 passed, 5 platform skips; no failures.
- 104 Node tests; 69 JavaScript syntax checks.
- 90 prior UI regressions plus 12 new R5 workflow checks.
- 15 packaged native checks, installer integrity, and 21 installed WebView2 checks.
- 117 installed source/asset files match the verified build.
- Actual Python/ConPTY run, repeat, stop and exit code; selective Melody scope/undo uses explicit fixture transport.
- Stable launcher and two shortcuts open R5. An existing user session was kept running.
- Profiles/history/extensions and shared SDK index preserved; only the requested English locale was changed.
- Five GitHub assets published with verified remote SHA-256 digests.
- English DEV article publicly verified, with real application images.

Core UI and install/uninstall flows use English. Advanced legacy messages remain
listed in STATUS. Windows remains an unsigned public preview; no new Linux/macOS
or universal VS Code compatibility claim. AI tests do not benchmark model quality.
