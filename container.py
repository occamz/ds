import re
import shlex
import click
import docker
import settings
from docker import errors


client = docker.from_env()
namespace = settings.get("namespace")
ID_IMAGE = f"ds-{namespace}"
ID_VOLUME = f"ds-{namespace}"
ID_CONTAINER = f"ds-{namespace}"
BASE_PATH = "/mnt/ds"


def build_image():
    image, _ = client.images.build(path=".", tag=ID_IMAGE)
    return image


def create_volume():
    return client.volumes.create(name=ID_VOLUME)


def run_container(image, volume):
    container = client.containers.run(
        image,
        name=ID_CONTAINER,
        volumes={volume.name: {"bind": BASE_PATH, "mode": "rw"}},
        volumes_from=[settings.get("container_name")],
        working_dir=BASE_PATH,
        remove=True,
        auto_remove=True,
        detach=True,
    )
    return container


def init():
    # Get or build image
    try:
        # NOTE: Blocks future versions of Dockerfile
        image = client.images.get(ID_IMAGE)
    except errors.ImageNotFound:
        image = build_image()

    # Get or create volume
    try:
        volume = client.volumes.get(ID_VOLUME)
    except errors.NotFound:
        volume = create_volume()

    # Get and/or run container
    try:
        container = client.containers.get(ID_CONTAINER)
    except errors.NotFound:
        container = run_container(image, volume)

    return container


def sh(input, container=None):

    if not container:
        container = init()

    code, output = container.exec_run(["sh", "-c", input])
    return output.decode("utf-8")


def file_read(path):
    return sh(f"cat {path} 2>/dev/null")


def file_write(path, content):
    return sh(f"echo {shlex.quote(content)} > {path}")


def directory_remove(path):
    return sh(f"rm -rf {path}")


def directory_size(path):
    # Replace with regex
    size = int(sh(f"du -s {path}").split("\t")[0]) * 1024
    return size


def sync(source_directory, destination_path):
    container = init()

    response = container.exec_run(
        [
            "sh",
            "-c",
            f"rsync -a --info=progress2 {source_directory}/* {destination_path}",
        ],
        stream=True,
        stdout=True,
        stderr=True,
    )
    with click.progressbar(length=100, label="Copying files", show_eta=False) as bar:
        for out in response.output:
            percentage_string = re.search(r"\d+%", out.decode("utf-8"))
            if percentage_string:
                try:
                    percentage = int(percentage_string.group()[:-1])
                    bar.update(percentage)
                except Exception as e:
                    pass
        bar.update(100)


def pause(container_name):
    try:
        container = client.containers.get(container_name)
        container.pause()
    except errors.NotFound:
        raise Exception(f"Container `{container_name}` not found")


def unpause(container_name):
    try:
        container = client.containers.get(container_name)
        container.unpause()
    except errors.NotFound:
        raise Exception(f"Container `{container_name}` not found")
