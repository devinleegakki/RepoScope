# Troubleshooting

## GUI does not start

Check Python, PySide6, and the `main.py` working directory. Use `python main.py --demo` to separate GUI issues from Git repository issues.

## Repository is rejected

The path must be a directory containing `.git`, and Git must be available on `PATH`. Run `python main.py check PATH` for a readable diagnostic.

## GUI tests fail

Set `QT_QPA_PLATFORM=offscreen` before pytest. Ensure the same Python interpreter is used for dependency installation and test execution.

## Export appears inactive

The Reports page requires completed analysis. Select at least one format, choose an output directory, and check the status message for success, cancellation, or failure.

## CI dependency failure

Verify that `.github/workflows/ci.yml` installs `config/requirements-dev.txt`, which includes the root runtime requirements.
