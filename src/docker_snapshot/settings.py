import dataclasses
import os
import typing as t
import yaml


if t.TYPE_CHECKING:
    # TODO: remove
    _Attrs = t.Literal[
        "container_name",
        "directory",
        "namespace",
    ]


DEFAULT_FILENAME: t.Final[str] = "ds.yaml"


@dataclasses.dataclass
class Settings:
    container_name: str
    directory: str
    namespace: str


_data: t.Optional[Settings] = None


def get_default_settings() -> Settings:
    return Settings(container_name="", directory="/", namespace="ds")


def init() -> None:
    path = DEFAULT_FILENAME
    if os.path.exists(path):
        raise Exception(
            f"File already exists, delete {DEFAULT_FILENAME} and try again."
        )

    with open(path, "w") as f:
        f.write(yaml.dump(dataclasses.asdict(get_default_settings())))


# TODO: fix
def get(attribute: "_Attrs") -> str:
    global _data
    if _data:
        # HACK: temporary hack
        return t.cast(str, getattr(_data, attribute))

    path = DEFAULT_FILENAME
    if not os.path.exists(path):
        raise Exception(f"Didn't find {DEFAULT_FILENAME}. Run init and try again.")

    with open(path, "r") as f:
        string_data = f.read()

    dict_data = yaml.load(string_data, Loader=yaml.FullLoader)

    _data = Settings(**dict_data)

    # HACK: temporary hack
    return t.cast(str, getattr(_data, attribute))
