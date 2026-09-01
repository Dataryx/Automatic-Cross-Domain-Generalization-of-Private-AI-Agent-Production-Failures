"""HTML review queue for human authorization (Appendix C)."""

from __future__ import annotations

from cfi_governance.review import ReviewTicket

RELEASE_GATE_CHECKLIST: list[tuple[int, str]] = [
    (1, "Local immutable evidence preserved"),
    (2, "Expected outcome supported"),
    (3, "Counterfactual interventions safe and repeated"),
    (4, "Graph elements justified"),
    (5, "Exact identifiers removed"),
    (6, "Source inference assessed"),
    (7, "Reconstruction attack assessed"),
    (8, "No executable exploit / unpatched vuln disclosure"),
    (9, "Negative controls sufficient"),
    (10, "Legal/privacy/security/domain review"),
    (11, "Disclosure tier and expiration explicit"),
    (12, "Schema, compiler, digest, attestations, signature present"),
]


def ticket_to_dict(ticket: ReviewTicket) -> dict[str, object]:
    return {
        "invariant_id": ticket.invariant_id,
        "status": ticket.status.value,
        "adversary_scores": ticket.adversary_scores,
        "checklist_complete": ticket.checklist_complete,
        "reviewer": ticket.reviewer,
        "notes": ticket.notes,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "checklist": [{"id": i, "item": text} for i, text in RELEASE_GATE_CHECKLIST],
    }


def render_review_ui(pending: list[ReviewTicket]) -> str:
    rows = []
    for t in pending:
        scores = ", ".join(f"{k}={v:.2f}" for k, v in t.adversary_scores.items())
        checklist = "".join(f"<li>{i}. {text}</li>" for i, text in RELEASE_GATE_CHECKLIST)
        rows.append(
            f"""<tr>
<td><a href="/review/{t.invariant_id}">{t.invariant_id}</a></td>
<td>{scores}</td><td>{t.status.value}</td>
<td>
  <details><summary>Checklist</summary><ol>{checklist}</ol></details>
  <button onclick="decide('{t.invariant_id}','approved')">Approve</button>
  <button onclick="decide('{t.invariant_id}','rejected')">Reject</button>
  <button onclick="decide('{t.invariant_id}','needs_generalization')">Needs generalization</button>
</td></tr>"""
        )
    body_rows = "".join(rows) or '<tr><td colspan="4">No pending reviews</td></tr>'
    return f"""<!DOCTYPE html>
<html><head><title>CFI Review Queue</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 0.5rem; vertical-align: top; }}
details {{ margin-bottom: 0.5rem; }}
</style></head>
<body>
<h1>Pending CFI reviews</h1>
<p>Human authorization required before lifecycle promotion. Not a privacy proof.</p>
<p>Adversary scores are registration-time estimates only. Complete all 12 checklist items before approval.</p>
<table>
<tr><th>ID</th><th>Adversary scores</th><th>Status</th><th>Actions</th></tr>
{body_rows}
</table>
<script>
async function decide(id, status) {{
  const reviewer = prompt("Reviewer email:", "reviewer@org");
  if (!reviewer) return;
  const notes = prompt("Notes:", "");
  const checklist = confirm("Confirm all 12 release-gate checklist items are complete?");
  const resp = await fetch(`/review/${{id}}/decision`, {{
    method: "POST",
    headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify({{status, reviewer, notes, checklist_complete: checklist}})
  }});
  if (resp.ok) location.reload();
  else alert(await resp.text());
}}
</script>
</body></html>"""


def render_review_detail(ticket: ReviewTicket, lifecycle_state: str) -> str:
    scores = "".join(
        f"<li>{k}: {v:.3f}</li>" for k, v in ticket.adversary_scores.items()
    ) or "<li>No adversary scores recorded</li>"
    checklist = "".join(f"<li>{i}. {text}</li>" for i, text in RELEASE_GATE_CHECKLIST)
    return f"""<!DOCTYPE html>
<html><head><title>Review {ticket.invariant_id}</title></head>
<body>
<h1>Review ticket: {ticket.invariant_id}</h1>
<p><a href="/review/ui">← Back to queue</a> | <a href="/cfi/{ticket.invariant_id}/audit">Audit JSON</a></p>
<p>Lifecycle: <strong>{lifecycle_state}</strong> | Status: <strong>{ticket.status.value}</strong></p>
<h2>Adversary scores</h2>
<ul>{scores}</ul>
<h2>Release gate checklist</h2>
<ol>{checklist}</ol>
<p>Reviewer: {ticket.reviewer or "—"} | Notes: {ticket.notes or "—"}</p>
</body></html>"""
