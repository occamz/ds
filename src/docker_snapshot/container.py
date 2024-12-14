from __future__ import annotations
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
from docker_snapshot import images


if t.TYPE_CHECKING:
    from types import TracebackType
    from docker.client import DockerClient
    from docker.models.containers import Container
    from docker.models.images import Image
    from docker.models.volumes import Volume
    from docker_snapshot.settings import Settings

    P = t.ParamSpec("P")
    R = t.TypeVar("R")

    F = t.Callable[t.Concatenate[Settings, P], R]


HELPER_BASE_PATH = "/mnt/ds"

client: DockerClient = docker.from_env()
container: t.Optional[Container] = None


def requires_helper_container(f: F[P, R]) -> F[P, R]:
    @wraps(f)
    def wrapper(settings: Settings, /, *args: P.args, **kwargs: P.kwargs) -> R:
        alloc(container_name=settings.container_name, namespace=settings.namespace)
        res = f(settings, *args, **kwargs)
        dealloc()
        return res

    return wrapper


class freeze_target_container(object):
    def __init__(self, name: str) -> None:
        self.name = name

    def __enter__(self) -> None:
        stop(self.name)

    def __exit__(
        self,
        exception_type: t.Optional[t.Type[BaseException]],
        exception: t.Optional[BaseException],
        traceback: t.Optional[TracebackType],
    ) -> None:
        start(self.name)


def is_target_container_running(name: str) -> bool:
    return is_running(name)


def get_image_id(namespace: str) -> str:
    return f"ds-{namespace}"


def get_volume_id(namespace: str) -> str:
    return f"ds-{namespace}"


def get_container_id(namespace: str) -> str:
    return f"ds-{namespace}"


def build_image(namespace: str) -> Image:
    dockerfile = io.BytesIO(pkg_resources.read_text(images, "rsync").encode("utf-8"))
    tag = get_image_id(namespace=namespace)
    image, _ = client.images.build(fileobj=dockerfile, tag=tag)
    return image


def create_volume(namespace: str) -> Volume:
    name = get_volume_id(namespace=namespace)
    return client.volumes.create(name=name)


def create_container(
    image: t.Union[str, Image],
    volume: Volume,
    volumes_from: str,
    namespace: str,
) -> Container:
    return client.containers.create(
        image,
        name=get_container_id(namespace=namespace),
        volumes={volume.name: {"bind": HELPER_BASE_PATH, "mode": "rw"}},
        volumes_from=[volumes_from],
        working_dir=HELPER_BASE_PATH,
        tty=True,
        stdin_open=True,
        auto_remove=False,
        detach=True,
    )


def alloc(container_name: str, namespace: str) -> None:
    global container
    # Get or build image
    try:
        # NOTE: Blocks future versions of Dockerfile
        image = client.images.get(get_image_id(namespace=namespace))
    except errors.ImageNotFound:
        image = build_image(namespace=namespace)

    # Get or create volume
    try:
        volume = client.volumes.get(get_volume_id(namespace=namespace))
    except errors.NotFound:
        volume = create_volume(namespace=namespace)

    # Get and/or run container
    try:
        container = client.containers.get(get_container_id(namespace=namespace))
    except errors.NotFound:
        if not exists(container_name=container_name):
            raise Exception(f"Target container with name {container_name} not found.")
        container = create_container(
            image=image,
            volume=volume,
            volumes_from=container_name,
            namespace=namespace,
        )

    container.start()


def dealloc() -> None:
    global container

    if container is None:
        return

    # NOTE: trying to stop the container breaks hanging I/O,
    # whereas force removing it automatically ends sessions
    # container.stop(timeout=0)
    container.remove(force=True)


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
def directory_filecount(path: str) -> int:
    try:
        return int(sh(f"find {path} -type f | wc -l"))
    except ValueError:
        return 0


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
        client.containers.get(container_name).stop(timeout=2)
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
