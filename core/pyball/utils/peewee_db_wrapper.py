import functools

from typing import Any, Callable, TypeVar, cast

from peewee import Database

F = TypeVar("F", bound=Callable[..., Any])


def connection_wrapper(database: Database) -> F:
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def inner_decorator(*args, **kwargs):
            with database:
                ret_val = func(*args, **kwargs)
            return ret_val

        return cast(F, inner_decorator)

    return decorator
