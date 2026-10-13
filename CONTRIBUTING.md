# Contributing to Zénit

Help make coding, execution and AI assistance work better together. Focused
improvements and reproducible feedback are welcome during this public preview.

## Before starting

Check [open issues](https://github.com/Arizt00/Zenit/issues) and the [roadmap](docs/ROADMAP.md).
Discuss large changes in a feature issue before implementing them. Small fixes
can go straight to a pull request. Use English for issues, docs and PR descriptions.

## Run from source

Follow [README](README.md#develop-locally). Python hosts the backend and native
shell; JavaScript and Monaco form the frontend. Node powers extension engines.
Keep user data separate while testing:

```powershell
$env:ZENIT_DATA_DIR = Join-Path $PWD ".lumen/contributor-profile"
python app.py --desktop
```

Do not commit SDKs, model weights, credentials, user profiles, vendor/build outputs
or local runtime overrides. They are intentionally outside source control.

## Report a bug

Use the issue template. Include revision, OS, DPI scaling, reproduction steps,
expected behavior and actual behavior. For window bugs, identify the affected
window and terminal. Remove private code, paths and credentials from attachments.

## Make a change

Create a branch from `main`, make one coherent change, and describe the concrete
before/after behavior. Preserve shared-buffer conflict checks, provider consent
and file recovery. Use existing theme tokens and motion settings.

```powershell
python -m unittest discover -s tests -p "test_*.py"
npm run check
npm test
```

For UI changes, inspect light/dark/forest themes, compact windows, keyboard access
and reduced motion. Add meaningful behavioral regressions; minor visual changes
usually need screenshots rather than tests duplicating CSS. Visual tests use Edge
and Playwright:

```powershell
python tests/test_craft_r5_ui.py --output qa-output/craft
```

Disclose fixture AI responses. A transport test does not establish model quality.
Describe partial extension compatibility accurately.

## Licensing

Original contributions intentionally submitted for inclusion are offered under
Apache-2.0, as described in [LICENSE](LICENSE), unless explicitly stated otherwise.
Changes to the independent GPL ASM worker retain its license. Preserve copyright
and third-party notices; submit only material you have permission to contribute.

## Releases

Build on the target OS with `tools/build_desktop.py`. Release a tested payload,
installer/portable, manifest, checksums and clear notes. A preview must not be
renamed stable without supporting release checks. Windows checks do not certify
new Linux/macOS packages.
