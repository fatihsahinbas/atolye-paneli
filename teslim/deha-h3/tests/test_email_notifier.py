import smtplib
import pytest

from app.notifiers.email import EmailNotifier
from tests.conftest import FakeSMTP


def test_email_send_success():
    n = EmailNotifier("h", 587, "u", "p", "from@x", smtp_factory=FakeSMTP)
    assert n.send("to@x", "merhaba") is True
    assert len(FakeSMTP.instances[-1].sent) == 1


def test_email_smtp_failure_raises():
    FakeSMTP.fail = True
    n = EmailNotifier("h", 587, "u", "p", "from@x", smtp_factory=FakeSMTP)
    with pytest.raises(smtplib.SMTPException):
        n.send("to@x", "merhaba")


def test_password_masked_in_repr():
    n = EmailNotifier("h", 587, "u", "supersecret", "from@x")
    r = repr(n)
    assert "supersecret" not in r
    assert "***" in r