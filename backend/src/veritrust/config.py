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
    platform_fee_rate: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["PLATFORM_FEE_RATE", "TRANSACTION_FEE_RATE"], "0.01"),
        description="Platform transaction fee rate cut as a decimal fraction (e.g. 0.01 = 1.0% / 100 bps)",
    )
    platform_treasury_id: str = Field(
        default_factory=lambda: os.getenv("PLATFORM_TREASURY_ID", "PLATFORM_TREASURY"),
        description="Designated identifier for the platform treasury account",
    )

    # -------------------------------------------------------------------------
    # Mathematical Framework & Calibration Parameters (Master Model 2026)
    # -------------------------------------------------------------------------
    m0: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["M_0", "MINT_BASE_REWARD"], "2.0"),
        description="Base reputation reward M_0 minted from first qualifying transaction in a pair",
    )
    mint_lambda: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["MINT_LAMBDA", "LAMBDA_MINT"], "0.693147"),
        description="Diminishing return decay parameter lambda for repeated transactions between same pair (ln(2) = 0.693147)",
    )
    hop_decay_delta: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["DELTA_HOP", "HOP_DECAY_DELTA"], "0.70"),
        description="Separate hop decay parameter delta in (0, 1] for multi-hop path transmission",
    )
    g_max: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["G_MAX", "PROPAGATED_CREDIBILITY_CAP"], "100.0"),
        description="Scoring cap G_max applied to propagated credibility during loan underwriting",
    )
    q_max: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["Q_MAX", "MAX_PENALTY_FRACTION"], "1.0"),
        description="Maximum allowed borrower default reputation penalty fraction q_max",
    )
    penalty_kappa: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["PENALTY_KAPPA", "KAPPA_DEFAULT"], "1.5"),
        description="Default penalty strength parameter kappa scaling borrower reputation loss",
    )
    penalty_beta: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["PENALTY_BETA", "BETA_TIME_ESCALATION"], "1.0"),
        description="Time-escalation parameter beta for overdue default penalty",
    )
    t0_days: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["T_0", "T0_DAYS"], "30.0"),
        description="Reference overdue duration T_0 in days",
    )
    penalty_eta: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["PENALTY_ETA", "ETA_ENDORSER_TRANSFER"], "0.5"),
        description="Endorser penalty transfer-strength parameter eta passing borrower default loss to contributing sources",
    )
    epsilon: Decimal = Field(
        default_factory=lambda: _get_env_decimal(["EPSILON", "NUMERICAL_STABILIZER"], "0.0001"),
        description="Numerical stabilizer epsilon to prevent division by zero in default severity calculations",
    )


def get_settings() -> Settings:
    """Return an instantiated Settings configuration instance."""
    return Settings()

