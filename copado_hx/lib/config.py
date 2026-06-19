from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional, Protocol

import keyring
from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, ConfigDict, Field, field_validator


APP_NAME = "copado-hx"
KEYRING_SERVICE = "copado-hx"


class ConfigurationError(RuntimeError):
    """Raised when copado-hx cannot load a usable profile."""


class SecretBackend(Protocol):
    def set_password(self, service_name: str, username: str, password: str) -> None:
        ...

    def get_password(self, service_name: str, username: str) -> Optional[str]:
        ...

    def delete_password(self, service_name: str, username: str) -> None:
        ...


class CopadoProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    base_url: str = "mock://copado"
    username: Optional[str] = None
    org_id: Optional[str] = None
    demo: bool = False

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("profile name cannot be empty")
        return cleaned

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        cleaned = value.strip().rstrip("/")
        if cleaned == "mock://copado":
            return cleaned
        if not cleaned.startswith(("https://", "http://")):
            raise ValueError("base_url must start with http:// or https://")
        return cleaned


class CopadoCredentials(BaseModel):
    profile: CopadoProfile
    api_token: str


class MetadataFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_profile: Optional[str] = None
    profiles: dict[str, CopadoProfile] = Field(default_factory=dict)
    encrypted_secret_fallbacks: dict[str, str] = Field(default_factory=dict)


class ConfigManager:
    """Reads encrypted metadata and stores API tokens through keyring.

    Some headless environments do not expose a usable OS keyring. In that case
    tokens are stored inside the same encrypted metadata file as a fallback.
    """

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        secret_backend: SecretBackend = keyring,
    ) -> None:
        self.config_dir = Path(config_dir) if config_dir else self.default_config_dir()
        self.secret_backend = secret_backend
        self.key_path = self.config_dir / "metadata.key"
        self.metadata_path = self.config_dir / "metadata.enc"

    @staticmethod
    def default_config_dir() -> Path:
        configured = os.environ.get("COPADO_HX_CONFIG_DIR")
        if configured:
            return Path(configured).expanduser()
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config).expanduser() / APP_NAME
        return Path.home() / ".config" / APP_NAME

    def load(self) -> MetadataFile:
        if not self.metadata_path.exists():
            return MetadataFile()
        fernet = self._fernet()
        try:
            encrypted = self.metadata_path.read_bytes()
            decrypted = fernet.decrypt(encrypted)
        except (InvalidToken, OSError) as exc:
            raise ConfigurationError("Unable to decrypt copado-hx metadata") from exc
        return MetadataFile.model_validate_json(decrypted)

    def save(self, metadata: MetadataFile) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        fernet = self._fernet()
        payload = metadata.model_dump_json().encode("utf-8")
        self.metadata_path.write_bytes(fernet.encrypt(payload))
        self._chmod_private(self.metadata_path)

    def save_profile(
        self,
        profile: CopadoProfile,
        api_token: Optional[str] = None,
        make_active: bool = True,
    ) -> None:
        metadata = self.load()
        metadata.profiles[profile.name] = profile
        if make_active:
            metadata.active_profile = profile.name
        if api_token:
            stored_in_keyring = self._try_set_secret(profile.name, api_token)
            if stored_in_keyring:
                metadata.encrypted_secret_fallbacks.pop(profile.name, None)
            else:
                metadata.encrypted_secret_fallbacks[profile.name] = api_token
        self.save(metadata)

    def set_active_profile(self, profile_name: str) -> CopadoProfile:
        metadata = self.load()
        if profile_name not in metadata.profiles:
            raise ConfigurationError(f"Profile '{profile_name}' does not exist")
        metadata.active_profile = profile_name
        self.save(metadata)
        return metadata.profiles[profile_name]

    def get_profile(self, profile_name: Optional[str] = None) -> CopadoProfile:
        metadata = self.load()
        selected = profile_name or metadata.active_profile
        if not selected:
            raise ConfigurationError("No active profile. Run 'copado-hx auth login'.")
        try:
            return metadata.profiles[selected]
        except KeyError as exc:
            raise ConfigurationError(f"Profile '{selected}' does not exist") from exc

    def get_credentials(self, profile_name: Optional[str] = None) -> CopadoCredentials:
        profile = self.get_profile(profile_name)
        if profile.demo:
            return CopadoCredentials(profile=profile, api_token="demo-token")
        token = self._get_secret(profile.name)
        if not token:
            raise ConfigurationError(
                f"Profile '{profile.name}' has no API token. Run 'copado-hx auth login'."
            )
        return CopadoCredentials(profile=profile, api_token=token)

    def list_profiles(self) -> list[CopadoProfile]:
        metadata = self.load()
        return sorted(metadata.profiles.values(), key=lambda profile: profile.name)

    def delete_profile(self, profile_name: str) -> None:
        metadata = self.load()
        if profile_name not in metadata.profiles:
            raise ConfigurationError(f"Profile '{profile_name}' does not exist")
        metadata.profiles.pop(profile_name)
        metadata.encrypted_secret_fallbacks.pop(profile_name, None)
        if metadata.active_profile == profile_name:
            metadata.active_profile = next(iter(metadata.profiles), None)
        self._try_delete_secret(profile_name)
        self.save(metadata)

    def _fernet(self) -> Fernet:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if not self.key_path.exists():
            self.key_path.write_bytes(Fernet.generate_key())
            self._chmod_private(self.key_path)
        return Fernet(self.key_path.read_bytes())

    def _try_set_secret(self, profile_name: str, api_token: str) -> bool:
        try:
            self.secret_backend.set_password(KEYRING_SERVICE, self._secret_name(profile_name), api_token)
            return True
        except Exception:
            return False

    def _get_secret(self, profile_name: str) -> Optional[str]:
        try:
            token = self.secret_backend.get_password(KEYRING_SERVICE, self._secret_name(profile_name))
            if token:
                return token
        except Exception:
            pass
        metadata = self.load()
        return metadata.encrypted_secret_fallbacks.get(profile_name)

    def _try_delete_secret(self, profile_name: str) -> None:
        try:
            self.secret_backend.delete_password(KEYRING_SERVICE, self._secret_name(profile_name))
        except Exception:
            pass

    @staticmethod
    def _secret_name(profile_name: str) -> str:
        return f"{profile_name}:api-token"

    @staticmethod
    def _chmod_private(path: Path) -> None:
        try:
            path.chmod(0o600)
        except OSError:
            pass

    def export_debug_json(self) -> str:
        metadata = self.load()
        safe = metadata.model_dump()
        safe["encrypted_secret_fallbacks"] = {
            key: "[encrypted]" for key in safe["encrypted_secret_fallbacks"]
        }
        return json.dumps(safe, indent=2, sort_keys=True)
