# CI/CD

GitHub Actions runs on pull requests and pushes to `main` using Windows with Python 3.11 and 3.12. Each job installs `config/requirements-dev.txt`, runs Ruff, compiles Python sources, and runs pytest with `QT_QPA_PLATFORM=offscreen`. Coverage is measured with `pytest-cov` and must be at least 60%; the XML report is uploaded as a workflow artifact.

The release workflow runs when a `vX.Y.Z` tag is pushed. It repeats the quality, compilation, test, and coverage checks, creates `RepoScope-vX.Y.Z.zip` with the tag contents, and attaches the source archive to a GitHub Release.

Reproduce the checks locally with the commands in `docs/TESTING.md`. A dependency installation failure usually means a requirements path changed without updating the workflow. GUI failures generally indicate missing offscreen configuration or an unhandled widget lifecycle issue.
