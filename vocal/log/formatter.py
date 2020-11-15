from colorlog import ColoredFormatter


class TogglingColoredFormatter(ColoredFormatter):
    """
    Blanks all color codes if not running under a TTY.

    This is useful when you want to be able to pipe colorlog output to a file.
    """

    def __init__(self, *args, **kwargs):
        """Overwrite the `reset` argument to False if stream is not a TTY."""
        self._color_enabled = kwargs.pop('color_enabled', True)

        # Both `reset` and `is_stream_tty` must be true to insert reset codes.
        self._reset = kwargs.get('reset', True)

        super().__init__(*args, **kwargs)

    def enable_color(self, v):
        self._color_enabled = bool(v)

    @property
    def color_enabled(self):
        return self._color_enabled

    @property
    def reset(self):
        return self._reset and self.color_enabled

    @reset.setter
    def reset(self, v):
        self._reset = bool(v)

    def color(self, log_colors, level_name):
        """Return escape codes from a ``log_colors`` dict."""
        if self.color_enabled:
            return super().color(log_colors, level_name)
        return super().color({}, level_name)
