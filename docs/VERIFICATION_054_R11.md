# R11 verification — 14 October 2026

- Python: 341 tests run, 336 passed and 5 platform skips.
- Node: 113 tests passed, including bounded output comparison and revision evidence.
- Frontend JavaScript syntax: 67 files passed.
- Browser workflows: 12 motion lifecycle groups, 7 new Melody/Lantern groups,
  8 existing model/nC groups, 11 profile/session groups and 12 existing workflow
  groups. Total: 50 groups.
- New execution checks use actual Python processes and unsaved buffers. They
  verify pin/follow behavior, actual output comparisons, read-only consultation
  and inline model selection without opening Settings.
- Motion checks include current-frame interruption, isolated dismissal, preserved
  canvas/scroll/control state, reduced motion, GPU pause behind overlays and
  bounded panel travel without clipping.

Package, installed application and publication receipts are recorded separately
in `tests/visual/evidence/windows-054-r11-*.json`. The installed verifier reports
whether the decorative canvas was running or paused when its window was covered;
paused background rendering is expected behavior.

AI tests use declared deterministic responses and catalogs. They do not certify
provider intelligence or account entitlement. Theme coverage from R8 is retained
as historical evidence; no new full theme matrix is claimed by this revision.
