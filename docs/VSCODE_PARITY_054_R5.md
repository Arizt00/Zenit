# Verified workflows — Zénit 0.5.4 R5

This is a workflow comparison, not a claim of full extension API compatibility.

| Workflow | Verified behavior | Remaining boundary |
| --- | --- | --- |
| Native editor | Full window, terminal below, run/toggle/detach/return | Window layouts are intentionally different; concurrent document conflicts need resolution. |
| Terminal | Main/exterior/Forge share interactive ConPTY views | Complete VS Code shell integration remains pending. |
| Forge | Configured runtime, actual Python/Java execution, repeat/stop/exit status | Toolchains must be available; history is local to a Forge window. |
| Melody | Visible provider/model, scoped questions, live edits, selection review and undo | Tests use declared fixture responses; they do not establish model intelligence. |
| File plans | Real create/update/delete, recovery, revisions and undo | Session access boundaries remain; provider must be configured. |
| Search | Matching lines, case/words/globs, file groups, exact locations | Literal search, 200 visible results; regex/bulk replacement pending. |
| Appearance | Three palettes, Material icons, profile/activity, reduced motion | Product icon themes and advanced legacy localization remain incomplete. |
| Extension host | Declarative contributions and supported authorized Node APIs | OAuth, complete configuration scope and binary custom documents remain incomplete. |

See [STATUS](STATUS.md), [ROADMAP](ROADMAP.md), and the R4 comparison for historical
details. Existing Emma voice integration is retained; no new voice model is trained.
