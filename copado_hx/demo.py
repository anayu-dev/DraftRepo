from __future__ import annotations

import asyncio

from copado_hx.lib.config import ConfigManager, CopadoProfile
from copado_hx.lib.mock_api import MockCopadoAPI
from copado_hx.utils.output import print_story_table, print_success


DEMO_PROFILE_NAME = "demo"


def activate_demo_profile() -> None:
    profile = CopadoProfile(name=DEMO_PROFILE_NAME, demo=True)
    ConfigManager().save_profile(profile, make_active=True)
    print_success("Demo profile activated. Try: copado-hx story list")


def show_demo_stories() -> None:
    stories = asyncio.run(MockCopadoAPI().list_stories())
    print_story_table(stories)
