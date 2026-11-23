# Zénit 0.5.5 R8 · nC language integration

This Windows preview extends the nC workflow without modifying the NCC compiler or replacing existing editor features.

## Changes
- Detects the nC toolchain under `%LOCALAPPDATA%/nC/bin` in addition to PATH and bundled SDKs.
- Offers two explicit language server profiles: general `nclsp` (via a persistent diagnostic bridge) and system `nc-sys-lsp lsp`.
- Both language servers use Zénit's existing, project-trusted LSP lifecycle; users authorize process startup.
- Provides an optional `ZENIT_NC_DEBUG_ENGINE=ncc` setting for `ncc debug-adapter` on `.n`/legacy `.nc`, alongside existing LLDB debugging.
- Maintains the distinct Machine `.nm` debugger workflow (`ncc machine debug-bridge` and `ncc machine debug-attach`).
- Preserves the official nC hexagon icon in file navigation and the Extensions catalogue.
- Keeps the installed nC extension version unchanged until a newer, verified VSIX is available. Zénit does not silently replace installed third-party extensions.

## Verification
- Test dual LSP discovery with real executables, opening and editing both normal and low-level files in a trusted workspace.
- Test NCC DAP breakpoints, stepping, scopes and variables; actual features depend on adapter capabilities.
- Verify that disabled/untrusted workspaces never start a language server.
- Verify that the released installer matches its GitHub Actions manifest and SHA-256 report.

This preview is not a guarantee that all NCC debugger operations are supported for every source mode. The nC compiler remains the authority for language correctness.
