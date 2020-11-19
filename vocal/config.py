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


class ConfigVar(object):
    def __init__(self, name, *default):
        if len(default) > 1:
            raise ValueError(default)
        self.name = name
        self.no_default = len(default) == 0
        self.not_set = True
        self.default = None if self.no_default else default[0]
        self.value = None

    def set(self, value):
        if self.not_set:
            self.value = value
            self.not_set = False
        else:
            raise RuntimeError(value)

    def get(self):
        if self.not_set:
            if self.no_default:
                raise LookupError()
            return self.default
        return self.value


class AppConfig(object):
    def __init__(self, *declares):
        self.__dict__['_cvars'] = {}
        self.__dict__['_declared'] = set([])
        for varname in declares:
            self.declare(varname)

    def declare(self, varname, *default):
        _declared = self.__dict__['_declared']
        _cvars = self.__dict__['_cvars']
        if varname in _declared:
            raise KeyError(varname)
        _declared.add(varname)
        _cvars[varname] = ConfigVar(varname, *default)

    @property
    def ready(self):
        ready = True
        for varname in self._declared:
            try:
                self._cvars[varname].get()
            except LookupError:
                ready = False
        return ready

    def __getattr__(self, varname):
        _cvars = self.__dict__['_cvars']
        if varname not in _cvars:
            return KeyError(varname)
        return _cvars[varname]

    def __setattr__(self, varname, v):
        raise RuntimeError()
        _cvars = self.__dict__['_cvars']
        if varname not in _cvars:
            return KeyError(varname)
        _cvars[varname].set(v)

    def __contains__(self, key):
        return key in self._cvars

    def __iter__(self):
        return iter(self._cvars)

    def __len__(self):
        return len(self._cvars)

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self._cvars)

    def __hash__(self):
        h = 0
        for key, value in iteritems(self._cvars):
            h ^= hash((key, value))
        return h
