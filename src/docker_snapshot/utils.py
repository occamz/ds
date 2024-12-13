import typing as t


# Fuck this name
def sizeof_fmt(num: float, suffix: str = "B") -> str:
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, "Yi", suffix)


@t.overload
def pluralize(
    word: str,
    n: int,
    *,
    suffix: str,
) -> str: ...


@t.overload
def pluralize(
    word: str,
    n: int,
    *,
    plural: str,
) -> str: ...


def pluralize(
    word: str,
    n: int,
    *,
    suffix: t.Optional[str] = None,
    plural: t.Optional[str] = None,
) -> str:
    if n == 1:
        return word

    if plural is not None:
        return plural

    if suffix is not None:
        return f"{word}{suffix}"

    raise ValueError("either `suffix` or `plural` must be non-null")
