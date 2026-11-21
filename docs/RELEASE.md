# Release Checklist

- Confirm the intended branch and review the change set.
- Update user and developer documentation.
- Run compileall and the complete pytest suite.
- Verify GUI startup, demo mode, repository analysis, and report export.
- Regenerate screenshots when UI behavior changes.
- Check Markdown, HTML, and CSV output.
- Open and review the pull request and CI results.
- After merge, create and push a semantic version tag, for example `git tag v0.1.0 && git push origin v0.1.0`.
- Verify the tag workflow completes and the GitHub Release contains `RepoScope-v0.1.0.zip`.

The release workflow validates Ruff, `compileall`, and the complete pytest suite with a 60% coverage minimum before publishing the source archive.
