import asyncio
import logging
import pdb
import traceback
from pathlib import Path
from importlib import import_module

import aiohttp.web
import click

import vocal.config
import vocal.log
from vocal.util.asyncio import synchronously


base_path = Path(__file__).parent.parent
config_path = str(base_path / 'config')


@click.group()
@click.option('-D', '--debug', is_flag=True, default=False)
@click.option('-C', '--config_path', default=config_path)
@click.pass_context
@synchronously(pass_loop=True)
async def main(loop, ctx, debug, config_path):
    try:
        loop.set_debug(debug)
        if ctx.obj is None:
            ctx.obj = {}
        ctx.obj.update(await vocal.config.load_config(config_path))
        await vocal.log.configure(ctx.obj)

        logger = logging.getLogger(__name__)
        if debug:
            ctx.obj['debug'] = True
            logger.info('debugging mode enabled')
    except:
        if debug:
            traceback.print_exc()
            pdb.post_mortem()
        raise


@main.command()
@click.argument('app_path')
@click.pass_obj
def serve(config, app_path):
    loop = asyncio.get_event_loop()
    logger = logging.getLogger(__name__)
    mod = import_module(app_path)

    async def setup_app(config, module):
        config.update(await mod.configure(config))
        return await module.initialize(config)

    app = loop.run_until_complete(setup_app(config, mod))
    appconf = config[app_path]
    appname = appconf.pop('name')
    logger.info(f"starting {appname}")

    aiohttp.web.run_app(app, **appconf)
