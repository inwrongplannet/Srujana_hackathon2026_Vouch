"""Configuration management for VeriTrust engine.

Loads environment variables from .env files or OS environment, allowing
algorithmic parameters (such as k / kappa, alpha, beta, hop decay, slashing fractions)
to be dynamically configured without modifying code.
"""

import os
from decimal import Decimal
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


def _load_env_file() -> None:
    """Lightweight .env loader that searches backend/ and root directories."""
    candidates = [
        Path.cwd() / ".env",
        Path.cwd() / "backend" / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",  # backend/.env
        Path(__file__).resolve().parent.parent.parent.parent / ".env",  # root/.env
    ]
    for env_path in candidates:
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'\"")
                        if key not in os.environ:
                            os.environ[key] = val
                break
            except Exception:
                pass


_load_env_file()


def _get_env_decimal(var_names: list[str], default: str) -> Decimal:
    """Retrieve first matching env var as Decimal, fallback to default."""
    for name in var_names:
        val = os.getenv(name)
        if val is not None and val.strip() != "":
            return Decimal(val.strip())
    return Decimal(default)


def _get_env_bool(var_names: list[str], default: bool) -> bool:
    """Retrieve first matching env var as bool."""
    for name in var_names:
        val = os.getenv(name)
        if val is not None:
            return val.strip().lower() in ("true", "1", "yes")
    return default


class Settings(BaseModel):
    """VeriTrust protocol and scoring configuration parameters."""

    # -------------------------------------------------------------------------
    # Scoring & Underwriting Parameters
    # -------------------------------------------------------------------------
    kappa: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["K", "KAPPA", "VERITRUST_KAPPA"], "1.0"),
        description="Epistemic uncertainty penalty parameter k / kappa for Lower Confidence Bound",
    )
    alpha: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["ALPHA", "VERITRUST_ALPHA"], "0.6"),
        description="Weight of graph trust vs cash-flow score in composite capacity mu",
    )
    beta: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["BETA", "VERITRUST_BETA"], "0.1"),
        description="Reputation multiplier exponent for settled loans and active vouches",
    )
    hop_decay: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["HOP_DECAY", "LAMBDA", "VERITRUST_HOP_DECAY"], "0.5"),
        description="Geometric decay factor per intermediate hop in trust path propagation",
    )
    base_unit_inr: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["BASE_UNIT_INR", "VERITRUST_BASE_UNIT_INR"], "10000.00"),
        description="Monetary conversion scale per score point in INR",
    )

    # -------------------------------------------------------------------------
    # Lending & Slashing Parameters
    # -------------------------------------------------------------------------
    default_base_slash: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["DELTA_0", "DEFAULT_BASE_SLASH"], "10.0"),
        description="Primary default penalty delta0 applied to defaulter",
    )
    gamma: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["GAMMA", "VERITRUST_GAMMA"], "0.5"),
        description="Direct sponsor penalty scaling factor (delta1 = gamma * W_AB * delta0)",
    )
    borrower_reward: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["BORROWER_REWARD"], "2.0"),
        description="Reputation increment minted to borrower on full loan settlement",
    )
    sponsor_reward: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["SPONSOR_REWARD"], "1.0"),
        description="Reputation increment awarded to direct sponsors on loan settlement",
    )
    circuit_breaker_threshold: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["THETA", "CIRCUIT_BREAKER_THRESHOLD"], "0.30"),
        description="Cluster default rate threshold triggering automatic slash pause",
    )

    # -------------------------------------------------------------------------
    # Identity & Platform Flags
    # -------------------------------------------------------------------------
    poseidon_protocol_salt: str = Field(
        default_factory=lambda: os.getenv("POSEIDON_PROTOCOL_SALT", "veritrust_demo_protocol_salt_2026"),
        description="Protocol salt for ZK identity nullifier stub (# ZK_STUB)",
    )
    demo_mode: bool = Field(
        default_factory=lambda: _get_env_bool(["DEMO_MODE"], True),
        description="When True, external data rails are short-circuited to deterministic seed data",
    )


def get_settings() -> Settings:
    """Return an instantiated Settings configuration instance."""
    return Settings()

