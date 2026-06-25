# copado-hx

`copado-hx` is a terminal-first Python CLI for Salesforce developers who want to
manage Copado DevOps lifecycle actions without browser UI interaction.

It provides command groups for:

- browserless authentication/profile management
- pulling and inspecting Copado user stories
- committing user stories
- promoting user stories
- validating deployments
- deploying user stories
- checking deployment and pipeline status
- demo mode through a mock Copado API layer

## Install

`copado-hx` supports Python 3.10 and newer, including Python 3.14. To create a
Python 3.14 virtual environment explicitly:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

```bash
python -m pip install .
```

For local development:

```bash
python -m pip install -e ".[dev]"
pytest
```

## Quick start with demo mode

Demo mode requires no real Copado credentials and never calls the network.

```bash
copado-hx demo
copado-hx story list
copado-hx story show US-001
copado-hx commit story US-001 --message "Commit validation changes"
copado-hx deploy validate US-001 --target uat
copado-hx promote story US-001 --target uat
copado-hx deploy story US-001 --target uat
```

## Configure a real Copado profile

`copado-hx` is designed for token-based terminal authentication. It does not
open a browser tab.

```bash
copado-hx auth login \
  --profile default \
  --base-url https://your-copado-instance.example.com \
  --username you@example.com \
  --api-token "$COPADO_API_TOKEN"
```

Tokens are stored in the OS keyring when available. Profile metadata is stored
locally in an encrypted file under the user config directory. In headless
environments without a keyring backend, the token is kept in the encrypted
metadata file as a fallback.

## Commands

```bash
copado-hx auth login
copado-hx auth profiles
copado-hx auth use demo
copado-hx auth status
copado-hx auth logout

copado-hx story list [--status STATUS]
copado-hx story show STORY_ID

copado-hx commit story STORY_ID --message "message"
copado-hx promote story STORY_ID --target ENV [--dry-run]
copado-hx deploy validate STORY_ID --target ENV
copado-hx deploy story STORY_ID --target ENV

copado-hx status deployment DEPLOYMENT_ID
copado-hx status pipeline [--story STORY_ID]
```

Most read/action commands support `--profile` and `--json`.

## Production deployment guardrail

Production deployments require explicit human confirmation:

```bash
copado-hx deploy story US-003 --target production
```

The CLI asks the operator to type:

```text
DEPLOY TO PRODUCTION
```

There is intentionally no `--yes`, environment variable, or config switch that
bypasses this guardrail.

## API surface

The real HTTP client targets the following REST action shape under:

```text
/services/apexrest/copado-hx/v1
```

Implemented operations:

- `GET /user-stories`
- `GET /user-stories/{story_id}`
- `POST /user-stories/{story_id}/commit`
- `POST /user-stories/{story_id}/promote`
- `POST /user-stories/{story_id}/validate`
- `POST /user-stories/{story_id}/deploy`
- `GET /deployments/{deployment_id}`
- `GET /pipeline/status`

If your Copado tenant exposes different endpoint paths, adapt
`copado_hx.lib.api.API_PREFIX` and the path methods in `CopadoAPIClient`.

## Project layout

```text
copado_hx/
  __init__.py
  __main__.py
  cli.py
  commands/
  lib/
  utils/
  demo.py
tests/
README.md
pyproject.toml
LICENSE
```

The distribution and executable are named `copado-hx`; the import package is
`copado_hx` because Python import package names cannot contain hyphens.
