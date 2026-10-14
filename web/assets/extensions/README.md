# Factory extension

`nc-language-1.0.0-21v.vsix` is the unchanged release package from
`tools/vscode/nc-language/dist/` in [Arizt00/ncc](https://github.com/Arizt00/ncc).
Its identity is `nc-lang.nc-language`. MIT OR Apache-2.0 terms are inside the VSIX.

The factory catalog pins the package SHA-256. Zénit installs it on first launch
without replacing an existing version or enabling its Node engine implicitly.
An installation marker respects later removal. Existing icon preferences and
automatic selection of other language icon themes are preserved. This package's
icon theme is available for explicit selection only.

Grammar, snippets, language associations and declarative resources are available
through the existing contribution loader. Executable tasks and language tools
remain subject to Zénit's actual VS Code API support and workspace authorization.
