"""msa command-line interface. Grows one subcommand per phase; today: perceive (stub-backed)."""

from __future__ import annotations

import json
from pathlib import Path

import click

from moral_spectrum import DEME10, __version__
from moral_spectrum.perception import get_backend


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__)
def cli() -> None:
    """Geometric Ethics for Trustworthy AI — GTC prototype."""


@cli.command("perceive")
@click.argument("text", type=str)
@click.option("--backend", type=click.Choice(["stub", "cached", "atlas"]), default="stub")
def cmd_perceive(text: str, backend: str) -> None:
    """Score TEXT across the DEME-10 moral dimensions with the chosen perception backend."""
    result = get_backend(backend).perceive(text)
    click.echo(f"[backend] {result.backend}  validated={result.all_validated()}")
    for dim in DEME10:
        if dim not in result.scores:
            continue
        s = result.scores[dim]
        click.echo(f"  {dim:24s} {s.value:+.3f}  conf={s.confidence:.2f}  {s.direction}")
    if result.meta.get("warning"):
        click.echo(f"[!] {result.meta['warning']}")


@cli.command("moderate")
@click.argument("text", type=str)
@click.option("--backend", type=click.Choice(["stub", "cached", "atlas"]), default="stub")
@click.option(
    "--hard-flag",
    "hard_flags",
    multiple=True,
    help="Hand-specified categorical hard-constraint veto(s), e.g. 'dosage_cap_exceeded'. Repeatable.",
)
@click.option(
    "--out",
    "out_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Write report.html + result.json here. Default: out/",
)
def cmd_moderate(
    text: str, backend: str, hard_flags: tuple[str, ...], out_dir: Path | None
) -> None:
    """Run TEXT through the end-to-end moderation spine."""
    from moral_spectrum.pipeline import moderate
    from moral_spectrum.report import render_html, result_to_json

    result = moderate(text, backend=backend, hard_flags=list(hard_flags))
    s = result.summary()
    click.echo(
        f"[decision] {s['action'].upper()}  S={s['satisfaction']:+.3f}  "
        f"review={s['requires_human_review']}  validated={s['all_validated']}"
    )
    click.echo(f"[tensor]   principal={s['principal_dimension']}")
    if result.decision.moral_residue:
        click.echo(f"[residue]  {', '.join(r['dimension'] for r in result.decision.moral_residue)}")
    click.echo(f"[audit]    proof={s['proof_hash'][:16]}…  verify={result.proof.verify()}")

    out = out_dir or (Path("out"))
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.html").write_text(render_html(result), encoding="utf-8")
    (out / "result.json").write_text(result_to_json(result), encoding="utf-8")
    click.echo(f"[wrote]    {out / 'report.html'}  {out / 'result.json'}")


@cli.command("version")
def cmd_version() -> None:
    """Print the prototype version."""
    click.echo(json.dumps({"moral-spectrum-analyzer": __version__}))


if __name__ == "__main__":
    cli()
