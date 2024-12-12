import importlib.resources as pkg_resources
import io
import re
import shlex
import typing as t
from functools import wraps
import click
import docker
from docker import errors
from rich.progress import Progress
from docker_snapshot import images, settings


if t.TYPE_CHECKING:
    from types import TracebackType
    from docker.client import DockerClient
    from docker.models.containers import Container
    from docker.models.images import Image
    from docker.models.volumes import Volume
    from typing_extensions import ParamSpec

    P = ParamSpec("P")
    R = t.TypeVar("R")


HELPER_BASE_PATH = "/mnt/ds"

client: "DockerClient" = docker.from_env()
container: t.Optional["Container"] = None


def requires_helper_container(f: t.Callable["P", "R"]) -> t.Callable["P", "R"]:
    @wraps(f)
    def wrapper(*args: "P.args", **kwargs: "P.kwargs") -> "R":
        alloc()
        res = f(*args, **kwargs)
        dealloc()
        return res

    return wrapper


class freeze_target_container(object):
    def __init__(self) -> None:
        pass

    def __enter__(self) -> None:
        stop(settings.get("container_name"))

    def __exit__(
        self,
        exception_type: t.Optional[t.Type[BaseException]],
        exception: t.Optional[BaseException],
        traceback: t.Optional["TracebackType"],
    ) -> None:
        start(settings.get("container_name"))


def is_target_container_running() -> bool:
    return is_running(settings.get("container_name"))


def get_image_id() -> str:
    namespace = settings.get("namespace")
    return f"ds-{namespace}"


def get_volume_id() -> str:
    namespace = settings.get("namespace")
    return f"ds-{namespace}"


def get_container_id() -> str:
    namespace = settings.get("namespace")
    return f"ds-{namespace}"


def build_image() -> "Image":
    dockerfile = io.BytesIO(pkg_resources.read_text(images, "rsync").encode("utf-8"))
    image, _ = client.images.build(fileobj=dockerfile, tag=get_image_id())
    return image


def create_volume() -> "Volume":
    return client.volumes.create(name=get_volume_id())


def create_container(
    image: t.Union[str, "Image"],
    volume: "Volume",
    volumes_from: t.Optional[t.Sequence[str]],
) -> "Container":
    return client.containers.create(
        image,
        name=get_container_id(),
        volumes={volume.name: {"bind": HELPER_BASE_PATH, "mode": "rw"}},
        volumes_from=volumes_from,
        working_dir=HELPER_BASE_PATH,
        tty=True,
        stdin_open=True,
        auto_remove=False,
    )


def alloc() -> None:
    global container
    # Get or build image
    try:
        # NOTE: Blocks future versions of Dockerfile
        image = client.images.get(get_image_id())
    except errors.ImageNotFound:
        image = build_image()

    # Get or create volume
    try:
        volume = client.volumes.get(get_volume_id())
    except errors.NotFound:
        volume = create_volume()

    # Get and/or run container
    try:
        container = client.containers.get(get_container_id())
    except errors.NotFound:
        target_container_name = settings.get("container_name")
        if not exists(target_container_name):
            raise Exception(
                f"Target container with name {target_container_name} not found."
            )
        container = create_container(image, volume, target_container_name)

    container.start()


def dealloc() -> None:
    global container

    if container is None:
        return

    container.stop(timeout=0)


def sh(command: str) -> str:
    global container

    # TODO typing: fix
    if container is None:
        raise RuntimeError("container global not set")

    result = container.exec_run(["sh", "-c", command])
    output = t.cast(bytes, result.output)
    return output.decode("utf-8")


# TODO: pathlib
def file_read(path: str) -> str:
    return sh(f"cat {path} 2>/dev/null")


# TODO: pathlib
def file_write(path: str, content: str) -> str:
    return sh(f"echo {shlex.quote(content)} > {path}")


# TODO: pathlib
def directory_remove(path: str) -> str:
    return sh(f"rm -rf {path}")


# TODO: pathlib
def directory_size(path: str) -> int:
    # TODO: Replace with regex
    size = int(sh(f"du -s {path}").split("\t")[0]) * 1024
    return size


# TODO: pathlib
def directory_filecount(path: str) -> t.Optional[int]:
    try:
        return int(sh(f"find {path} -type f | wc -l"))
    except ValueError:
        return None


# TODO: pathlib
def sync(source_directory: str, destination_path: str) -> None:
    global container

    # TODO typing: fix
    if container is None:
        raise RuntimeError("container global not set")

    response = container.exec_run(
        [
            "sh",
            "-c",
            # TODO: this could probably be split on every whitespace character
            (
                "rsync -aAHX --delete --info=progress2 "
                f"{source_directory}/ {destination_path}"
            ),
        ],
        stream=True,
        stdout=True,
        stderr=True,
    )

    current_percentage = 0
    with Progress() as progress:
        task = progress.add_task("Copying files...", total=100)
        for out in response.output:
            percentage_string = re.search(r"\d+%", out.decode("utf-8"))
            if not percentage_string:
                continue

            try:
                percentage = int(percentage_string.group()[:-1])
                if current_percentage >= percentage:
                    continue
            except Exception:
                pass

            progress.update(task, advance=percentage - current_percentage)
            current_percentage = percentage
        progress.update(task, completed=100)


def stop(container_name: str) -> None:
    click.echo(f"Stopping container {container_name}...")
    try:
        client.containers.get(container_name).stop(timeout=1)
    except errors.NotFound:
        raise Exception(f"Container `{container_name}` not found")


def start(container_name: str) -> None:
    click.echo(f"Starting container {container_name}...")
    try:
        client.containers.get(container_name).start()
    except errors.NotFound:
        raise Exception(f"Container `{container_name}` not found")


def exists(container_name: str) -> bool:
    try:
        client.containers.get(container_name)
        return True
    except errors.NotFound:
        return False


def is_running(container_name: str) -> bool:
    try:
        return client.containers.get(container_name).status == "running"
    except errors.NotFound:
        return False
