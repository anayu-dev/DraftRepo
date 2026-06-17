# copado-hx

`copado-hx` is an open source Python CLI that lets Salesforce developers run a
Copado Source Format lifecycle from the terminal. It orchestrates installed
Salesforce CLI (`sf`) and Copado CLI plugin (`sf copado ...`) commands without
requiring browser interaction after a Copado user story has been created.

## What it does

- Initializes project config with `.copado-hx.ini`
- Checks local prerequisites with `doctor`
- Authenticates Salesforce with JWT/no-browser auth
- Links the authenticated org to Copado CLI
- Retrieves, validates, deploys, previews, and converts Salesforce source format
- Sets, displays, lists, pushes, and submits Copado user stories
- Checks Copado jobs, environments, repos, and pipelines
- Runs a full terminal lifecycle:
  story binding -> optional retrieve -> validation -> optional commit -> Git push
  -> Copado push -> optional validate/promote/deploy submit
- Supports `--dry-run` so teams can inspect generated commands safely
- Includes raw pass-through commands for Copado plugin features that move faster
  than this wrapper

Copado user story creation remains in Copado/Salesforce UI; after that, normal
developer work can happen from the terminal.

## Requirements

- Python 3.10+
- Git
- Salesforce CLI v2 (`sf`)
- Copado CLI plugin:

```bash
sf plugins install @copado/copado-cli
```

or through this tool:

```bash
copado-hx copado install-plugin
```

## Install from source

```bash
python3 -m pip install -e .
copado-hx --version
```

## Project setup

Run this at the root of a Salesforce DX project:

```bash
copado-hx init \
  --target-org dev-sandbox \
  --copado-username copado-admin@example.com \
  --source-dir force-app \
  --base-branch main
```

You can override config with environment variables:

- `COPADO_HX_TARGET_ORG`
- `COPADO_HX_COPADO_USERNAME`
- `COPADO_HX_USER_STORY`

## No-browser auth flow

Use JWT auth for Salesforce:

```bash
copado-hx auth jwt \
  --username dev@example.com \
  --client-id "$SF_CLIENT_ID" \
  --jwt-key-file server.key \
  --instance-url https://test.salesforce.com \
  --alias dev-sandbox \
  --set-default
```

Then link the authenticated org to Copado CLI:

```bash
copado-hx auth copado --username copado-admin@example.com
copado-hx auth status
```

## Common lifecycle

Set the user story that was created in Copado:

```bash
copado-hx story set --story US-000123 --base-branch main
```

Retrieve source format from the development org:

```bash
copado-hx sf retrieve --target-org dev-sandbox --source-dir force-app
```

Validate the source format:

```bash
copado-hx sf validate --target-org dev-sandbox --test-level RunLocalTests
```

Commit and push:

```bash
copado-hx git commit -m "US-000123 update account automation"
copado-hx git push
```

Push metadata to Copado:

```bash
copado-hx story push --strategy scoped
```

Submit the user story:

```bash
copado-hx story submit --validate --wait
copado-hx story submit --promote --wait
copado-hx story submit --deploy --wait
```

## One-command lifecycle

```bash
copado-hx lifecycle run \
  --story US-000123 \
  --target-org dev-sandbox \
  --retrieve \
  --message "US-000123 update account automation" \
  --submit-validate \
  --wait
```

This runs:

1. `sf copado story set ...`
2. `sf project retrieve start ...` when `--retrieve` is provided
3. `sf project deploy validate ...` unless `--skip-validate` is provided
4. `git add` and `git commit` when `--message` is provided
5. `git push -u origin <current-branch>` unless `--skip-git-push` is provided
6. `sf copado story push --strategy scoped` unless `--skip-copado-push` is provided
7. `sf copado story submit ...` when a submit flag is provided

Preview commands before executing them:

```bash
copado-hx --dry-run lifecycle run \
  --story US-000123 \
  --target-org dev-sandbox \
  --retrieve \
  --message "US-000123 update account automation" \
  --submit-validate \
  --wait
```

## Useful command groups

```bash
copado-hx doctor
copado-hx sf preview --target-org dev-sandbox
copado-hx sf deploy --target-org qa --manifest manifest/package.xml
copado-hx sf quick-deploy --job-id 0Af...
copado-hx story display
copado-hx story list --listview "Cli Listview"
copado-hx job get --job-id a1B...
copado-hx copado env-list
copado-hx copado repo-list
copado-hx copado pipeline-list
```

## Pass-through commands

When Salesforce CLI or Copado CLI adds a command before `copado-hx` wraps it,
use raw pass-through:

```bash
copado-hx sf raw -- org display --target-org dev-sandbox
copado-hx copado raw -- package list
copado-hx story raw -- list --json
copado-hx git raw -- log --oneline -5
```

## Development

```bash
python3 -m unittest discover -s tests
python3 -m compileall src tests
```

The test suite uses fake command runners; it does not require real Salesforce or
Copado credentials.
