import pdb
import traceback
from pathlib import Path

import click

import vocal.config
from vocal.util.asyncio import synchronously


base_path = Path(__file__).parent.parent


@click.group()
@click.option('-D', '--debug', is_flag=True, default=False)
@click.option('-C', '--config_path', default=str(base_path / 'config'))
@click.pass_context
@synchronously
async def main(ctx, debug, config_path):
    try:
        if ctx.obj is None:
            ctx.obj = {}
        ctx.obj.update(await vocal.config.configure(config_path))
    except:
        if debug:
            traceback.print_exc()
            pdb.post_mortem()
        raise


@main.command()
@click.pass_obj
@synchronously
async def serve(config):
    pdb.set_trace()
