from abc import ABC, abstractmethod


class SecretBackend(ABC):
    """Secret storage backend interface."""

    @abstractmethod
    def get(self, name: str) -> str:
        """Retrieve a secret by name."""
        raise NotImplementedError
