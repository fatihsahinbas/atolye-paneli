import logging

from app.core.logging import MaskingFilter


def test_email_masked_in_log(caplog):
    logger = logging.getLogger("test.mask")
    logger.addFilter(MaskingFilter())
    with caplog.at_level(logging.INFO, logger="test.mask"):
        logger.info("gönderim: veli@example.com adresine")
    assert "veli@example.com" not in caplog.text
    assert "v***@example.com" in caplog.text


def test_phone_masked_in_log(caplog):
    logger = logging.getLogger("test.mask2")
    logger.addFilter(MaskingFilter())
    with caplog.at_level(logging.INFO, logger="test.mask2"):
        logger.info("sms: +905551112233")
    assert "+905551112233" not in caplog.text
    assert "***" in caplog.text