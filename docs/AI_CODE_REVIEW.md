# AI code review

RepoScope can run an advisory review on pull requests with DeepSeek's OpenAI-compatible API. The workflow reviews the pull request diff and updates one PR comment marked with `reposcope-deepseek-review`.

## Configuration

Add a repository or organization Actions secret named `DEEPSEEK_API_KEY`. The workflow uses:

| Setting | Value |
| --- | --- |
| API base URL | `https://api.deepseek.com` |
| Model | `deepseek-flash` |
| Current model | DeepSeek-V4.1-Flash-1017 |

The old model names `deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` are not used by this workflow.

## Behavior and privacy

The workflow runs for opened, reopened, synchronized, and ready-for-review pull requests. Draft pull requests are skipped. It reads changed-file metadata and patches through the GitHub API, then sends that diff to DeepSeek. It does not check out or execute the pull request branch, and it does not upload the full repository, local caches, reports, or coverage files.

The review is advisory. It only creates or updates a PR comment; it does not approve, reject, modify, or commit code, and it does not block the existing CI checks. Fork pull requests do not receive repository secrets, so the AI review is skipped when `DEEPSEEK_API_KEY` is unavailable.

## Review focus

The prompt prioritizes functional regressions, security, Git and path handling, Qt thread/lifecycle behavior, CLI and report compatibility, missing tests, and documentation mismatches. It asks the model to report evidence-based findings with severity, file/line references, and concrete fixes while ignoring unrelated pre-existing issues and formatting preferences.

## Troubleshooting

- No comment: verify `DEEPSEEK_API_KEY` exists and the PR is not a draft.
- API error: check the DeepSeek account, key, quota, endpoint, and model availability.
- Repeated comments: confirm the marker is present and that the workflow has `pull-requests: write` permission.
- Incorrect finding: treat the comment as a suggestion and validate it against source code and the normal CI results.
