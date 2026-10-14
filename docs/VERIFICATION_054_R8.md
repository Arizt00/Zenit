# R8 verification — 14 October 2026

The Windows build comes from source commit
`4ee4ff2e1fdccd4dff6df232f3928c1303108fb0`. The following results cover the R7
implementation and its final model, factory extension and motion follow-ups;
R8 packages that work alongside the user's active R7 installation.

- 341 Python tests: 336 passed, 5 platform skips; no failures.
- 109 Node tests and 78 JavaScript syntax checks.
- 46 browser workflow groups across four suites: interface refinements, existing
  R6 workflows, terminal/window synchronization and the latest follow-ups.
- 75 actual installed theme variants, including the six nC variants: computed
  text, field, button and card contrast; visible borders; no horizontal overflow;
  unchanged Monaco document model.
- Actual GCC/LLDB disassembly and bounded memory reads, plus actual Python pauses
  and value comparison. Unsupported operations remain explicit.
- 15 packaged native checks and installer integrity verification.
- 28 checks of the installed WebView2 application, including native external
  binary paging, real terminal detach/return, floating read-only Debug
  consultation, extension isolation and profile cropping. All 140 inspected
  source/asset files match the verified bundle.
- The stable launcher resolves to R8. Installation keeps the running R7 process,
  the previous payload, shared Java/C++/Python SDK selections and the settings,
  profile, session and extension index present at installation time.
- The unchanged factory nC VSIX is installed once. The separate factory-install
  check preserved all 16 previous extensions, settings, session and icon choice.
  Its Node engine was not started in the user's profile. An isolated trusted
  engine regression registered its actual language providers and returned
  semantic tokens without unsupported API calls.

The quick model selector is tested with an explicitly declared catalog. AI
consultation tests use deterministic transports to verify scope, read-only
behavior and UI/file handling. They do not certify provider intelligence,
account entitlement or a successful response from every advertised model.

Screenshots in [the feature gallery](media/r7/README.md) were captured during
R7 development from an isolated Aurora/Alex profile. They are actual application
captures. The user's profile photo and live project are not included.

Machine-readable records are in `tests/visual/evidence/windows-054-r8-*.json`.
The nC factory installation receipt is
`tests/visual/evidence/windows-054-r7-nc-factory.json`.

Windows remains an unsigned public preview with partial VS Code APIs. No new
Linux/macOS verification or globally unique AI capability is claimed.
