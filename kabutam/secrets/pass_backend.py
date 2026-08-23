import subprocess

from .base import SecretBackend


class PassBackend(SecretBackend):
    def __init__(self, paths: dict[str, str]):
        self.paths = paths

    def get(self, name: str) -> str:
        try:
            path = self.paths[name]
        except KeyError as e:
            raise RuntimeError(
                f"pass backendにsecret '{name}' の設定がありません。"
            ) from e

        try:
            result = subprocess.run(
                ["pass", "show", path],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError as e:
            raise RuntimeError(
                "pass コマンドが見つかりません。"
            ) from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"pass から secret '{name}' を取得できませんでした。"
            ) from e

        value = result.stdout.splitlines()[0].strip()

        if not value:
            raise RuntimeError(
                f"secret '{name}' が空です。"
            )

        return value
