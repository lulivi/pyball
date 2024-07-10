import functools
import logging

from typing import Any, Callable, TypeVar, cast

from peewee import Database

from pyball.logger import log_func

logger = logging.getLogger(__name__)


F = TypeVar("F", bound=Callable[..., Any])


@log_func
def connection_wrapper(database: Database) -> F:
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def inner_decorator(*args, **kwargs):
            logger.debug("    >>> Opening database connection")
            with database:
                ret_val = func(*args, **kwargs)
                logger.debug("    <<< Closing database connection")
            return ret_val

        return cast(F, inner_decorator)

    return decorator
