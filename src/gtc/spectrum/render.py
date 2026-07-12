"""Render the moral spectrogram. HTML is dependency-free (shopfront-ready); PNG needs matplotlib."""

from __future__ import annotations

import html
from pathlib import Path

import numpy as np


def _auroc_color(a: float) -> str:
    """Diverging color centered at 0.5: blue = anti-correlated, grey = none, red = strong signal."""
    d = max(-0.5, min(0.5, a - 0.5))
    if d >= 0:  # signal (red)
        t = d / 0.5
        r, g, b = 198, int(198 * (1 - t)) + 30, int(198 * (1 - t)) + 30
    else:  # anti-correlated (blue)
        t = -d / 0.5
        r, g, b = int(198 * (1 - t)) + 30, int(198 * (1 - t)) + 30, 198
    return f"rgb({r},{g},{b})"


def spectrogram_html(feeders, labels, M: np.ndarray, band2: dict, band3: dict) -> str:
    """A self-contained moral spectrogram: Band-1 heatmap + effective rank + missing-dimension bars."""
    # Band 1 heatmap
    head = "".join(f"<th style='font-size:11px;transform:rotate(-30deg);height:70px'>{html.escape(l)}</th>"
                   for l in labels)
    rows = []
    for i, f in enumerate(feeders):
        cells = "".join(
            f"<td title='{M[i,j]:.3f}' style='background:{_auroc_color(float(M[i,j]))};"
            f"width:46px;height:24px;text-align:center;font-size:10px;color:#222'>{M[i,j]:.2f}</td>"
            for j in range(len(labels))
        )
        rows.append(f"<tr><td style='font-size:12px;padding-right:8px;white-space:nowrap'>"
                    f"{html.escape(f)}</td>{cells}</tr>")
    heat = (f"<table style='border-collapse:collapse'><tr><th></th>{head}</tr>{''.join(rows)}</table>")

    # Band 2 effective rank
    er = band2.get("effective_rank_participation", "?")
    nd = band2.get("n_dims", "?")
    ev = band2.get("explained_ratio", [])
    bars = "".join(
        f"<span style='display:inline-block;width:20px;height:{max(2,int(r*120))}px;"
        f"background:#1565c0;margin:0 2px;vertical-align:bottom' title='{r:.3f}'></span>"
        for r in ev
    )
    band2_html = (f"<h3>Band 2 — eigen-spectrum</h3>"
                  f"<div style='height:130px'>{bars}</div>"
                  f"<div style='color:#555'>effective rank (participation) ≈ <b>{er}</b> of {nd} — "
                  f"the moral space is lower-rank than its nine named axes.</div>")

    # Band 3 discovery
    cand = band3.get("missing_dimension_candidates", []) if isinstance(band3, dict) else []
    per = band3.get("per_category", []) if isinstance(band3, dict) else []
    b3rows = "".join(
        f"<tr><td>{html.escape(r['category'])}</td><td>{r['auroc_feeders']}</td>"
        f"<td>{r['auroc_embedding']}</td>"
        f"<td style='font-weight:700;color:{'#c62828' if (r['gap'] or 0)>0.08 else '#555'}'>"
        f"{r['gap']}</td></tr>"
        for r in per
    )
    cand_names = ", ".join(html.escape(c["category"]) for c in cand[:4]) or "—"
    band3_html = (
        f"<h3>Band 3 — residual / discovery</h3>"
        f"<table style='border-collapse:collapse;font-size:13px'>"
        f"<tr style='text-align:left'><th>category</th><th>AUROC (9 feeders)</th>"
        f"<th>AUROC (embedding)</th><th>gap</th></tr>{b3rows}</table>"
        f"<div style='margin-top:8px'>Candidate <b>missing dimensions</b> (embedding predicts them, "
        f"the nine axes don't; each has an independent native label → admission-filter clean): "
        f"<b>{cand_names}</b></div>"
    )

    return f"""<div style="font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:900px;
margin:20px auto;color:#222">
<h1 style="margin-bottom:2px">Moral Spectrum Analyzer</h1>
<div style="color:#777;font-size:14px">Energy per moral axis across moderation categories —
red = signal, blue = anti-correlated, grey = noise floor.</div>
<h3>Band 1 — named-dimension spectrum (per-feeder AUROC)</h3>
<div style="overflow-x:auto">{heat}</div>
{band2_html}
{band3_html}
</div>"""


def spectrogram_png(feeders, labels, M: np.ndarray, path: str | Path) -> bool:
    """Optional matplotlib heatmap. Returns False if matplotlib is unavailable."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # noqa: BLE001
        return False
    fig, ax = plt.subplots(figsize=(1.1 * len(labels) + 3, 0.5 * len(feeders) + 2))
    im = ax.imshow(M, cmap="RdBu_r", vmin=0.2, vmax=0.8, aspect="auto")
    ax.set_xticks(range(len(labels)), labels, rotation=40, ha="right", fontsize=9)
    ax.set_yticks(range(len(feeders)), feeders, fontsize=9)
    for i in range(len(feeders)):
        for j in range(len(labels)):
            ax.text(j, i, f"{M[i,j]:.2f}", ha="center", va="center", fontsize=7, color="#222")
    ax.set_title("Moral spectrum — per-feeder AUROC vs moderation category")
    fig.colorbar(im, ax=ax, label="AUROC")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return True
