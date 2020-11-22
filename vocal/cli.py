import asyncio
import logging
import pdb
import traceback
from pathlib import Path
from importlib import import_module

import aiohttp.web
import alembic.config
import click
import sqlalchemy

import vocal.config
import vocal.log
from vocal.util.asyncio import synchronously


base_path = Path(__file__).parent.parent

@click.group()
@click.option('-D', '--debug', is_flag=True, default=False)
@click.option('-C', '--config_path', default=None)
@click.option('-E', '--env', default='dev')
@click.argument('app_path')
@click.pass_context
@synchronously(pass_loop=True)
async def main(loop, ctx, debug, config_path, env, app_path):
    try:
        loop.set_debug(debug)
        appctx = vocal.config.AppConfig('debug', 'config', 'module')

        if config_path is None:
            config_path = base_path / 'config' / app_path
        if ctx.obj is None:
            ctx.obj = appctx

        appctx.config.set(await vocal.config.load_config(config_path, env))
        appctx.module.set(import_module(app_path))

        await vocal.log.configure(appctx)
        logger = logging.getLogger(__name__)

        appctx.debug.set(debug)
        if debug:
            logger.info('debugging mode enabled')
        assert appctx.ready
    except:
        if debug:
            traceback.print_exc()
            pdb.post_mortem()
        raise


@main.command()
@click.pass_obj
def serve(appctx):
    loop = asyncio.get_event_loop()
    logger = logging.getLogger(__name__)
    mod = appctx.module.get()
    config = appctx.config.get()

    async def setup_app(appctx, module):
        await mod.configure(appctx)
        return await module.initialize(appctx)

    app = loop.run_until_complete(setup_app(appctx, mod))
    appconf = config['app'].copy()
    appname = appconf.pop('name')

    logger.info(f"starting {appname}")
    loop.run_until_complete(aiohttp.web.run_app(app, **appconf))


@main.group()
@click.pass_obj
def database(appctx):
    appctx.declare('alembic_conf')

    config = appctx.config.get()
    dbconf = config['storage']

    connargs = dbconf['connection']
    connargs.update(config['secrets']['storage'])
    dsn = sqlalchemy.engine.url.URL.create('postgresql', **connargs)

    # we have to escape ourselves, instead of letting user escape in the conf
    # because create_async_engine does its own escaping (maybe?)
    esc = str(dsn).replace('%', '%%')

    alconf = alembic.config.Config()
    alconf.set_main_option('script_location', str(base_path / 'vocal' / 'migrations'))
    alconf.set_section_option('alembic', 'sqlalchemy.url', esc)
    alconf.set_section_option('alembic', 'file_template', '%%(slug)s-%%(rev)s')

    appctx.alembic_conf.set(alconf)
    assert appctx.ready


@database.command()
@click.argument('revision')
@click.pass_obj
def up(appctx, revision):
    alconf = appctx.alembic_conf.get()
    alembic.command.upgrade(alconf, revision)


@database.command()
@click.argument('revision')
@click.pass_obj
def down(appctx, revision):
    alconf = appctx.alembic_conf.get()
    alembic.command.downgrade(alconf, revision)


@database.command()
@click.argument('message')
@click.pass_obj
def generate(appctx, message):
    alconf = appctx.alembic_conf.get()
    alembic.command.revision(alconf, message)
