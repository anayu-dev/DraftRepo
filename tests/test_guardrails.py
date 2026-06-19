from __future__ import annotations

import pytest

from copado_hx.commands.deploy import (
    PRODUCTION_CONFIRMATION_PHRASE,
    ProductionDeploymentRefused,
    ensure_production_confirmation,
    is_production_environment,
)


def test_production_environment_detection_is_explicit() -> None:
    assert is_production_environment("prod")
    assert is_production_environment(" production ")
    assert not is_production_environment("uat")
    assert not is_production_environment("prod-like-sandbox")


def test_production_confirmation_requires_exact_phrase() -> None:
    with pytest.raises(ProductionDeploymentRefused):
        ensure_production_confirmation("production", "yes")

    with pytest.raises(ProductionDeploymentRefused):
        ensure_production_confirmation("production", PRODUCTION_CONFIRMATION_PHRASE.lower())

    ensure_production_confirmation("production", PRODUCTION_CONFIRMATION_PHRASE)


def test_non_production_does_not_require_confirmation() -> None:
    ensure_production_confirmation("uat", None)
