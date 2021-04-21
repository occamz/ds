import click
from click_aliases import ClickAliasedGroup
from rich.console import Console
from rich.table import Table
from docker_snapshot import container, snapshot, settings, utils

"""
Configuration parameters:
- container_name: 		postgres					kind-control-plane
- directory: 			/var/lib/postgresql/data	/mnt1/postgres-data
- snapshot_volume_name:	snapshots-postgres			snapshots-kind
"""


def error(message):
    click.echo(click.style(str(message), fg="red"), err=True)


@container.requires_helper_container
def get_names(ctx, args, incomplete):
    snapshots = snapshot.snapshot_list()
    return list(
        filter(
            lambda name: name.startswith(incomplete),
            map(lambda s: s.name, snapshots),
        )
    )


@click.group(cls=ClickAliasedGroup)
def cli():
    pass


@cli.command()
@container.requires_helper_container
def ls():
    snapshots = snapshot.snapshot_list()

    if not len(snapshots):
        click.echo("No snapshots found")
        return

    console = Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column("Created", style="dim")
    table.add_column("Name")
    table.add_column("Size", style="dim")
    table.add_column("UUID", style="dim")

    for s in snapshots:
        table.add_row(
            s.created_when.strftime("%Y-%m-%d %H:%M:%S"),
            f"[bold]{s.name}[/bold]",
            utils.sizeof_fmt(s.size),
            s.uuid,
        )

    console.print(table)


@cli.command()
@click.argument("name", default="")
@container.requires_helper_container
def create(name):
    if not container.is_target_container_running():
        error(f"Target container `{settings.get('container_name')}` is not running.")
        return

    name = name if name else None
    try:
        s = snapshot.snapshot_create(name)
        click.echo(click.style(f"Created `{s.name}`", fg="green"))
    except Exception as e:
        error(e)


@cli.command(aliases=["d", "rm"])
@click.argument("name", type=click.STRING, autocompletion=get_names)
@container.requires_helper_container
def delete(name):
    try:
        snapshot.snapshot_delete(name)
        click.echo(click.style(f"Deleted `{name}`", fg="red"))
    except Exception as e:
        error(e)


@cli.command()
@click.argument("name", default="", type=click.STRING, autocompletion=get_names)
@container.requires_helper_container
def restore(name):
    if not container.is_target_container_running():
        error(f"Target container `{settings.get('container_name')}` is not running.")
        return

    # Restore latest if no name is given
    if not name:
        snapshots = snapshot.snapshot_list()
        if len(snapshots):
            name = snapshots[-1].name
            click.echo(
                click.style(
                    f"No snapshot name given, restoring latest snapshot `{name}`",
                    fg="green",
                )
            )
    else:
        click.echo(click.style(f"Restoring `{name}`", fg="green"))

    try:
        snapshot.snapshot_restore(name)
        click.echo(click.style(f"Restored `{name}`", fg="green"))
    except Exception as e:
        error(e)


@cli.command()
def init():
    try:
        settings.init()
        click.echo(click.style("Created `ds.yaml`", fg="green"))
    except Exception as e:
        error(e)


def execute_cli():
    cli()
