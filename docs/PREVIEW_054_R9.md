# Zénit 0.5.4 R9 — Continuous opening and dismissal

R9 refines the complete motion lifecycle for Activity, the IDE profile, dialogs,
Settings and navigation between the welcome scene and the editor.

- Activity and profile expand from their actual avatar after their final content
  layout is measured. Text keeps its natural scale.
- Closing follows a 340 ms return to the avatar with a distinct exit curve,
  staged content fade and coordinated backdrop. Standard dialogs and Settings
  use a shorter surface dismissal.
- Closing halfway through an entrance starts from the currently rendered frame.
  Reopening during dismissal continues from the visible shape. Changing dialogs
  transfers the surface instead of replaying the avatar entrance.
- Confirmation results and dialog removal remain synchronous. The visual exit
  uses an inert snapshot in an isolated shadow tree, including actual canvas
  pixels; copied forms and IDs cannot interfere with live application selectors.
- The home scene holds its actual parallax position through opening and closing.
  It resumes after the last overlay disappears, without resetting underneath it.
- Entering the IDE expands the new screen. Returning home contracts the outgoing
  screen. Rapid alternating navigation honors the last requested destination.
- Keyboard focus returns after dismissal without stealing focus from a newly
  selected editor control. Resize and reduced motion safely settle active
  effects and remove temporary layers.

The new browser regression covers eleven lifecycle scenarios, including real
confirmation results, canvas preservation, focus, rapid navigation and reduced
motion. Profile/session, existing workflows and packaged native checks are also
recorded in the R9 verification receipts. This remains an unsigned Windows preview.
