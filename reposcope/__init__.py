"""RepoScope analysis core: statistical metrics and anti-pattern rules.

Owner: TYB (task 2). GUI-independent; consumes LTY's RepositorySnapshot.

Typical integration (from the application service layer)::

    from reposcope.metrics import compute_metrics
    from reposcope.rules import detect_all
    from reposcope.models_analysis import AnalysisConfig

    config = AnalysisConfig.from_yaml("default_rules.yaml")
    metrics = compute_metrics(snapshot, config, as_of=now)
    warnings = detect_all(metrics, config)
    # feed metrics.to_dict() and [w.to_dict() for w in warnings] to GUI/reports
"""

from .models_analysis import (
    AnalysisConfig,
    AuthorContribution,
    CommitCompliance,
    FileStat,
    RepositoryMetrics,
    Warning,
)
from .metrics import compute_metrics
from .rules import detect_all

__all__ = [
    "AnalysisConfig",
    "AuthorContribution",
    "CommitCompliance",
    "FileStat",
    "RepositoryMetrics",
    "Warning",
    "compute_metrics",
    "detect_all",
]
