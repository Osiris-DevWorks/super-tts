# Test Plan

The tester checklist for the release in progress. Amr runs it from the active `release/X.Y.Z` (`poetry run python gui_main.py`, or an installer from `scripts\build\build_all.bat`) before the release PR into `main` merges, since merging deploys the server bot to Railway.

- Each feature pushed to the release branch adds its own section below, titled `### #issue: short name`, with concrete items a tester can mark pass or fail. Say which track each item is for (server, desktop or both).
- `/release` copies the sections into the release PR body.
- `/start_release` clears them when the next release branch opens.

## Next release

_No features yet._
