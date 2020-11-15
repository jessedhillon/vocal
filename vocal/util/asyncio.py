import asyncio


def synchronously(f, loop_getter=asyncio.get_event_loop):
    def run(*args, **kwargs):
        loop = loop_getter()
        return loop.run_until_complete(f(*args, **kwargs))
    run.__name__ = f.__name__
    return run
