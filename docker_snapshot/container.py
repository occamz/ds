import io
import re
import shlex
import importlib.resources as pkg_resources
import click
import docker
from functools import wraps
from rich.progress import Progress
from docker import errors
from docker_snapshot import images, settings


HELPER_BASE_PATH = "/mnt/ds"

client = docker.from_env()
container = None


def requires_helper_container(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        alloc()
        res = f(*args, **kwargs)
        dealloc()
        return res

    return wrapper


class freeze_target_container(object):
    def __init__(self):
        pass

    def __enter__(self):
        stop(settings.get("container_name"))

    def __exit__(self, type, value, traceback):
        start(settings.get("container_name"))


def is_target_container_running():
    return is_running(settings.get("container_name"))


def get_image_id():
    namespace = settings.get("namespace")
    return f"ds-{namespace}"


def get_volume_id():
    namespace = settings.get("namespace")
    return f"ds-{namespace}"


def get_container_id():
    namespace = settings.get("namespace")
    return f"ds-{namespace}"


def build_image():
    dockerfile = io.BytesIO(pkg_resources.read_text(images, "rsync").encode("utf-8"))
    image, _ = client.images.build(fileobj=dockerfile, tag=get_image_id())
    return image


def create_volume():
    return client.volumes.create(name=get_volume_id())


def create_container(image, volume, volumes_from):
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


def alloc():
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


def dealloc():
    container.stop(timeout=0)


def sh(command):
    global container
    code, output = container.exec_run(["sh", "-c", command])
    return output.decode("utf-8")


def file_read(path):
    return sh(f"cat {path} 2>/dev/null")


def file_write(path, content):
    return sh(f"echo {shlex.quote(content)} > {path}")


def directory_remove(path):
    return sh(f"rm -rf {path}")


def directory_size(path):
    # TODO: Replace with regex
    size = int(sh(f"du -s {path}").split("\t")[0]) * 1024
    return size


def sync(source_directory, destination_path):
    global container

    response = container.exec_run(
        [
            "sh",
            "-c",
            f"rsync -aAHX --delete --info=progress2 {source_directory}/ {destination_path}",
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
            except Exception as e:
                pass

            progress.update(task, advance=percentage - current_percentage)
            current_percentage = percentage
        progress.update(task, completed=100)


def stop(container_name):
    click.echo(f"Stopping container {container_name}...")
    try:
        client.containers.get(container_name).stop(timeout=1)
    except errors.NotFound:
        raise Exception(f"Container `{container_name}` not found")


def start(container_name):
    click.echo(f"Starting container {container_name}...")
    try:
        client.containers.get(container_name).start()
    except errors.NotFound:
        raise Exception(f"Container `{container_name}` not found")


def exists(container_name):
    try:
        client.containers.get(container_name)
        return True
    except errors.NotFound:
        return False


def is_running(container_name):
    try:
        return client.containers.get(container_name).status == "running"
    except errors.NotFound:
        return False
