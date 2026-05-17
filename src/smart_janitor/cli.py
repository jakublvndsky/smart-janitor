import typer

app = typer.Typer(help="Tidy up messy folders based on declarative YAML rules.")


@app.command()
def hello() -> None:
    """Sanity check command. Will be replaced with real commands later."""
    typer.echo("Smart Janitor is alive.")


if __name__ == "__main__":
    app()
