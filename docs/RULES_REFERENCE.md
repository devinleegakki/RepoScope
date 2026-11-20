# Rules Reference

`reposcope.rules.detect_all()` evaluates every rule and returns warnings ordered by severity.

| Rule | Trigger |
|---|---|
| Single-maintainer risk | One author exceeds the configured recent commit share. |
| Activity-without-release illusion | Recent activity exists but the latest tag is stale. |
| High-frequency change hotspot | A file exceeds the change threshold. |
| Large / binary file risk | Large or configured binary files are present. |
| Zombie file | Files exceed the stale age threshold. |
| Non-standard commit message | Commit messages fail the configured pattern or length. |
| Code quality issues | Long functions/files or bare exception handlers are found. |
| Single-owner file risk | Files are dominated by one author. |
| Dependency hygiene risk | Dependencies are unpinned, duplicated, or lack a lock file. |
| Potential secret detected | Credential-like values or private keys are found. |
| Dangerous code pattern | Unsafe calls such as `shell=True`, `eval`, or `os.system` are found. |
| Insufficient test coverage | The test-file ratio is below the configured minimum. |

Each warning carries a name, severity, message, target, actual value, threshold, suggestion, and evidence fields.
