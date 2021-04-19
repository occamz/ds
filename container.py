import io
import re
import shlex
import click
import docker
import importlib.resources as pkg_resources
import settings
from docker import errors
import images


client = docker.from_env()
BASE_PATH = "/mnt/ds"


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


def run_container(image, volume):
    container = client.containers.run(
        image,
        name=get_container_id(),
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
            f"rsync -aAHX --delete --info=progress2 {source_directory}/ {destination_path}",
        ],
        stream=True,
        stdout=True,
        stderr=True,
    )
    current_percentage = 0
    with click.progressbar(length=100, label="Copying files", show_eta=True) as bar:
        for out in response.output:
            percentage_string = re.search(r"\d+%", out.decode("utf-8"))
            if percentage_string:
                try:
                    percentage = int(percentage_string.group()[:-1])
                    if current_percentage < percentage:
                        bar.update(percentage - current_percentage)
                        current_percentage = percentage
                except Exception as e:
                    pass
        bar.update(100)


def stop(container_name):
    try:
        container = client.containers.get(container_name)
        container.stop()
    except errors.NotFound:
        raise Exception(f"Container `{container_name}` not found")


def start(container_name):
    try:
        container = client.containers.get(container_name)
        container.start()
    except errors.NotFound:
        raise Exception(f"Container `{container_name}` not found")
