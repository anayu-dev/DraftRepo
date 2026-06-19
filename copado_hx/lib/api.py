from __future__ import annotations

from typing import Any, Optional, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field

from .config import ConfigManager


API_PREFIX = "/services/apexrest/copado-hx/v1"


class CopadoAPIError(RuntimeError):
    """Raised when the Copado API returns an error response."""


class OperationResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    status: str
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class UserStory(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    key: str
    name: str
    status: str
    source_org: Optional[str] = None
    target_org: Optional[str] = None
    release: Optional[str] = None


class CopadoAPI(Protocol):
    async def list_stories(self, status: Optional[str] = None) -> list[UserStory]:
        ...

    async def get_story(self, story_id: str) -> UserStory:
        ...

    async def commit_story(
        self,
        story_id: str,
        message: str,
        include_metadata: bool = True,
    ) -> OperationResult:
        ...

    async def promote_story(
        self,
        story_id: str,
        target_environment: str,
        dry_run: bool = False,
    ) -> OperationResult:
        ...

    async def validate_story(self, story_id: str, target_environment: str) -> OperationResult:
        ...

    async def deploy_story(
        self,
        story_id: str,
        target_environment: str,
        deployment_id: Optional[str] = None,
    ) -> OperationResult:
        ...

    async def deployment_status(self, deployment_id: str) -> OperationResult:
        ...

    async def pipeline_status(self, story_id: Optional[str] = None) -> list[OperationResult]:
        ...


class CopadoAPIClient:
    """Async REST client for Copado CI/CD actions."""

    def __init__(
        self,
        base_url: str,
        api_token: str,
        timeout: float = 30.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = timeout
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "CopadoAPIClient":
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._client and self._owns_client:
            await self._client.aclose()
        self._client = None

    async def list_stories(self, status: Optional[str] = None) -> list[UserStory]:
        params = {"status": status} if status else None
        payload = await self._request("GET", "/user-stories", params=params)
        items = payload.get("stories", payload if isinstance(payload, list) else [])
        return [UserStory.model_validate(item) for item in items]

    async def get_story(self, story_id: str) -> UserStory:
        payload = await self._request("GET", f"/user-stories/{story_id}")
        return UserStory.model_validate(payload)

    async def commit_story(
        self,
        story_id: str,
        message: str,
        include_metadata: bool = True,
    ) -> OperationResult:
        payload = await self._request(
            "POST",
            f"/user-stories/{story_id}/commit",
            json={"message": message, "include_metadata": include_metadata},
        )
        return OperationResult.model_validate(payload)

    async def promote_story(
        self,
        story_id: str,
        target_environment: str,
        dry_run: bool = False,
    ) -> OperationResult:
        payload = await self._request(
            "POST",
            f"/user-stories/{story_id}/promote",
            json={"target_environment": target_environment, "dry_run": dry_run},
        )
        return OperationResult.model_validate(payload)

    async def validate_story(self, story_id: str, target_environment: str) -> OperationResult:
        payload = await self._request(
            "POST",
            f"/user-stories/{story_id}/validate",
            json={"target_environment": target_environment},
        )
        return OperationResult.model_validate(payload)

    async def deploy_story(
        self,
        story_id: str,
        target_environment: str,
        deployment_id: Optional[str] = None,
    ) -> OperationResult:
        payload = await self._request(
            "POST",
            f"/user-stories/{story_id}/deploy",
            json={
                "target_environment": target_environment,
                "deployment_id": deployment_id,
            },
        )
        return OperationResult.model_validate(payload)

    async def deployment_status(self, deployment_id: str) -> OperationResult:
        payload = await self._request("GET", f"/deployments/{deployment_id}")
        return OperationResult.model_validate(payload)

    async def pipeline_status(self, story_id: Optional[str] = None) -> list[OperationResult]:
        params = {"story_id": story_id} if story_id else None
        payload = await self._request("GET", "/pipeline/status", params=params)
        items = payload.get("items", payload if isinstance(payload, list) else [])
        return [OperationResult.model_validate(item) for item in items]

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        client = await self._ensure_client()
        url = f"{self.base_url}{API_PREFIX}{path}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.api_token}"
        headers["Accept"] = "application/json"
        if method.upper() in {"POST", "PUT", "PATCH"}:
            headers["Content-Type"] = "application/json"
        response = await client.request(method, url, headers=headers, **kwargs)
        if response.status_code >= 400:
            raise CopadoAPIError(self._error_message(response))
        if not response.content:
            return {}
        return response.json()

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
            message = payload.get("message") or payload.get("error") or str(payload)
        except ValueError:
            message = response.text
        return f"Copado API request failed ({response.status_code}): {message}"


def build_api(config: ConfigManager, profile_name: Optional[str] = None) -> CopadoAPI:
    credentials = config.get_credentials(profile_name)
    if credentials.profile.demo:
        from .mock_api import MockCopadoAPI

        return MockCopadoAPI()
    return CopadoAPIClient(credentials.profile.base_url, credentials.api_token)
