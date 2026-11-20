# Configuration

`AnalysisConfig` is the shared configuration object for GUI and CLI analysis. Values can be loaded from JSON and overridden by CLI flags.

Important thresholds are `stale_days`, `large_file_mb`, `single_maintainer_ratio`, `release_stale_days`, `hotspot_changes`, `min_message_length`, `max_function_lines`, `max_file_lines`, `min_test_ratio`, and `ownership_ratio`.

Optional scans are controlled by `enable_dependency_scan` and `enable_secret_scan`. `rule_levels` maps rule identifiers to `high`, `medium`, or `low`.

Example:

```json
{
  "observation_days": 90,
  "stale_days": 180,
  "large_file_mb": 10,
  "hotspot_changes": 10,
  "min_test_ratio": 0.05,
  "enable_secret_scan": true
}
```

Invalid ranges and invalid commit regular expressions fail early with a readable configuration error.
