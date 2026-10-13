# R6 verification — 13 October 2026

- 325 Python tests: 320 passed, 5 platform skips; no failures.
- 106 Node tests and 73 JavaScript syntax checks.
- 49 browser workflow checks across four suites; the theme suite includes 89
  actual installed theme variants and synchronization with a separate window.
- 15 packaged native checks and installer integrity verification.
- 24 installed WebView2 checks, including floating Debug consultation,
  Extensions isolation, brand identities and terminal detach/return.
- 126 installed source/asset files match the verified bundle.
- Stable launcher and two shortcuts resolve to 0.5.4 R6.
- Settings, profile, session, extension index and Java/C++/Python SDK selections
  retained byte-for-byte during installation. Previous payload retained.
- Five public GitHub release assets have verified remote SHA-256 digests.

AI responses in workflow tests are explicit deterministic fixtures. Actual
Python/ConPTY and native WebView2 execute the tested runtime/UI behavior. No
provider intelligence or access to every paid account is certified by these tests.

Original branding SVG provenance is in `web/assets/providers/NOTICE.md`.
Account login uses official clients; API and local destinations have separate
connection types. Current client documentation:

- [Codex authentication](https://learn.chatgpt.com/docs/auth)
- [Claude Code authentication](https://code.claude.com/docs/en/authentication)
- [Gemini CLI authentication](https://geminicli.com/docs/get-started/authentication/)
- [Copilot CLI authentication](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/authenticate-copilot-cli)

Windows remains an unsigned public preview with partial VS Code APIs. Advanced
legacy messages still need complete localization. No new Linux/macOS certification.
