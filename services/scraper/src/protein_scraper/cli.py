"""Command-line interface for the scraper."""

from __future__ import annotations

import asyncio
import importlib.resources
import logging

import typer
import yaml
from rich.console import Console
from rich.table import Table

from . import pipeline
from .config import get_settings
from .db import Repository, create_engine

app = typer.Typer(add_completion=False, help="Protein powder scraping pipeline.")
console = Console()


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _repo() -> Repository:
    return Repository(create_engine(get_settings().database_url))


@app.command()
def seed() -> None:
    """Insert/update the seed sources from the bundled seed_sources.yaml."""
    data = importlib.resources.files("protein_scraper").joinpath("seed_sources.yaml").read_text()
    config = yaml.safe_load(data)
    repo = _repo()
    count = 0
    for entry in config.get("sources", []):
        repo.upsert_source(
            slug=entry["slug"], name=entry["name"], type_=entry["type"],
            base_url=entry["base_url"], enabled=entry.get("enabled", True),
            config=entry.get("config"),
        )
        count += 1
    console.print(f"[green]Seeded {count} sources.[/green]")


@app.command("list-sources")
def list_sources() -> None:
    """Show enabled sources."""
    table = Table("slug", "name", "type", "base url")
    for s in _repo().list_enabled_sources():
        table.add_row(s["slug"], "", s["type"], s["baseUrl"])
    console.print(table)


@app.command()
def run(
    source: list[str] = typer.Option(None, "--source", "-s", help="Source slug(s) to run."),
    all_sources: bool = typer.Option(False, "--all", help="Run every enabled source."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run the scraping pipeline."""
    _setup_logging(verbose)
    if not source and not all_sources:
        raise typer.BadParameter("Pass --source <slug> (repeatable) or --all.")

    slugs = None if all_sources else list(source)
    stats = asyncio.run(pipeline.run(slugs))

    table = Table("metric", "count")
    table.add_row("sources", str(stats.sources))
    table.add_row("products", str(stats.products))
    table.add_row("variants", str(stats.variants))
    table.add_row("price observations", str(stats.prices))
    table.add_row("nutrition stored", str(stats.nutrition_ok))
    table.add_row("issues flagged", str(stats.issues))
    console.print(table)
    for err in stats.errors:
        console.print(f"[red]{err}[/red]")


if __name__ == "__main__":
    app()
