import logging
import logging.config
import time

from .formatter import TogglingColoredFormatter
from .handler import TTYAwareColoredStreamHandler


__all__ = [
    'TogglingColoredFormatter',
    'TTYAwareColoredStreamHandler',
]


async def configure(config):
    logging.config.dictConfig(config['logging'])
    logging.Formatter.converter = time.gmtime
