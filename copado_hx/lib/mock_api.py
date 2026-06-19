from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

from .api import OperationResult, UserStory


class MockCopadoAPI:
    """Deterministic Copado API for demos and tests.

    When a state path is provided, mock operations persist between CLI
    invocations so demo mode behaves like a small local sandbox.
    """

    def __init__(self, state_path: Optional[Path] = None) -> None:
        self.state_path = state_path
        self.next_id = 1001
        if state_path and state_path.exists():
            self._load_state(state_path)
            return
        self._load_default_state()

    def _load_default_state(self) -> None:
        self.stories: dict[str, UserStory] = {
            "US-001": UserStory(
                id="US-001",
                key="US-001",
                name="Add account matching validation",
                status="Ready to Commit",
                source_org="dev-a",
                target_org="integration",
                release="Spring Demo",
            ),
            "US-002": UserStory(
                id="US-002",
                key="US-002",
                name="Refactor lead assignment flow",
                status="Committed",
                source_org="dev-b",
                target_org="uat",
                release="Spring Demo",
            ),
            "US-003": UserStory(
                id="US-003",
                key="US-003",
                name="Prepare production hotfix",
                status="Validated",
                source_org="uat",
                target_org="production",
                release="Hotfix",
            ),
        }
        self.operations: dict[str, OperationResult] = {}

    async def list_stories(self, status: Optional[str] = None) -> list[UserStory]:
        await self._latency()
        stories = list(self.stories.values())
        if status:
            stories = [story for story in stories if story.status.lower() == status.lower()]
        return stories

    async def get_story(self, story_id: str) -> UserStory:
        await self._latency()
        return self._story(story_id)

    async def commit_story(
        self,
        story_id: str,
        message: str,
        include_metadata: bool = True,
    ) -> OperationResult:
        await self._latency()
        story = self._story(story_id)
        updated = story.model_copy(update={"status": "Committed"})
        self.stories[story.id] = updated
        operation = self._operation(
            "commit",
            "Succeeded",
            f"Committed {story.key}: {message}",
            {"story_id": story.id, "include_metadata": include_metadata},
        )
        self._save_state()
        return operation

    async def promote_story(
        self,
        story_id: str,
        target_environment: str,
        dry_run: bool = False,
    ) -> OperationResult:
        await self._latency()
        story = self._story(story_id)
        status = "DryRunSucceeded" if dry_run else "Promoted"
        if not dry_run:
            self.stories[story.id] = story.model_copy(
                update={"status": "Promoted", "target_org": target_environment}
            )
        operation = self._operation(
            "promote",
            status,
            f"Promote {story.key} to {target_environment}",
            {"story_id": story.id, "target_environment": target_environment, "dry_run": dry_run},
        )
        self._save_state()
        return operation

    async def validate_story(self, story_id: str, target_environment: str) -> OperationResult:
        await self._latency()
        story = self._story(story_id)
        self.stories[story.id] = story.model_copy(
            update={"status": "Validated", "target_org": target_environment}
        )
        operation = self._operation(
            "validate",
            "Succeeded",
            f"Validated {story.key} against {target_environment}",
            {"story_id": story.id, "target_environment": target_environment},
        )
        self._save_state()
        return operation

    async def deploy_story(
        self,
        story_id: str,
        target_environment: str,
        deployment_id: Optional[str] = None,
    ) -> OperationResult:
        await self._latency()
        story = self._story(story_id)
        operation = self._operation(
            "deploy",
            "Succeeded",
            f"Deployed {story.key} to {target_environment}",
            {
                "story_id": story.id,
                "target_environment": target_environment,
                "deployment_id": deployment_id,
            },
        )
        self.stories[story.id] = story.model_copy(
            update={"status": "Deployed", "target_org": target_environment}
        )
        self._save_state()
        return operation

    async def deployment_status(self, deployment_id: str) -> OperationResult:
        await self._latency()
        return self.operations.get(
            deployment_id,
            OperationResult(
                id=deployment_id,
                status="Unknown",
                message="No matching mock deployment found",
                data={},
            ),
        )

    async def pipeline_status(self, story_id: Optional[str] = None) -> list[OperationResult]:
        await self._latency()
        operations = list(self.operations.values())
        if story_id:
            operations = [
                operation
                for operation in operations
                if operation.data.get("story_id", "").lower() == story_id.lower()
            ]
        return operations

    def _story(self, story_id: str) -> UserStory:
        story = self.stories.get(story_id.upper())
        if not story:
            raise KeyError(f"Mock user story '{story_id}' does not exist")
        return story

    def _operation(
        self,
        prefix: str,
        status: str,
        message: str,
        data: dict[str, object],
    ) -> OperationResult:
        operation = OperationResult(
            id=f"{prefix}-{self.next_id}",
            status=status,
            message=message,
            data=data,
        )
        self.next_id += 1
        self.operations[operation.id] = operation
        return operation

    def _load_state(self, state_path: Path) -> None:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        self.next_id = int(payload.get("next_id", 1001))
        self.stories = {
            story["id"]: UserStory.model_validate(story)
            for story in payload.get("stories", [])
        }
        self.operations = {
            operation["id"]: OperationResult.model_validate(operation)
            for operation in payload.get("operations", [])
        }
        if not self.stories:
            self._load_default_state()

    def _save_state(self) -> None:
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "next_id": self.next_id,
            "stories": [story.model_dump() for story in self.stories.values()],
            "operations": [operation.model_dump() for operation in self.operations.values()],
        }
        self.state_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    async def _latency() -> None:
        await asyncio.sleep(0)
