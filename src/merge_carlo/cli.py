"""Command-line entry point; real-data pipeline commands land with their milestones."""

from pathlib import Path
from typing import Annotated

import typer

from merge_carlo import __version__
from merge_carlo.artifacts import Evidence, write_experiment
from merge_carlo.demo import demo_experiment

app = typer.Typer(
    name="merge-carlo",
    help="Explore how AI pull-request demand interacts with human review capacity.",
    no_args_is_help=True,
)


def _print_version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit(code=0)


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_print_version, is_eager=True, help="Print the version and exit."),
    ] = False,
) -> None:
    """merge-carlo simulates pull-request review workflows offline."""


@app.command()
def demo(
    out: Annotated[Path, typer.Option(help="Directory for synthetic artifacts; must be empty or absent.")],
    seed: Annotated[int, typer.Option(min=0, help="Root random seed.")] = 42,
    replications: Annotated[int, typer.Option(min=1, help="Paired replications per scenario.")] = 200,
) -> None:
    """Run the SYNTHETIC offline demo without credentials or network access."""
    try:
        write_experiment(demo_experiment(seed, replications), Evidence(synthetic=True, training_cutoff=None), out)
    except (ValueError, OSError) as exc:
        typer.echo(f"Cannot write demo: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(f"SYNTHETIC demo: {out / 'report.md'}")
    typer.echo("Only the base assumption set was run. Full sensitivity has not been run.")
