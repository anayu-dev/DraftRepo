from __future__ import annotations

import asyncio

from copado_hx.lib.mock_api import MockCopadoAPI


def test_mock_api_lists_commits_and_reports_pipeline_status() -> None:
    asyncio.run(_assert_mock_api_lists_commits_and_reports_pipeline_status())


async def _assert_mock_api_lists_commits_and_reports_pipeline_status() -> None:
    api = MockCopadoAPI()

    stories = await api.list_stories()
    assert {story.id for story in stories} >= {"US-001", "US-002", "US-003"}

    commit = await api.commit_story("US-001", "Commit from test")
    assert commit.status == "Succeeded"
    assert commit.data["story_id"] == "US-001"

    story = await api.get_story("US-001")
    assert story.status == "Committed"

    operations = await api.pipeline_status("US-001")
    assert [operation.id for operation in operations] == [commit.id]


def test_mock_api_validate_and_deploy() -> None:
    asyncio.run(_assert_mock_api_validate_and_deploy())


async def _assert_mock_api_validate_and_deploy() -> None:
    api = MockCopadoAPI()

    validation = await api.validate_story("US-002", "uat")
    deployment = await api.deploy_story("US-002", "uat", deployment_id=validation.id)

    assert validation.status == "Succeeded"
    assert deployment.status == "Succeeded"
    assert deployment.data["deployment_id"] == validation.id

    story = await api.get_story("US-002")
    assert story.status == "Deployed"
    assert story.target_org == "uat"
