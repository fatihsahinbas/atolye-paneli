"""Log hijyeni: e-posta, telefon ve token'lar maskelenir (Checklist #14)."""
import logging
import re

_EMAIL = re.compile(r"([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+)")
_PHONE = re.compile(r"(?<!\d)(\+?90)?\s?0?(5\d{2})[\s-]?\d{3}[\s-]?\d{2}[\s-]?(\d{2})(?!\d)")
_TOKEN = re.compile(r"(token|session|password|sifre|secret)=([^\s&]+)", re.IGNORECASE)


def mask(text: str) -> str:
    text = _EMAIL.sub(r"\1***@\2", text)
    text = _PHONE.sub(r"\2*****\3", text)
    text = _TOKEN.sub(r"\1=***", text)
    return text


class MaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Önce mesajı biçimlendir (%d, %s...), sonra maskele
        record.msg = mask(record.getMessage())
        record.args = None
        return True


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.addFilter(MaskingFilter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
