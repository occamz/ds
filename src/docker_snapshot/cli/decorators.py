from __future__ import annotations
import functools
import typing as t
import click
from docker_snapshot import settings


if t.TYPE_CHECKING:
    from click import Context
    from typing_extensions import Concatenate, ParamSpec
    from docker_snapshot.settings import Settings

    P = ParamSpec("P")
    R = t.TypeVar("R")

    _Func = t.Callable[Concatenate[Settings, Context, P], R]
    _Wrapper = t.Callable[Concatenate[Context, P], R]


def find_root_settings(f: _Func[P, R]) -> _Wrapper[P, R]:
    @functools.wraps(f)
    def inner(ctx: Context, /, *args: P.args, **kwargs: P.kwargs) -> R:
        # HACK: ultrahack to avoid storing stuff in global scope
        _root_ctx = ctx.find_root()
        _settings = settings.load(**_root_ctx.params)
        return f(_settings, ctx, *args, **kwargs)

    return inner


pass_settings = click.make_pass_decorator(settings.Settings)
