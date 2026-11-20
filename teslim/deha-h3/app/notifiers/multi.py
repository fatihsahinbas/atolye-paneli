from app.notifiers.base import BaseNotifier


class MultiNotifier:
    """Telefon varsa SMS, yoksa e-posta, ikisi de yoksa SKIPPED."""

    def __init__(self, sms: BaseNotifier, email: BaseNotifier):
        self.sms = sms
        self.email = email

    def choose_and_send(self, customer, message: str) -> tuple[str, bool]:
        if customer.phone:
            try:
                return "SMS", self.sms.send(customer.phone, message)
            except Exception:
                return "SMS", False
        if customer.email:
            try:
                return "EMAIL", self.email.send(customer.email, message)
            except Exception:
                return "EMAIL", False
        return "SKIPPED", False