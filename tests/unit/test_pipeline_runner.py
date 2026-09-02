"""Pipeline runner ZK attestation integration tests."""

from cfi_contributor.pipeline_runner import run_inprocess_full_pipeline


def test_inprocess_pipeline_includes_zk_attestation() -> None:
    summary = run_inprocess_full_pipeline(epoch="zk-test")
    assert summary["assessed"] is True
    assert summary.get("zk_attestation_verified") is True
