from __future__ import annotations
import dataclasses
import pathlib
import typing as t
import yaml


if t.TYPE_CHECKING:
    from typing_extensions import Unpack

    # TODO typing: remove
    _Attrs = t.Literal[
        "container_name",
        "directory",
        "namespace",
    ]

    class SettingsKwargs(t.TypedDict):
        container_name: t.Optional[str]
        directory: t.Optional[str]
        namespace: t.Optional[str]


DEFAULT_PATH: t.Final[pathlib.Path] = pathlib.Path("ds.yaml")


@dataclasses.dataclass
class Settings:
    container_name: str
    directory: str
    namespace: str


_data: t.Optional[Settings] = None


def get_default_settings() -> Settings:
    return Settings(container_name="", directory="/", namespace="ds")


def _get_from_file() -> Settings:
    if not DEFAULT_PATH.exists():
        raise FileNotFoundError(
            f"Didn't find '{DEFAULT_PATH}'. Run init and try again."
        )

    with DEFAULT_PATH.open("r") as f:
        buffer = f.read()

    data = yaml.load(buffer, Loader=yaml.FullLoader)

    # TODO typing: fix, unsafe
    return Settings(**data)


def _load() -> Settings:
    try:
        return _get_from_file()
    except FileNotFoundError:
        return get_default_settings()


def _override(original: Settings, replacement: "SettingsKwargs") -> Settings:
    return Settings(
        container_name=replacement["container_name"] or original.container_name,
        directory=replacement["directory"] or original.directory,
        namespace=replacement["namespace"] or original.namespace,
    )


def load(**kwargs: Unpack[SettingsKwargs]) -> Settings:
    return _override(original=_load(), replacement=kwargs)


def init() -> None:
    if DEFAULT_PATH.exists():
        raise Exception(f"File already exists, delete '{DEFAULT_PATH}' and try again.")

    with DEFAULT_PATH.open("w") as f:
        f.write(yaml.dump(dataclasses.asdict(get_default_settings())))


# TODO typing: remove
def get(attribute: "_Attrs") -> str:
    global _data
    if _data:
        # HACK: temporary hack
        return t.cast(str, getattr(_data, attribute))

    _data = _get_from_file()

    # HACK: temporary hack
    return t.cast(str, getattr(_data, attribute))
