from app.notifiers.base import BaseNotifier


class SmsNotifier(BaseNotifier):
    """PR #5 gelince gerçek SMS/WhatsApp gateway ile değiştirilecek."""

    def __init__(self, api_key: str = ""):
        self._api_key = api_key

    def __repr__(self) -> str:
        return "<SmsNotifier api_key=***>"

    def send(self, recipient: str, message: str) -> bool:
        # Gerçek entegrasyona kadar sahte başarı
        return True