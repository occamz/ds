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
    snapshot_list = snapshot.snapshot_list()
    return list(
        filter(
            lambda name: name.startswith(incomplete),
            map(lambda s: s.name, snapshot_list),
        )
    )


@click.group(cls=ClickAliasedGroup)
@click.option('--container-name')
@click.option('--directory')
@click.option('--namespace')
def snapshots(container_name, directory, namespace):
    if container_name or directory or namespace:
        s = settings.get_default_settings()
        if container_name:
            s.container_name = container_name
        if directory:
            s.directory = directory
        if namespace:
            s.namespace = namespace
        settings._data = s
    pass


@snapshots.command()
@container.requires_helper_container
def ls():
    snapshot_list = snapshot.snapshot_list()

    if not len(snapshot_list):
        click.echo("No snapshots found")
        return

    console = Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column("Created", style="dim")
    table.add_column("Name")
    table.add_column("Size", style="dim")
    table.add_column("UUID", style="dim")

    for s in snapshot_list:
        table.add_row(
            s.created_when.strftime("%Y-%m-%d %H:%M:%S"),
            f"[bold]{s.name}[/bold]",
            utils.sizeof_fmt(s.size),
            s.uuid,
        )

    console.print(table)


@snapshots.command()
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


@snapshots.command(aliases=["d", "rm"])
@click.argument("name", type=click.STRING, shell_complete=get_names)
@container.requires_helper_container
def delete(name):
    try:
        snapshot.snapshot_delete(name)
        click.echo(click.style(f"Deleted `{name}`", fg="red"))
    except Exception as e:
        error(e)


@snapshots.command()
@click.argument("name", default="", type=click.STRING, shell_complete=get_names)
@container.requires_helper_container
def restore(name):
    if not container.is_target_container_running():
        error(f"Target container `{settings.get('container_name')}` is not running.")
        return

    # Restore latest if no name is given
    if not name:
        snapshot_list = snapshot.snapshot_list()
        if len(snapshot_list):
            name = snapshot_list[-1].name
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


@snapshots.command()
def init():
    try:
        settings.init()
        click.echo(click.style("Created `ds.yaml`", fg="green"))
    except Exception as e:
        error(e)


def execute_cli():
    snapshots()

