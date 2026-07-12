"""Self-contained HTML report for a moderation result.

No external assets — inline CSS only — so the file opens anywhere and is safe to embed in the audit
bundle. Surfaces exactly what the trust story needs: the decision, the tensor decomposition (with
the collapsed family grouped, not shown as nine independent axes), the moral residue, per-dimension
validation provenance, and the verifiable proof hash.
"""

from __future__ import annotations

import html
import json

from gtc import DEME10
from gtc.decision import COLLAPSED_FAMILY, HARD_CHANNEL, INDEPENDENT, graded_validated
from gtc.pipeline import ModerationResult

_ACTION_COLOR = {"allow": "#2e7d32", "remove": "#c62828", "escalate": "#e65100"}


def _bar(value: float) -> str:
    """A tiny signed bar: green right for upheld (+), red left for violated (−)."""
    pct = min(100.0, abs(value) * 100.0)
    color = "#2e7d32" if value >= 0 else "#c62828"
    side = "left:50%" if value >= 0 else f"right:50%"
    return (
        f'<span style="display:inline-block;position:relative;width:120px;height:10px;'
        f'background:#eee;border-radius:5px;vertical-align:middle">'
        f'<span style="position:absolute;top:0;{side};width:{pct*0.5:.1f}%;height:10px;'
        f'background:{color};border-radius:5px"></span></span>'
    )


def render_html(result: ModerationResult) -> str:
    d = result.decision
    p = result.perception
    color = _ACTION_COLOR.get(d.action, "#555")
    verified = "✓ verified" if result.proof.verify() else "✗ TAMPERED"

    rows = []
    for dim in DEME10:
        sc = p.scores.get(dim)
        if sc is None:  # pre-10-axis cache: don't invent a row
            continue
        group = (
            "hard-constraint" if dim in HARD_CHANNEL
            else "shared-valence family" if dim in COLLAPSED_FAMILY
            else "independent axis"
        )
        badge = (
            '<span style="color:#1565c0">▣ hard rule</span>' if dim in HARD_CHANNEL
            else '<span style="color:#2e7d32">● validated</span>' if sc.validated
            else '<span style="color:#b71c1c">○ unvalidated</span>'
        )
        rows.append(
            f"<tr><td>{html.escape(dim)}</td><td style='color:#777'>{group}</td>"
            f"<td>{_bar(sc.value)} {sc.value:+.3f}</td>"
            f"<td>{sc.confidence:.2f}</td><td>{badge}</td></tr>"
        )

    residue = (
        "".join(
            f"<li><b>{html.escape(r['dimension'])}</b>: {r['value']:+.2f} "
            f"(conf {r['confidence']:.2f})</li>"
            for r in d.moral_residue
        )
        or "<li><i>none material</i></li>"
    )
    axes = "".join(
        f"<li>{html.escape(k)}: <b>{v:+.3f}</b></li>" for k, v in d.effective_axes.items()
    )

    warn = ""
    if not graded_validated(p):
        warn = (
            '<div style="background:#fff8e1;border:1px solid #ffb300;padding:8px 12px;'
            'border-radius:6px;margin:10px 0">⚠ Graded perception is <b>not</b> from validated '
            f'encoders ({html.escape(p.backend)} backend) — this decision is illustrative, not a '
            "validated judgment. Real runs use the validated xbse feeders (the `cached`/`atlas` "
            "backends).</div>"
        )

    return f"""<div style="font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:820px;
margin:24px auto;color:#222;line-height:1.5">
<h1 style="margin-bottom:4px">Geometric Ethics — Moderation Report</h1>
<div style="color:#777;font-size:14px">Trust as a measured structural property.</div>
{warn}
<div style="background:{color};color:#fff;padding:14px 18px;border-radius:8px;margin:14px 0">
  <div style="font-size:26px;font-weight:700;text-transform:uppercase">{html.escape(d.action)}</div>
  <div>{html.escape(d.rationale)}</div>
  <div style="opacity:.85;margin-top:6px;font-size:13px">
    satisfaction S = {d.satisfaction:+.3f} ·
    {'requires human review' if d.requires_human_review else 'no review required'}
    {('· veto: ' + html.escape(d.fired_channel)) if d.fired_channel else ''}
  </div>
</div>

<h3>Content</h3>
<blockquote style="border-left:3px solid #ccc;margin:0;padding:6px 14px;color:#444">
{html.escape(result.text)}</blockquote>

<h3>Tensor decomposition — DEME-10</h3>
<p style="font-size:13px;color:#777">The compiler's nine axes plus <b>identity_attack</b> — the 10th
axis the Spectrum Analyzer discovered and validated (cross-dataset AUROC 0.80). The four
<i>shared-valence family</i> dimensions are one effective axis, not four (see the effective-axis
contraction), so the rows are shown for provenance but are <b>not</b> ten independent measurements.</p>
<table style="border-collapse:collapse;width:100%;font-size:14px">
<tr style="text-align:left;color:#555"><th>dimension</th><th>group</th><th>valence</th>
<th>conf</th><th>feeder</th></tr>
{''.join(rows)}
</table>

<h3>Effective axes (contracted)</h3><ul>{axes}</ul>
<h3>Moral residue <span style="font-weight:400;color:#777;font-size:13px">— values considered but
discarded in the contraction</span></h3><ul>{residue}</ul>

<h3>Audit</h3>
<div style="font-family:ui-monospace,Consolas,monospace;font-size:12px;background:#f6f6f6;
padding:10px;border-radius:6px;word-break:break-all">
proof_hash: {result.proof.proof_hash}<br>prev_hash: {result.proof.prev_hash}<br>
status: <b>{verified}</b> · backend: {html.escape(p.backend)}
</div>
</div>"""


def result_to_json(result: ModerationResult) -> str:
    return json.dumps(
        {
            "summary": result.summary(),
            "decision": result.decision.as_dict(),
            "proof": result.proof.to_dict(),
        },
        indent=2,
        ensure_ascii=False,
    )
