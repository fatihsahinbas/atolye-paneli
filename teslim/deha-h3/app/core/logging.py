import logging
import re

EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]{1,2})[A-Za-z0-9._%+-]*(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE_RE = re.compile(r"(\+?\d{1,3})[\d\s\-]{4,}(\d{2})")


class MaskingFilter(logging.Filter):
    """Telefon ve e-postayı log'larda maskeler."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        msg = EMAIL_RE.sub(r"\1***\2", msg)
        msg = PHONE_RE.sub(r"\1***\2", msg)
        record.msg = msg
        record.args = ()
        return True


def setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.addFilter(MaskingFilter())
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)