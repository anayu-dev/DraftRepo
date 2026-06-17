"""Command-line interface for Copado HX."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import shutil
import sys
from typing import Callable, Sequence, TextIO

from . import __version__
from .config import HxConfig, load_config, require_value, write_default_config
from .copado import CopadoCli
from .errors import CommandExecutionError, CopadoHxError
from .gitops import GitCli
from .runner import CommandRunner
from .salesforce import SalesforceCli, ensure_salesforce_project
from .workflow import Lifecycle, LifecycleOptions


Handler = Callable[["Context", argparse.Namespace], int | None]


@dataclass
class Context:
    config: HxConfig
    config_path: Path | None
    runner: CommandRunner
    stdout: TextIO
    stderr: TextIO

    @property
    def sf(self) -> SalesforceCli:
        return SalesforceCli(self.runner, self.config)

    @property
    def copado(self) -> CopadoCli:
        return CopadoCli(self.runner, self.config)

    @property
    def git(self) -> GitCli:
        return GitCli(self.runner, self.config)


def entrypoint() -> None:
    raise SystemExit(main())


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: CommandRunner | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        active_runner = runner or CommandRunner(dry_run=args.dry_run, verbose=args.verbose, stdout=out, stderr=err)
        context = Context(HxConfig(), None, active_runner, out, err)
    else:
        try:
            config, config_path = load_config(args.config)
        except CopadoHxError as exc:
            print(f"copado-hx: {exc}", file=err)
            return 2
        active_runner = runner or CommandRunner(dry_run=args.dry_run, verbose=args.verbose, stdout=out, stderr=err)
        context = Context(config, config_path, active_runner, out, err)

    handler: Handler | None = getattr(args, "handler", None)
    if not handler:
        parser.print_help(out)
        return 2

    try:
        return handler(context, args) or 0
    except (CommandExecutionError, CopadoHxError) as exc:
        print(f"copado-hx: {exc}", file=err)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="copado-hx",
        description="Terminal-first Copado Source Format lifecycle CLI.",
    )
    parser.add_argument("--version", action="version", version=f"copado-hx {__version__}")
    parser.add_argument("--config", help="Path to .copado-hx.ini (defaults to nearest parent config).")
    parser.add_argument("--dry-run", action="store_true", help="Print external commands without executing them.")
    parser.add_argument("--verbose", action="store_true", help="Print external commands before executing them.")

    sub = parser.add_subparsers(dest="command")

    init = sub.add_parser("init", help="Create a starter .copado-hx.ini config file.")
    init.add_argument("--path", default=".copado-hx.ini", help="Config path to write.")
    init.add_argument("--force", action="store_true", help="Overwrite an existing config file.")
    init.add_argument("--source-dir", default="force-app", help="Salesforce source-format directory.")
    init.add_argument("--target-org", default="", help="Default Salesforce target org username or alias.")
    init.add_argument("--copado-username", default="", help="Salesforce username for the Copado org.")
    init.add_argument("--user-story", default="", help="Default Copado user story name.")
    init.add_argument("--base-branch", default="main", help="Default Copado base branch.")
    init.set_defaults(handler=handle_init)

    doctor = sub.add_parser("doctor", help="Check local Salesforce/Copado prerequisites.")
    doctor.set_defaults(handler=handle_doctor)

    auth = sub.add_parser("auth", help="Authenticate Salesforce and link Copado CLI.")
    auth_sub = auth.add_subparsers(dest="auth_command", required=True)
    jwt = auth_sub.add_parser("jwt", help="Login to Salesforce with JWT/no-browser auth.")
    jwt.add_argument("--username", required=True)
    jwt.add_argument("--client-id", required=True)
    jwt.add_argument("--jwt-key-file", required=True)
    jwt.add_argument("--instance-url")
    jwt.add_argument("--alias")
    jwt.add_argument("--set-default", action="store_true")
    jwt.set_defaults(handler=handle_auth_jwt)
    copado_auth = auth_sub.add_parser("copado", help="Link an authenticated Salesforce org to Copado CLI.")
    copado_auth.add_argument("--username", help="Salesforce username of the Copado org.")
    copado_auth.add_argument("--alias", help="Salesforce alias of the Copado org.")
    copado_auth.set_defaults(handler=handle_auth_copado)
    status = auth_sub.add_parser("status", help="Show current Copado CLI auth.")
    status.add_argument("--json", action="store_true")
    status.set_defaults(handler=handle_auth_status)
    setup = auth_sub.add_parser("setup", help="Run Copado CLI setup.")
    setup.add_argument("args", nargs=argparse.REMAINDER, help="Extra args passed to sf copado setup.")
    setup.set_defaults(handler=handle_auth_setup)

    sf = sub.add_parser("sf", help="Salesforce source-format operations.")
    sf_sub = sf.add_subparsers(dest="sf_command", required=True)
    _add_retrieve(sf_sub)
    _add_deploy(sf_sub, "deploy", validate_only=False)
    _add_deploy(sf_sub, "validate", validate_only=True)
    quick = sf_sub.add_parser("quick-deploy", help="Run sf project deploy quick.")
    quick.add_argument("--job-id", required=True)
    quick.add_argument("--target-org")
    quick.add_argument("--wait", type=int)
    quick.set_defaults(handler=handle_sf_quick_deploy)
    preview = sf_sub.add_parser("preview", help="Preview a source-format deployment.")
    preview.add_argument("--target-org")
    preview.add_argument("--source-dir")
    preview.set_defaults(handler=handle_sf_preview)
    conv_source = sf_sub.add_parser("convert-source", help="Convert Salesforce source format to Metadata API format.")
    conv_source.add_argument("--root-dir")
    conv_source.add_argument("--output-dir")
    conv_source.set_defaults(handler=handle_sf_convert_source)
    conv_mdapi = sf_sub.add_parser("convert-mdapi", help="Convert Metadata API format to Salesforce source format.")
    conv_mdapi.add_argument("--root-dir")
    conv_mdapi.add_argument("--output-dir")
    conv_mdapi.set_defaults(handler=handle_sf_convert_mdapi)
    org_list = sf_sub.add_parser("org-list", help="List Salesforce orgs.")
    org_list.add_argument("--all", action="store_true")
    org_list.set_defaults(handler=handle_sf_org_list)
    sf_raw = sf_sub.add_parser("raw", help="Pass arguments directly to sf.")
    sf_raw.add_argument("args", nargs=argparse.REMAINDER)
    sf_raw.set_defaults(handler=handle_sf_raw)

    copado = sub.add_parser("copado", help="Copado plugin resource operations.")
    copado_sub = copado.add_subparsers(dest="copado_command", required=True)
    install = copado_sub.add_parser("install-plugin", help="Install @copado/copado-cli into Salesforce CLI.")
    install.set_defaults(handler=handle_copado_install)
    for name, handler in (("env-list", handle_copado_env_list), ("repo-list", handle_copado_repo_list), ("pipeline-list", handle_copado_pipeline_list)):
        resource = copado_sub.add_parser(name, help=f"Run sf copado {name.replace('-', ' ')}.")
        resource.add_argument("--json", action="store_true")
        resource.set_defaults(handler=handler)
    raw_copado = copado_sub.add_parser("raw", help="Pass arguments directly to sf copado.")
    raw_copado.add_argument("args", nargs=argparse.REMAINDER)
    raw_copado.set_defaults(handler=handle_copado_raw)

    story = sub.add_parser("story", help="Copado user-story operations.")
    story_sub = story.add_subparsers(dest="story_command", required=True)
    story_set = story_sub.add_parser("set", help="Bind this repo to a Copado user story and checkout its feature branch.")
    group = story_set.add_mutually_exclusive_group()
    group.add_argument("--story", "-s", help="Copado user story name, for example US-000123.")
    group.add_argument("--id", dest="story_id", help="Salesforce record id for the Copado user story.")
    group.add_argument("--external-id", "-e", help="Configured external id value.")
    story_set.add_argument("--base-branch", "-b")
    story_set.add_argument("--credential", "-c")
    story_set.add_argument("--auto-detect", action="store_true", help="Allow Copado CLI positional auto-detection.")
    story_set.set_defaults(handler=handle_story_set)
    display = story_sub.add_parser("display", help="Display the current or selected Copado user story.")
    display.add_argument("--story", "-s")
    display.add_argument("--id", dest="story_id")
    display.add_argument("--json", action="store_true")
    display.set_defaults(handler=handle_story_display)
    story_list = story_sub.add_parser("list", help="List Copado user stories.")
    story_list.add_argument("--listview", "-l")
    story_list.add_argument("--query", "-q")
    story_list.add_argument("--json", action="store_true")
    story_list.set_defaults(handler=handle_story_list)
    push = story_sub.add_parser("push", help="Push committed metadata to Git, environment branch, and Copado.")
    push.add_argument("--force", action="store_true")
    push.add_argument("--strategy", choices=["full", "scoped"], default="scoped")
    push.set_defaults(handler=handle_story_push)
    submit = story_sub.add_parser("submit", help="Submit current user story for validate, promote, or deploy.")
    submit_action = submit.add_mutually_exclusive_group(required=True)
    submit_action.add_argument("--validate", action="store_true")
    submit_action.add_argument("--promote", action="store_true")
    submit_action.add_argument("--deploy", action="store_true")
    submit.add_argument("--wait", action="store_true")
    submit.set_defaults(handler=handle_story_submit)
    open_story = story_sub.add_parser("open", help="Open the current Copado user story in Salesforce.")
    open_story.set_defaults(handler=handle_story_open)
    story_raw = story_sub.add_parser("raw", help="Pass arguments directly to sf copado story.")
    story_raw.add_argument("args", nargs=argparse.REMAINDER)
    story_raw.set_defaults(handler=handle_story_raw)

    job = sub.add_parser("job", help="Copado job execution operations.")
    job_sub = job.add_subparsers(dest="job_command", required=True)
    job_get = job_sub.add_parser("get", help="Get Copado job status/details.")
    job_get.add_argument("--job-id", "-i", required=True)
    job_get.add_argument("--json", action="store_true")
    job_get.set_defaults(handler=handle_job_get)
    job_list = job_sub.add_parser("list", help="List Copado jobs.")
    job_list.add_argument("--json", action="store_true")
    job_list.set_defaults(handler=handle_job_list)

    git = sub.add_parser("git", help="Git helpers for source-format work.")
    git_sub = git.add_subparsers(dest="git_command", required=True)
    git_status = git_sub.add_parser("status", help="Run git status --short.")
    git_status.set_defaults(handler=handle_git_status)
    git_commit = git_sub.add_parser("commit", help="Add configured source paths and commit.")
    git_commit.add_argument("--message", "-m", required=True)
    git_commit.add_argument("paths", nargs="*")
    git_commit.set_defaults(handler=handle_git_commit)
    git_push = git_sub.add_parser("push", help="Push the current branch.")
    git_push.add_argument("--remote")
    git_push.add_argument("--branch")
    git_push.set_defaults(handler=handle_git_push)
    git_raw = git_sub.add_parser("raw", help="Pass arguments directly to git.")
    git_raw.add_argument("args", nargs=argparse.REMAINDER)
    git_raw.set_defaults(handler=handle_git_raw)

    lifecycle = sub.add_parser("lifecycle", help="Run an end-to-end Copado source-format lifecycle.")
    lifecycle_sub = lifecycle.add_subparsers(dest="lifecycle_command", required=True)
    run = lifecycle_sub.add_parser("run", help="Set story, retrieve, validate, commit, push, and optionally submit.")
    group = run.add_mutually_exclusive_group()
    group.add_argument("--story", "-s")
    group.add_argument("--id", dest="story_id")
    group.add_argument("--external-id", "-e")
    run.add_argument("--base-branch", "-b")
    run.add_argument("--credential", "-c")
    run.add_argument("--target-org")
    run.add_argument("--retrieve", action="store_true")
    run.add_argument("--skip-validate", action="store_true")
    run.add_argument("--test", dest="tests", action="append", default=[])
    run.add_argument("--message", "-m", dest="commit_message")
    run.add_argument("--path", dest="commit_paths", action="append", default=[])
    run.add_argument("--skip-git-push", action="store_true")
    run.add_argument("--skip-copado-push", action="store_true")
    submit_group = run.add_mutually_exclusive_group()
    submit_group.add_argument("--submit-validate", action="store_true")
    submit_group.add_argument("--submit-promote", action="store_true")
    submit_group.add_argument("--submit-deploy", action="store_true")
    run.add_argument("--wait", action="store_true")
    run.set_defaults(handler=handle_lifecycle_run)

    return parser


def handle_init(context: Context, args: argparse.Namespace) -> int:
    path = write_default_config(
        args.path,
        overwrite=args.force,
        source_dir=args.source_dir,
        target_org=args.target_org,
        copado_username=args.copado_username,
        user_story=args.user_story,
        base_branch=args.base_branch,
    )
    print(f"Wrote {path}", file=context.stdout)
    return 0


def handle_doctor(context: Context, _args: argparse.Namespace) -> int:
    print("Copado HX doctor", file=context.stdout)
    print(f"Config: {context.config_path or 'not found; defaults/env only'}", file=context.stdout)
    _print_check(context, "Salesforce CLI (sf)", shutil.which("sf") is not None)
    if shutil.which("sf") is not None or context.runner.dry_run:
        sf_version = context.sf.version()
        if sf_version.stdout.strip():
            print(f"  {sf_version.stdout.strip()}", file=context.stdout)
    _print_check(context, "Copado CLI plugin", context.runner.dry_run or _command_ok(context.copado.help()))
    _print_check(context, "Git", shutil.which("git") is not None)
    _print_check(context, "sfdx-project.json", ensure_salesforce_project())
    _print_check(context, f"source directory ({context.config.source_dir})", Path(context.config.source_dir).exists())
    if not context.config.target_org:
        print("WARN target org is not configured", file=context.stdout)
    if not context.config.copado_username:
        print("WARN Copado username is not configured", file=context.stdout)
    return 0


def handle_auth_jwt(context: Context, args: argparse.Namespace) -> int:
    context.sf.login_jwt(
        username=args.username,
        client_id=args.client_id,
        jwt_key_file=args.jwt_key_file,
        instance_url=args.instance_url,
        alias=args.alias,
        set_default=args.set_default,
    )
    return 0


def handle_auth_copado(context: Context, args: argparse.Namespace) -> int:
    if not args.username and not args.alias and not context.config.copado_username:
        raise CopadoHxError("Provide --username/--alias or configure [copado] username.")
    context.copado.auth_set(username=args.username or context.config.copado_username, alias=args.alias)
    return 0


def handle_auth_status(context: Context, args: argparse.Namespace) -> int:
    context.copado.auth_get(json=args.json)
    return 0


def handle_auth_setup(context: Context, args: argparse.Namespace) -> int:
    context.copado.setup(_strip_remainder(args.args))
    return 0


def handle_copado_install(context: Context, _args: argparse.Namespace) -> int:
    context.sf.plugin_install_copado()
    return 0


def handle_copado_env_list(context: Context, args: argparse.Namespace) -> int:
    context.copado.env_list(json=args.json)
    return 0


def handle_copado_repo_list(context: Context, args: argparse.Namespace) -> int:
    context.copado.repo_list(json=args.json)
    return 0


def handle_copado_pipeline_list(context: Context, args: argparse.Namespace) -> int:
    context.copado.pipeline_list(json=args.json)
    return 0


def handle_copado_raw(context: Context, args: argparse.Namespace) -> int:
    context.copado.passthrough(_strip_remainder(args.args))
    return 0


def handle_sf_retrieve(context: Context, args: argparse.Namespace) -> int:
    context.sf.retrieve(
        target_org=args.target_org,
        source_dir=args.source_dir,
        manifest=args.manifest,
        metadata=args.metadata,
        wait_minutes=args.wait,
    )
    return 0


def handle_sf_deploy(context: Context, args: argparse.Namespace) -> int:
    context.sf.deploy(
        validate_only=args.validate_only,
        target_org=args.target_org,
        source_dir=args.source_dir,
        manifest=args.manifest,
        test_level=args.test_level,
        tests=args.tests,
        wait_minutes=args.wait,
        ignore_conflicts=args.ignore_conflicts,
    )
    return 0


def handle_sf_quick_deploy(context: Context, args: argparse.Namespace) -> int:
    context.sf.quick_deploy(job_id=args.job_id, target_org=args.target_org, wait_minutes=args.wait)
    return 0


def handle_sf_preview(context: Context, args: argparse.Namespace) -> int:
    context.sf.preview(target_org=args.target_org, source_dir=args.source_dir)
    return 0


def handle_sf_convert_source(context: Context, args: argparse.Namespace) -> int:
    context.sf.convert_source(root_dir=args.root_dir, output_dir=args.output_dir)
    return 0


def handle_sf_convert_mdapi(context: Context, args: argparse.Namespace) -> int:
    context.sf.convert_mdapi(root_dir=args.root_dir, output_dir=args.output_dir)
    return 0


def handle_sf_org_list(context: Context, args: argparse.Namespace) -> int:
    context.sf.org_list(all_orgs=args.all)
    return 0


def handle_sf_raw(context: Context, args: argparse.Namespace) -> int:
    context.sf.passthrough(_strip_remainder(args.args))
    return 0


def handle_story_set(context: Context, args: argparse.Namespace) -> int:
    story = args.story or (context.config.user_story if not args.story_id and not args.external_id else None)
    if not story and not args.story_id and not args.external_id:
        raise CopadoHxError("Provide --story, --id, --external-id, or configure [copado] user_story.")
    context.copado.story_set(
        story=story,
        story_id=args.story_id,
        external_id=args.external_id,
        base_branch=args.base_branch,
        credential=args.credential,
        no_auto_detect=not args.auto_detect,
    )
    return 0


def handle_story_display(context: Context, args: argparse.Namespace) -> int:
    context.copado.story_display(story=args.story, story_id=args.story_id, json=args.json)
    return 0


def handle_story_list(context: Context, args: argparse.Namespace) -> int:
    context.copado.story_list(listview=args.listview, query=args.query, json=args.json)
    return 0


def handle_story_push(context: Context, args: argparse.Namespace) -> int:
    context.copado.story_push(force=args.force, strategy=args.strategy)
    return 0


def handle_story_submit(context: Context, args: argparse.Namespace) -> int:
    action = _submit_action(args)
    context.copado.story_submit(action=action, wait=args.wait)
    return 0


def handle_story_open(context: Context, _args: argparse.Namespace) -> int:
    context.copado.story_open()
    return 0


def handle_story_raw(context: Context, args: argparse.Namespace) -> int:
    context.copado.passthrough(["story", *_strip_remainder(args.args)])
    return 0


def handle_job_get(context: Context, args: argparse.Namespace) -> int:
    context.copado.job_get(job_id=args.job_id, json=args.json)
    return 0


def handle_job_list(context: Context, args: argparse.Namespace) -> int:
    context.copado.job_list(json=args.json)
    return 0


def handle_git_status(context: Context, _args: argparse.Namespace) -> int:
    context.git.status()
    return 0


def handle_git_commit(context: Context, args: argparse.Namespace) -> int:
    context.git.add(args.paths)
    context.git.commit(args.message)
    return 0


def handle_git_push(context: Context, args: argparse.Namespace) -> int:
    context.git.push(remote=args.remote, branch=args.branch)
    return 0


def handle_git_raw(context: Context, args: argparse.Namespace) -> int:
    context.git.passthrough(_strip_remainder(args.args))
    return 0


def handle_lifecycle_run(context: Context, args: argparse.Namespace) -> int:
    lifecycle = Lifecycle(context.sf, context.copado, context.git, context.config)
    lifecycle.run(
        LifecycleOptions(
            story=args.story,
            story_id=args.story_id,
            external_id=args.external_id,
            base_branch=args.base_branch,
            credential=args.credential,
            target_org=args.target_org,
            retrieve=args.retrieve,
            validate=not args.skip_validate,
            commit_message=args.commit_message,
            commit_paths=args.commit_paths,
            push_git=not args.skip_git_push,
            push_copado=not args.skip_copado_push,
            submit_action=_lifecycle_submit_action(args),
            wait=args.wait,
            tests=args.tests,
        )
    )
    return 0


def _add_retrieve(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    retrieve = sub.add_parser("retrieve", help="Retrieve source-format metadata from a Salesforce org.")
    retrieve.add_argument("--target-org")
    retrieve.add_argument("--source-dir")
    retrieve.add_argument("--manifest")
    retrieve.add_argument("--metadata", action="append", default=[])
    retrieve.add_argument("--wait", type=int)
    retrieve.set_defaults(handler=handle_sf_retrieve)


def _add_deploy(sub: argparse._SubParsersAction[argparse.ArgumentParser], name: str, *, validate_only: bool) -> None:
    deploy = sub.add_parser(name, help=("Validate" if validate_only else "Deploy") + " source-format metadata.")
    deploy.add_argument("--target-org")
    deploy.add_argument("--source-dir")
    deploy.add_argument("--manifest")
    deploy.add_argument("--test-level")
    deploy.add_argument("--test", dest="tests", action="append", default=[])
    deploy.add_argument("--wait", type=int)
    deploy.add_argument("--ignore-conflicts", action="store_true")
    deploy.set_defaults(handler=handle_sf_deploy, validate_only=validate_only)


def _print_check(context: Context, label: str, ok: bool) -> None:
    status = "OK" if ok else "MISSING"
    print(f"{status} {label}", file=context.stdout)


def _command_ok(result: object) -> bool:
    return bool(getattr(result, "returncode", 1) == 0)


def _strip_remainder(args: Sequence[str]) -> list[str]:
    values = list(args)
    if values and values[0] == "--":
        values = values[1:]
    return values


def _submit_action(args: argparse.Namespace) -> str:
    if args.validate:
        return "validate"
    if args.promote:
        return "promote"
    return "deploy"


def _lifecycle_submit_action(args: argparse.Namespace) -> str | None:
    if args.submit_validate:
        return "validate"
    if args.submit_promote:
        return "promote"
    if args.submit_deploy:
        return "deploy"
    return None
