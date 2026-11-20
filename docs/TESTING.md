# Testing

Run the full suite on Windows or another environment with Git installed:

```powershell
python -m compileall -q .
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest -q
```

Tests cover Git parsing and validation, models, services, batch isolation, CLI commands, report formats, rules, metrics, and GUI smoke behavior. Use focused commands such as `python -m pytest tests/test_cli.py -q` when iterating.

GUI tests use the offscreen Qt platform. Test deterministic data with `gui.mock_data`; test real analysis through temporary Git repositories.
