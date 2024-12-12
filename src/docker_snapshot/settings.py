import os
import yaml
import dataclasses

DEFAULT_FILENAME = "ds.yaml"


@dataclasses.dataclass
class Settings:
    container_name: ""
    directory: ""
    namespace: ""


_data = None


def get_default_settings():
    return Settings(container_name="", directory="/", namespace="ds")


def init():
    path = DEFAULT_FILENAME
    if os.path.exists(path):
        raise Exception(
            f"File already exists, delete {DEFAULT_FILENAME} and try again."
        )

    with open(path, "w") as f:
        f.write(
            yaml.dump(
                dataclasses.asdict(
                    get_default_settings()
                )
            )
        )


def get(attribute):
    global _data
    if _data:
        return getattr(_data, attribute)

    path = DEFAULT_FILENAME
    if not os.path.exists(path):
        raise Exception(f"Didn't find {DEFAULT_FILENAME}. Run init and try again.")

    with open(path, "r") as f:
        string_data = f.read()

    dict_data = yaml.load(string_data, Loader=yaml.FullLoader)

    _data = Settings(**dict_data)

    return getattr(_data, attribute)
