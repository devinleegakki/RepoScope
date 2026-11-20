# CI/CD

GitHub Actions runs on pull requests and pushes to `main` using Windows with Python 3.11 and 3.12. It installs `config/requirements-dev.txt`, compiles Python sources, and runs pytest with `QT_QPA_PLATFORM=offscreen`.

A dependency installation failure usually means a requirements path changed without updating the workflow. GUI failures generally indicate missing offscreen configuration or an unhandled widget lifecycle issue. Reproduce CI locally with the commands in `docs/TESTING.md`.
