"""Backward-compatible re-exports for eval harness imports."""

from cfi_contributor.pipeline_runner import (
    cohort_manifest,
    run_inprocess_full_pipeline,
    run_remote_full_pipeline,
)

__all__ = ["cohort_manifest", "run_inprocess_full_pipeline", "run_remote_full_pipeline"]
