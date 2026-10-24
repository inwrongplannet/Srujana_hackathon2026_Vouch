"""Unit tests for configuration loading and environment overrides."""

from decimal import Decimal
import os
import pytest
from veritrust.config import Settings, get_settings
from veritrust.engine import TrustEngine
from veritrust.lending import LendingService
from veritrust.scoring import CreditScorer


def test_default_config_parameters():
    """Verify standard default configuration parameters."""
    settings = Settings()
    assert settings.kappa == Decimal("1.0")
    assert settings.alpha == Decimal("0.6")
    assert settings.beta == Decimal("0.1")
    assert settings.hop_decay == Decimal("0.5")
    assert settings.base_unit_inr == Decimal("10000.00")
    assert settings.gamma == Decimal("0.5")
    assert settings.default_base_slash == Decimal("10.0")
    assert settings.demo_mode is True


def test_env_override_k(monkeypatch: pytest.MonkeyPatch):
    """Verify that setting K or KAPPA via environment overrides the uncertainty parameter."""
    monkeypatch.setenv("K", "2.25")
    settings = Settings()
    assert settings.kappa == Decimal("2.25")

    engine = TrustEngine()
    scorer = CreditScorer(engine)
    assert scorer.kappa == Decimal("2.25")


def test_env_override_alpha_and_gamma(monkeypatch: pytest.MonkeyPatch):
    """Verify that ALPHA, GAMMA, and BASE_UNIT_INR can be overridden via environment."""
    monkeypatch.setenv("ALPHA", "0.75")
    monkeypatch.setenv("GAMMA", "0.35")
    monkeypatch.setenv("BASE_UNIT_INR", "15000.00")

    settings = Settings()
    assert settings.alpha == Decimal("0.75")
    assert settings.gamma == Decimal("0.35")
    assert settings.base_unit_inr == Decimal("15000.00")

    engine = TrustEngine()
    scorer = CreditScorer(engine)
    lending = LendingService(engine, scorer)

    assert scorer.alpha == Decimal("0.75")
    assert scorer.base_unit_inr == Decimal("15000.00")
    assert lending.gamma == Decimal("0.35")
