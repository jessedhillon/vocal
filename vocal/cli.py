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

        if config_path is None:
            config_path = base_path / 'config' / app_path
        if ctx.obj is None:
            ctx.obj = {}

        ctx.obj.update(await vocal.config.load_config(config_path, env))
        ctx.obj['module'] = import_module(app_path)

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
@click.pass_obj
def serve(config):
    loop = asyncio.get_event_loop()
    logger = logging.getLogger(__name__)
    mod = config['module']

    async def setup_app(config, module):
        config.update(await mod.configure(config))
        return await module.initialize(config)

    app = loop.run_until_complete(setup_app(config, mod))
    appconf = config['app'].copy()
    appname = appconf.pop('name')

    logger.info(f"starting {appname}")
    aiohttp.web.run_app(app, **appconf)


@main.group()
@click.pass_obj
def database(config):
    dbconf = config['database']

    connargs = dbconf['connection']
    connargs.update(config['secrets']['database'])
    dsn = sqlalchemy.engine.url.URL('postgresql', **connargs)
    escaped = str(dsn).replace('%', '%%')

    alconf = alembic.config.Config()
    alconf.set_main_option('script_location', str(base_path / 'vocal' / 'migrations'))
    alconf.set_section_option('alembic', 'sqlalchemy.url', escaped)
    alconf.set_section_option('alembic', 'file_template', '%%(slug)s-%%(rev)s')

    config['alembic'] = alconf


@database.command()
@click.argument('revision')
@click.pass_obj
def up(config, revision):
    alembic.command.upgrade(config.pop('alembic'), revision)


@database.command()
@click.argument('revision')
@click.pass_obj
def down(config, revision):
    alembic.command.downgrade(config.pop('alembic'), revision)


@database.command()
@click.argument('message')
@click.pass_obj
def generate(config, message):
    alembic.command.revision(config.pop('alembic'), message)
