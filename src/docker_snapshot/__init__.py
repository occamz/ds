import typing as t
import click
from click_aliases import ClickAliasedGroup
from rich.console import Console
from rich.table import Table
from docker_snapshot import container, settings, snapshot, utils


if t.TYPE_CHECKING:
    from typing_extensions import TypeGuard


"""
Configuration parameters:
- container_name: 		postgres					kind-control-plane
- directory: 			/var/lib/postgresql/data	/mnt1/postgres-data
- snapshot_volume_name:	snapshots-postgres			snapshots-kind
"""


def error(message: t.Union[str, BaseException]) -> None:
    click.echo(click.style(str(message), fg="red"), err=True)


@container.requires_helper_container
def get_names(
    ctx: object,
    args: object,
    incomplete: t.Union[str, t.Tuple[str, ...]],
) -> t.Sequence[str]:
    def _get_name(snapshot: snapshot.Snapshot) -> str:
        return snapshot.name

    def _predicate(name: str) -> "TypeGuard[str]":
        return name.startswith(incomplete)

    snapshots = snapshot.snapshot_list()
    return list(filter(_predicate, map(_get_name, snapshots)))


@click.group(cls=ClickAliasedGroup)
@click.version_option()
@click.option("--container-name")
@click.option("--directory")
@click.option("--namespace")
def snapshots(container_name: str, directory: str, namespace: str) -> None:
    if container_name or directory or namespace:
        s = settings.get_default_settings()
        if container_name:
            s.container_name = container_name
        if directory:
            s.directory = directory
        if namespace:
            s.namespace = namespace
        settings._data = s


@snapshots.command
@container.requires_helper_container
def ls() -> None:
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
    table.add_column("File count", style="dim", justify="right")

    for s in snapshot_list:
        table.add_row(
            s.created_when.strftime("%Y-%m-%d %H:%M:%S"),
            f"[bold]{s.name}[/bold]",
            utils.sizeof_fmt(s.size),
            s.uuid,
            str(s.file_count),
        )

    # Show the present stats
    present = snapshot.snapshot_present_stats()
    table.add_row(
        "present",
        "",
        utils.sizeof_fmt(present.size),
        "",
        str(present.file_count),
        style="green",
    )

    console.print(table)


@snapshots.command
@click.argument("name", default="")
@container.requires_helper_container
def create(name: str) -> None:
    if not container.is_target_container_running():
        error(f"Target container `{settings.get('container_name')}` is not running.")
        return

    _name = name if name else None
    try:
        s = snapshot.snapshot_create(_name)
        click.echo(click.style(f"Created `{s.name}`", fg="green"))
    except Exception as e:
        error(e)


# NOTE: somehow mypy sees this as untyped :shrug:
@snapshots.command(aliases=["d", "rm"])  # type: ignore[misc]
@click.argument("name", type=click.STRING, shell_complete=get_names)
@container.requires_helper_container
def delete(name: str) -> None:
    try:
        snapshot.snapshot_delete(name)
        click.echo(click.style(f"Deleted `{name}`", fg="red"))
    except Exception as e:
        error(e)


@snapshots.command
@click.argument("name", default="", type=click.STRING, shell_complete=get_names)
@container.requires_helper_container
def restore(name: str) -> None:
    if not container.is_target_container_running():
        error(f"Target container `{settings.get('container_name')}` is not running.")
        return

    # Restore latest if no name is given
    if not name:
        if snapshots := snapshot.snapshot_list():
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


@snapshots.command
def init() -> None:
    try:
        settings.init()
        click.echo(click.style("Created `ds.yaml`", fg="green"))
    except Exception as e:
        error(e)


def execute_cli() -> None:
    snapshots()
