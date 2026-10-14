# R9 verification — 14 October 2026

R9 changes the frontend motion lifecycle and increments the release revision.
There are no new backend or provider behaviors.
Build source: `b9150d9`.

- 11 new browser lifecycle scenarios: entrance/dismissal, current-frame
  interruption, reopening, surface transfer, canvas pixels, confirmation results,
  focus restoration, Settings, rapid screen navigation, resize and reduced motion.
- Existing model/nC workflows: 8 groups; profile and actual file/session recovery:
  11 groups; existing R6 workflows: 12 groups. Total: 42 browser workflow groups.
- 109 Node tests and 64 frontend JavaScript syntax checks pass. Native package and installed application results are
  recorded in the machine-readable Windows R9 verification receipts.
- Source, binary and theme coverage from [R8](VERIFICATION_054_R8.md) remains
  historical evidence. R9 does not claim a new run of the entire Python/theme
  matrix.

AI responses in existing regression tests are declared deterministic fixtures.
They do not measure provider intelligence or account entitlement.
