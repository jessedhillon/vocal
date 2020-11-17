from aiohttp.web import Application

from .routes import routes


async def configure(config):
    # e.g. configure storage, template renderer, etc
    return {
        'routes': routes
    }


async def initialize(config):
    app = Application()
    app.add_routes(config['routes'])
    return app
