"""High-level lifecycle orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .config import HxConfig
from .copado import CopadoCli, SubmitAction
from .gitops import GitCli
from .runner import CommandResult
from .salesforce import SalesforceCli


@dataclass(frozen=True)
class LifecycleOptions:
    """Options for ``copado-hx lifecycle run``."""

    story: str | None = None
    story_id: str | None = None
    external_id: str | None = None
    base_branch: str | None = None
    credential: str | None = None
    target_org: str | None = None
    retrieve: bool = False
    validate: bool = True
    commit_message: str | None = None
    commit_paths: Sequence[str] = ()
    push_git: bool = True
    push_copado: bool = True
    submit_action: SubmitAction | None = None
    wait: bool = False
    tests: Sequence[str] = ()


class Lifecycle:
    """Coordinate Salesforce, Git, and Copado CLI commands."""

    def __init__(self, sf: SalesforceCli, copado: CopadoCli, git: GitCli, config: HxConfig) -> None:
        self.sf = sf
        self.copado = copado
        self.git = git
        self.config = config

    def run(self, options: LifecycleOptions) -> list[CommandResult]:
        """Run a terminal-first source-format lifecycle."""

        results: list[CommandResult] = []
        if options.story or options.story_id or options.external_id or self.config.user_story:
            results.append(
                self.copado.story_set(
                    story=options.story or (self.config.user_story if not options.story_id and not options.external_id else None),
                    story_id=options.story_id,
                    external_id=options.external_id,
                    base_branch=options.base_branch or self.config.base_branch,
                    credential=options.credential,
                )
            )

        if options.retrieve:
            results.append(self.sf.retrieve(target_org=options.target_org))

        if options.validate:
            results.append(self.sf.deploy(validate_only=True, target_org=options.target_org, tests=options.tests))

        if options.commit_message:
            results.append(self.git.add(options.commit_paths))
            results.append(self.git.commit(options.commit_message))

        if options.push_git:
            results.append(self.git.push())

        if options.push_copado:
            results.append(self.copado.story_push(strategy="scoped"))

        if options.submit_action:
            results.append(self.copado.story_submit(action=options.submit_action, wait=options.wait))

        return results
