from functools import partial, wraps
import asyncio


def synchronously(f=None, pass_loop=False, loop_getter=asyncio.get_event_loop):
    if f is None:
        return partial(synchronously, pass_loop=pass_loop, loop_getter=loop_getter)

    @wraps(f)
    def run(*args, **kwargs):
        loop = loop_getter()
        if pass_loop:
            args = (loop,) + args
        return loop.run_until_complete(f(*args, **kwargs))
    return run
