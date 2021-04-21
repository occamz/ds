import json
import uuid
import hruid
import datetime
import dataclasses
from docker_snapshot import container, settings


@dataclasses.dataclass
class Snapshot:
    uuid: str = None
    name: str = None
    size: int = 0
    created: int = 0

    def __post_init__(self):
        if not self.uuid:
            self.uuid = str(uuid.uuid4())
        if not self.created:
            self.created = int(datetime.datetime.now().timestamp())
        if not self.name:
            generator = hruid.Generator(use_number=False)
            self.name = generator.random()

    @property
    def created_when(self):
        return datetime.datetime.fromtimestamp(self.created)

    @property
    def path(self):
        return f"{container.HELPER_BASE_PATH}/{self.uuid}"


# Could be made lazy-loaded
def load_database():
    json_string = container.file_read("db.json")
    if not json_string:
        return []

    return list(
        map(lambda snapshot_data: Snapshot(**snapshot_data), json.loads(json_string))
    )


def save_database(snapshot_list):
    json_string = json.dumps(
        list(map(lambda snapshot: dataclasses.asdict(snapshot), snapshot_list))
    )
    container.file_write("db.json", json_string)


def snapshot_list():
    snapshots = load_database()
    return snapshots


def snapshot_create(name):
    snapshots = load_database()

    existing_snapshots = list(filter(lambda s: s.name == name, snapshots))
    if len(existing_snapshots) > 0:
        raise Exception("A snapshot with that name already exists")

    snapshot = Snapshot(name=name)

    with container.freeze_target_container():
        container.sync(settings.get("directory"), snapshot.path)

    snapshot.size = container.directory_size(snapshot.path)

    snapshots.append(snapshot)
    save_database(snapshots)
    return snapshot


def snapshot_delete(name):
    snapshots_before = load_database()

    existing_snapshots = list(filter(lambda s: s.name == name, snapshots_before))
    if len(existing_snapshots) > 1:
        raise Exception("This shouldn't happen - 2 snapshots with the same name")

    if len(existing_snapshots) < 1:
        raise Exception("No snapshot found")

    snapshot = existing_snapshots[0]

    snapshots_after = list(filter(lambda s: s.name != name, snapshots_before))

    container.directory_remove(snapshot.path)

    save_database(snapshots_after)


def snapshot_restore(name):
    snapshots_before = load_database()

    existing_snapshots = list(filter(lambda s: s.name == name, snapshots_before))
    if len(existing_snapshots) > 1:
        raise Exception("This shouldn't happen - 2 snapshots with the same name")

    if len(existing_snapshots) < 1:
        raise Exception("No snapshot found")

    snapshot = existing_snapshots[0]

    with container.freeze_target_container():
        container.sync(snapshot.path, settings.get("directory"))
