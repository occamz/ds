import click
from click_aliases import ClickAliasedGroup
from terminaltables import AsciiTable

import snapshot
import settings
import utils

"""
Configuration parameters:
- container_name: 		postgres					kind-control-plane
- directory: 			/var/lib/postgresql/data	/mnt1/postgres-data
- snapshot_volume_name:	snapshots-postgres			snapshots-kind
"""


def error(message):
    click.echo(click.style(str(message), fg="red"), err=True)


def get_names(ctx, args, incomplete):
    snapshots = snapshot.snapshot_list()
    return list(
        filter(
            lambda name: name.name.startswith(incomplete),
            map(lambda s: s.name, snapshots),
        )
    )


@click.group(cls=ClickAliasedGroup)
def cli():
    pass


@cli.command()
def ls():
    snapshots = snapshot.snapshot_list()

    if not len(snapshots):
        click.echo("No snapshots found")
        return

    table_data = [
        ["Created", "Name", "Size", "UUID"],
    ]
    table_data.extend(
        list(
            map(
                lambda s: [
                    s.created_when,
                    s.name,
                    utils.sizeof_fmt(s.size),
                    s.uuid,
                ],
                snapshots,
            )
        )
    )

    table = AsciiTable(table_data)
    click.echo(table.table)


@cli.command()
@click.argument("name", default="")
def create(name):
    name = name if name else None
    try:
        s = snapshot.snapshot_create(name)
        click.echo(click.style(f"Created `{s.name}`", fg="green"))
    except Exception as e:
        error(e)


@cli.command(aliases=["d", "rm"])
@click.argument("name", type=click.STRING, autocompletion=get_names)
def delete(name):
    try:
        snapshot.snapshot_delete(name)
        click.echo(click.style(f"Deleted `{name}`", fg="red"))
    except Exception as e:
        error(e)


@cli.command()
@click.argument("name", default="", type=click.STRING, autocompletion=get_names)
def restore(name):
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
        click.echo(click.style("Created ds.yaml", fg="green"))
    except Exception as e:
        error(e)


if __name__ == "__main__":
    cli()
