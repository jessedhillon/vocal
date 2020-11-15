from logging import StreamHandler


class TTYAwareColoredStreamHandler(StreamHandler):
    """
    A StreamHandler that communicates the tty capability of its stream to the
    downstream formatter.
    """

    def setFormatter(self, fmt):
        super().setFormatter(fmt)
        self.update_color_formater()

    def setStream(self, stream):
        super().setStream(stream)
        self.update_color_formater()

    def update_color_formater(self):
        if hasattr(self.stream, 'isatty') and hasattr(self.formatter, 'enable_color'):
            self.formatter.enable_color(self.stream.isatty())
