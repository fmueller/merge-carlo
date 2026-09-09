"""Command-line entry point.

The v0.1.0 command contract is documented in `specs/v0.1.0.md`. Only `--version`
is implemented so far; the pipeline commands land with their milestones rather
than as success-shaped stubs.
"""

from typing import Annotated

import typer

from merge_carlo import __version__

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
