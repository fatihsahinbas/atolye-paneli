from abc import ABC, abstractmethod


class BaseNotifier(ABC):
    @abstractmethod
    def send(self, recipient: str, message: str) -> bool: ...