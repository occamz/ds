import dataclasses
import datetime
import itertools
import json
import typing as t
import uuid
import hruid  # type: ignore[import-untyped]
from docker_snapshot import container


def _generate_uuid() -> str:
    return str(uuid.uuid4())


def _generate_name() -> str:
    return hruid.Generator(use_number=False).random()  # type: ignore[no-any-return]


def _get_timestamp() -> int:
    return int(datetime.datetime.now().timestamp())


# TODO typing: pathlib
def _get_snapshot_path(suffix: str) -> str:
    return f"{container.HELPER_BASE_PATH}/{suffix}"


@dataclasses.dataclass
class Snapshot:
    uuid: str = dataclasses.field(default_factory=_generate_uuid)
    name: str = dataclasses.field(default_factory=_generate_name)
    size: int = dataclasses.field(default=0)
    file_count: int = dataclasses.field(default=0)
    created: int = dataclasses.field(default_factory=_get_timestamp)

    @property
    def created_when(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.created)

    @property
    def path(self) -> str:
        return _get_snapshot_path(suffix=self.uuid)


def _create_snapshot(**kwargs: object) -> Snapshot:
    _kwargs = {k: v for k, v in kwargs.items() if v}
    return Snapshot(**_kwargs)  # type: ignore[arg-type]


# Could be made lazy-loaded
def load_database() -> t.MutableSequence[Snapshot]:
    json_string = container.file_read("db.json")
    if not json_string:
        return []

    def _transform(data: object) -> Snapshot:
        if not isinstance(data, dict):
            raise RuntimeError("expected dict from json")
        return _create_snapshot(**data)

    return list(map(_transform, json.loads(json_string)))


def save_database(snapshot_list: t.Sequence[Snapshot]) -> None:
    json_string = json.dumps(list(map(dataclasses.asdict, snapshot_list)))
    container.file_write("db.json", json_string)


def snapshot_list() -> t.Sequence[Snapshot]:
    snapshots = load_database()
    return snapshots


def snapshot_create(
    name: t.Optional[str],
    source: str,
    container_name: str,
) -> Snapshot:
    snapshots = load_database()

    def _name_equals(snapshot: Snapshot) -> t.TypeGuard[Snapshot]:
        return snapshot.name == name

    if any(filter(_name_equals, snapshots)):
        raise Exception("A snapshot with that name already exists")

    _uuid = _generate_uuid()
    _path = _get_snapshot_path(suffix=_uuid)

    with container.freeze_target_container(name=container_name):
        container.sync(source_directory=source, destination_path=_path)

    _name = name or _generate_name()
    _size = container.directory_size(_path)
    _file_count = container.directory_filecount(_path)

    snapshot = Snapshot(
        uuid=_uuid,
        name=_name,
        size=_size,
        file_count=_file_count,
    )

    snapshots.append(snapshot)
    save_database(snapshots)
    return snapshot


def snapshot_delete(name: str) -> None:
    snapshots_before = load_database()

    def _name_equals(snapshot: Snapshot) -> t.TypeGuard[Snapshot]:
        return snapshot.name == name

    existing_snapshots = tuple(filter(_name_equals, snapshots_before))
    if len(existing_snapshots) > 1:
        raise Exception("This shouldn't happen - 2 snapshots with the same name")

    if not existing_snapshots:
        raise Exception("No snapshot found")

    snapshot = existing_snapshots[0]

    snapshots_after = tuple(itertools.filterfalse(_name_equals, snapshots_before))

    container.directory_remove(snapshot.path)

    save_database(snapshots_after)


def snapshot_restore(name: str, destination: str, container_name: str) -> None:
    snapshots_before = load_database()

    def _name_equals(snapshot: Snapshot) -> t.TypeGuard[Snapshot]:
        return snapshot.name == name

    existing_snapshots = tuple(filter(_name_equals, snapshots_before))
    if len(existing_snapshots) > 1:
        raise Exception("This shouldn't happen - 2 snapshots with the same name")

    if not existing_snapshots:
        raise Exception("No snapshot found")

    snapshot = existing_snapshots[0]

    with container.freeze_target_container(name=container_name):
        container.sync(source_directory=snapshot.path, destination_path=destination)


def snapshot_present_stats(path: str) -> Snapshot:
    return Snapshot(
        file_count=container.directory_filecount(path=path),
        size=container.directory_size(path=path),
    )
