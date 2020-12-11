from . import mock
from .base import BasePaymentProcessor


async def configure(appctx):
    # enumerate and configure all modules discovered in conf
    # wrap in configuration class
    # expose through registry
    appctx.declare('payments')
    config = appctx.config.get()
    pmtconf = config.get('payments', {})
    pmtconf.update(config['secrets']['payments'])

    registry = {}
    # TODO: load modules dynamically based on configuration
    for name in pmtconf.keys():
        if name == 'mock':
            proc = mock.configure(**pmtconf['mock'])
            register_processor(registry, proc.processor_id, proc)
        else:
            raise ValueError(name)
    appctx.payments.set(registry)


def register_processor(registry: dict, processor_id: str, processor: BasePaymentProcessor):
    registry[processor_id] = processor
