import functools
from pathlib import Path
import tomllib

from platformdirs import user_config_dir

from kabutam.secrets.base import SecretBackend
from kabutam.secrets.pass_backend import PassBackend
from kabutam.secrets.secretservice import SecretServiceBackend


APP_NAME = "kabutam"

DEFAULT_PASS_PATHS = {
    "EDNET_DB_API_KEY": "ednetdb/api/EDNET_DB_API_KEY",
    "JPX_JQUANTS_API_KEY": "jpx-jquants.com/api/JPX_JQUANTS_API_KEY",
}


def get_config_path() -> Path:
    return Path(user_config_dir(APP_NAME)) / "config.toml"


@functools.lru_cache(maxsize=1)
def load_config() -> dict:
    config_path = get_config_path()

    if not config_path.exists():
        return {}

    try:
        with config_path.open("rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise RuntimeError(
            f"設定ファイルの形式が正しくありません: {config_path}"
        ) from e


def get_secret_backend() -> SecretBackend:
    config = load_config()
    secrets_config = config.get("secrets", {})

    backend_name = secrets_config.get("backend", "pass")

    if backend_name == "pass":
        pass_config = secrets_config.get("pass", {})

        return PassBackend(
            paths=pass_config.get("paths", DEFAULT_PASS_PATHS)
        )

    if backend_name == "secretservice":
        secretservice_config = secrets_config.get(
            "secretservice",
            {},
        )

        return SecretServiceBackend(
            service=secretservice_config.get(
                "service",
                "kabutam",
            )
        )

    raise RuntimeError(
        f"未知のsecret backendです: {backend_name!r}. "
        "利用可能なbackend: pass, secretservice"
    )


def get_secret(name: str) -> str:
    """Retrieve a secret using the configured backend."""
    backend = get_secret_backend()
    return backend.get(name)


@functools.lru_cache(maxsize=1)
def get_edinet_api_key() -> str:
    return get_secret("EDNET_DB_API_KEY")


@functools.lru_cache(maxsize=1)
def get_jquants_api_key() -> str:
    return get_secret("JPX_JQUANTS_API_KEY")


def get_color_scheme() -> str:
    config = load_config()

    display_config = config.get("display", {})
    scheme = display_config.get("color_scheme", "japan")

    if scheme not in ("japan", "western", "none"):
        raise RuntimeError(
            f"未知のcolor_schemeです: {scheme!r}. "
            "利用可能なcolor_scheme: japan, western, none"
        )

    return scheme
