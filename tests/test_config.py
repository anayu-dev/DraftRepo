from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

from copado_hx.lib.config import ConfigManager, ConfigurationError, CopadoProfile


class MemorySecrets:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.values: dict[tuple[str, str], str] = {}

    def set_password(self, service_name: str, username: str, password: str) -> None:
        if self.fail:
            raise RuntimeError("no keyring")
        self.values[(service_name, username)] = password

    def get_password(self, service_name: str, username: str) -> Optional[str]:
        if self.fail:
            raise RuntimeError("no keyring")
        return self.values.get((service_name, username))

    def delete_password(self, service_name: str, username: str) -> None:
        if self.fail:
            raise RuntimeError("no keyring")
        self.values.pop((service_name, username), None)


def test_save_and_load_demo_profile(tmp_path: Path) -> None:
    manager = ConfigManager(config_dir=tmp_path, secret_backend=MemorySecrets())
    manager.save_profile(CopadoProfile(name="demo", demo=True))

    profile = manager.get_profile()

    assert profile.name == "demo"
    assert profile.demo is True
    assert manager.metadata_path.exists()
    assert b"demo" not in manager.metadata_path.read_bytes()


def test_token_uses_encrypted_fallback_when_keyring_unavailable(tmp_path: Path) -> None:
    manager = ConfigManager(config_dir=tmp_path, secret_backend=MemorySecrets(fail=True))
    manager.save_profile(
        CopadoProfile(name="default", base_url="https://copado.example.com"),
        api_token="secret-token",
    )

    credentials = manager.get_credentials()

    assert credentials.api_token == "secret-token"
    assert b"secret-token" not in manager.metadata_path.read_bytes()


def test_missing_profile_raises_configuration_error(tmp_path: Path) -> None:
    manager = ConfigManager(config_dir=tmp_path, secret_backend=MemorySecrets())

    with pytest.raises(ConfigurationError):
        manager.get_profile()
