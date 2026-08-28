import subprocess

from .base import SecretBackend


class SecretServiceBackend(SecretBackend):
    """Secret backend using Linux Secret Service via secret-tool."""

    def __init__(self, service: str = "kabutam"):
        self.service = service

    def get(self, name: str) -> str:
        try:
            result = subprocess.run(
                [
                    "secret-tool",
                    "lookup",
                    "service",
                    self.service,
                    "username",
                    name,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError as e:
            raise RuntimeError(
                "secret-tool コマンドが見つかりません。"
                "libsecret の secret-tool をインストールしてください。"
            ) from e

        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Secret Service から secret '{name}' を取得できませんでした。"
                "Secret Service が利用可能か確認してください。"
            ) from e

        value = result.stdout.strip()

        if not value:
            raise RuntimeError(f"secret '{name}' が空です。")

        return value
