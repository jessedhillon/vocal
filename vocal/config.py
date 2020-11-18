from pathlib import Path

import yaml


async def load_config(config_path, env):
    env_path = Path(config_path) / env
    common_path = Path(config_path) / 'common'

    base_conf = {}
    if common_path.exists():
        for p in common_path.parent.glob('*.yaml'):
            path = Path(p)
            keyname = path.stem
            if keyname in base_conf:
                raise RuntimeError(f"disallowed or multiply-defined configuration key: common/{keyname}")
            with path.open('r') as f:
                base_conf[keyname] = yaml.load(f.read(), Loader=yaml.CLoader)

    env_conf = {}
    for p in env_path.glob('*.yaml'):
        path = Path(p)
        keyname = path.stem
        if keyname in env_conf:
            raise RuntimeError(f"disallowed or multiply-defined configuration key: {env}/{keyname}")
        with path.open('r') as f:
            env_conf[keyname] = yaml.load(f.read(), Loader=yaml.CLoader)

    base_conf.update(env_conf)
    return base_conf
