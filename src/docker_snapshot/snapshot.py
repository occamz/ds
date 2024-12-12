import dataclasses
import datetime
import itertools
import json
import typing as t
import uuid
import hruid  # type: ignore[import-untyped]
from docker_snapshot import container, settings


if t.TYPE_CHECKING:
    from typing_extensions import TypeGuard


@dataclasses.dataclass
class Snapshot:
    uuid: t.Optional[str] = None
    name: t.Optional[str] = None
    size: int = 0
    file_count: t.Optional[int] = 0
    created: int = 0

    def __post_init__(self) -> None:
        if not self.uuid:
            self.uuid = str(uuid.uuid4())
        if not self.created:
            self.created = int(datetime.datetime.now().timestamp())
        if not self.name:
            generator = hruid.Generator(use_number=False)
            self.name = generator.random()
        # NOTE: Soft "migration", will result in saved file_count
        # after first create / remove
        if not self.file_count:
            self.file_count = container.directory_filecount(self.path)

    @property
    def created_when(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.created)

    @property
    def path(self) -> str:
        return f"{container.HELPER_BASE_PATH}/{self.uuid}"


# Could be made lazy-loaded
def load_database() -> t.MutableSequence[Snapshot]:
    json_string = container.file_read("db.json")
    if not json_string:
        return []

    def _transform(data: object) -> Snapshot:
        if not isinstance(data, dict):
            raise RuntimeError("expected dict from json")
        return Snapshot(**data)

    return list(map(_transform, json.loads(json_string)))


def save_database(snapshot_list: t.Sequence[Snapshot]) -> None:
    json_string = json.dumps(list(map(dataclasses.asdict, snapshot_list)))
    container.file_write("db.json", json_string)


def snapshot_list() -> t.Sequence[Snapshot]:
    snapshots = load_database()
    return snapshots


def snapshot_create(name: str) -> Snapshot:
    snapshots = load_database()

    def _name_equals(snapshot: Snapshot) -> "TypeGuard[Snapshot]":
        return snapshot.name == name

    if any(filter(_name_equals, snapshots)):
        raise Exception("A snapshot with that name already exists")

    # Dummy file_count for the command to only run once
    snapshot = Snapshot(name=name, file_count=123)

    with container.freeze_target_container():
        container.sync(settings.get("directory"), snapshot.path)

    snapshot.size = container.directory_size(snapshot.path)
    snapshot.file_count = container.directory_filecount(snapshot.path)

    snapshots.append(snapshot)
    save_database(snapshots)
    return snapshot


def snapshot_delete(name: str) -> None:
    snapshots_before = load_database()

    def _name_equals(snapshot: Snapshot) -> "TypeGuard[Snapshot]":
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


def snapshot_restore(name: str) -> None:
    snapshots_before = load_database()

    def _name_equals(snapshot: Snapshot) -> "TypeGuard[Snapshot]":
        return snapshot.name == name

    existing_snapshots = tuple(filter(_name_equals, snapshots_before))
    if len(existing_snapshots) > 1:
        raise Exception("This shouldn't happen - 2 snapshots with the same name")

    if not existing_snapshots:
        raise Exception("No snapshot found")

    snapshot = existing_snapshots[0]

    with container.freeze_target_container():
        container.sync(snapshot.path, settings.get("directory"))


def snapshot_present_stats() -> Snapshot:
    path = settings.get("directory")
    return Snapshot(
        file_count=container.directory_filecount(path),
        size=container.directory_size(path),
    )
