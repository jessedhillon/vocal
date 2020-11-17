from pathlib import Path

import yaml


async def load_config(config_path):
    cfpath = Path(config_path) / 'config.yaml'
    with cfpath.open('r') as cf:
        config = yaml.load(cf.read(), Loader=yaml.CLoader) or {}

    for p in cfpath.parent.glob('*.yaml'):
        path = Path(p)
        if path.samefile(cfpath):
            continue
        keyname = path.stem
        if keyname in config:
            raise RuntimeError(f"disallowed or multiply-defined configuration key: {keyname}")
        with path.open('r') as f:
            config[keyname] = yaml.load(f.read(), Loader=yaml.CLoader)

    return config
