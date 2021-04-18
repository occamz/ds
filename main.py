import click
import colorama
from click_aliases import ClickAliasedGroup
from terminaltables import AsciiTable

import snapshot
import settings
import utils

"""
- Store snapshots in a named volume
- Install rsync for showing progress
- Add configuration file
- Add "snapshots init" command to create template configuration file


Configuration parameters:
- container_name: 		postgres					kind-control-plane
- directory: 			/var/lib/postgresql/data	/mnt1/postgres-data
- snapshot_volume_name:	snapshots-postgres			snapshots-kind
"""


def error(message):
    click.echo(f"{colorama.Fore.RED}{message}", err=True)


def get_names(ctx, args, incomplete):
    snapshots = snapshot.snapshot_list()
    names = list(map(lambda s: (s.name, s.created_when), snapshots))
    return [name for name in names if name[0].startswith(incomplete)]


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


@cli.command(aliases=["c"])
@click.argument("name", default="")
def create(name):
    name = name if name else None
    s = snapshot.snapshot_create(name)
    click.echo(f"{colorama.Fore.GREEN}Created `{s.name}`")


@cli.command(aliases=["d"])
@click.argument("name", type=click.STRING, autocompletion=get_names)
def delete(name):
    try:
        snapshot.snapshot_delete(name)
        click.echo(f"{colorama.Fore.RED}Deleted `{name}`")
    except Exception as e:
        error(e)


@cli.command(aliases=["r"])
@click.argument("name", type=click.STRING, autocompletion=get_names)
def restore(name):
    try:
        snapshot.snapshot_restore(name)
        click.echo(f"{colorama.Fore.GREEN}Restored `{name}`")
    except Exception as e:
        error(e)


@cli.command()
def init():
    try:
        settings.init()
        click.echo(f"{colorama.Fore.GREEN}Created ds.yaml")
    except Exception as e:
        error(e)


if __name__ == "__main__":
    cli()
