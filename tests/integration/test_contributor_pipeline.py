"""Pipeline and replay provider tests."""

from cfi_contributor.pipeline import ContributorPipeline
from cfi_contributor.replay import StructuralReplayProvider
from cfi_core.signing import KeyPair
from cfi_core.wire import Incident, MinimizationConfig, TypedTrace, TraceEvent
from cfi_core.models import EventType


def test_contributor_pipeline_produces_signed_cfi() -> None:
    key = KeyPair.generate("pipeline-test")
    pipeline = ContributorPipeline(key, replay=StructuralReplayProvider(), seed=42)
    incident = Incident(
        incident_id="local-inc-1",
        initiating_request_digest="abc",
        trace=TypedTrace(
            events=[
                TraceEvent(event_type=EventType.POLICY_LOOKUP, actor="agent", sequence_index=0),
                TraceEvent(event_type=EventType.ACTION, actor="agent", sequence_index=1),
            ]
        ),
        policy_digest="policy-digest",
        initial_state_digest="s0",
        terminal_state_digest="s1",
        expected_outcome="no_refund",
        observed_outcome="refund_issued",
        severity=0.8,
        evidence_store_ref="local://evidence/1",
    )
    raw = {
        "events": [
            {"type": "policy_lookup", "actor": "agent", "index": 0},
            {"type": "action", "actor": "agent", "index": 1},
        ]
    }
    minimization = MinimizationConfig(
        eta=0.9,
        delta=0.05,
        lambda_nodes=1.0,
        lambda_edges=1.0,
        lambda_literals=1.0,
        lambda_replay=1.0,
    )
    report = pipeline.extract_from_incident(
        incident, raw, minimization, checklist_answers={i: True for i in range(1, 13)}
    )
    assert report.candidates
    assert report.minimization is not None
    assert report.package is not None
    assert report.package.success
    assert report.package.cfi is not None
    assert report.package.cfi.signature is not None
