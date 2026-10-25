"""The behaviour layer: conditions that are nobody's fault, random walks, and absurdity.

Rules alone make a world too tidy. This layer adds, on a separate random stream:
- Covariate events (heatwave, flood, lockdown) that hit a whole region at once. Endorsers live in
  the same region, so the help they can give shrinks (params COVARIATE_EVENTS `support`).
- A persistent random walk in income and a slow drift in discipline, so people change.
- A scarcity dip: after a shock, discipline falls for a few months, then recovers.
- Rare events no rule predicts: windfalls, theft or fire, migration, impulse splurges (more
  likely for present-biased people and at festival time), and technical bounces.
Every event is logged per month, so the answer key can say what really happened.
"""

import math
import random
from dataclasses import dataclass, field

from . import params as P
from .model import Borrower, year_month


@dataclass
class Traits:
    """Behaviour traits and walk state for one borrower (hidden truth)."""

    present_bias: float                    # 0..1: how much of a windfall or surplus is spent now
    exposed: dict[str, bool] = field(default_factory=dict)   # covariate event -> hit or spared
    lockdown_job_loss: bool = False
    level: float = 0.0                     # log-income random-walk state
    scarcity: int = 0                      # months of scarcity dip left


def sample_traits(b: Borrower, rng: random.Random) -> Traits:
    traits = Traits(present_bias=rng.betavariate(2.0, 3.0))
    for event in P.COVARIATE_EVENTS:
        in_region = event["states"] is None or b.state in event["states"]
        touched = b.segment in event["factor"] or b.segment in event["loss"]
        traits.exposed[event["name"]] = in_region and touched and rng.random() < event["exposure"]
    traits.lockdown_job_loss = b.segment == "salaried_formal" and rng.random() < P.LOCKDOWN_JOB_LOSS
    return traits


def active_events(b: Borrower, traits: Traits, month: int) -> list[dict]:
    ym = year_month(month)
    return [e for e in P.COVARIATE_EVENTS if ym in e["months"] and traits.exposed.get(e["name"])]


def regional_events(state: str, months: range) -> list[str]:
    """Covariate events reported in a state over `months`: public news a lender can see."""
    found = []
    for e in P.COVARIATE_EVENTS:
        if (e["states"] is None or state in e["states"]) and any(year_month(m) in e["months"] for m in months):
            found.append(e["name"])
    return found


@dataclass
class MonthEffects:
    income_factor: float = 1.0
    extra_cost: float = 0.0                # x monthly income, one-time
    windfall: float = 0.0                  # x monthly income
    savings_lost: float = 0.0              # share of savings lost
    support_factor: float = 1.0            # how much endorser help survives
    tech_bounce: bool = False
    discipline: float = 0.0                # effective discipline this month
    events: list[tuple[str, str]] = field(default_factory=list)   # (category, name)


def step(b: Borrower, traits: Traits, month: int, rng: random.Random, shocked_now: bool) -> MonthEffects:
    """Advance the walks and draw this month's covariate and absurd effects."""
    fx = MonthEffects()
    traits.level = P.RW_RHO * traits.level + rng.gauss(0.0, P.RW_SD[b.segment])
    fx.income_factor = math.exp(traits.level)
    b.discipline = min(0.99, max(0.05, b.discipline + rng.gauss(0.0, P.DISCIPLINE_DRIFT_SD)))

    first_months = []
    for event in active_events(b, traits, month):
        fx.income_factor *= event["factor"].get(b.segment, 1.0)
        fx.support_factor = min(fx.support_factor, event["support"])
        fx.events.append(("COVARIATE", event["name"]))
        if year_month(month) == min(event["months"]):
            first_months.append(event)
        if event["name"] == "LOCKDOWN_NATIONAL" and traits.lockdown_job_loss:
            fx.income_factor = 0.0
            fx.events.append(("COVARIATE", "LOCKDOWN_JOB_LOSS"))
    for event in first_months:
        if b.segment in event["loss"]:
            fx.extra_cost += rng.uniform(*event["loss"][b.segment])
            fx.events.append(("COVARIATE", f"{event['name']}_ASSET_LOSS"))

    if shocked_now or first_months:
        traits.scarcity = P.SCARCITY_MONTHS
    fx.discipline = max(0.0, b.discipline - (P.SCARCITY_DIP if traits.scarcity > 0 else 0.0))
    traits.scarcity = max(0, traits.scarcity - 1)

    _, cal = year_month(month)
    if rng.random() < P.P_WINDFALL:
        fx.windfall = rng.uniform(*P.WINDFALL)
        fx.events.append(("ABSURD", "WINDFALL"))
    if rng.random() < P.P_THEFT:
        fx.savings_lost = rng.uniform(0.3, 1.0)
        fx.events.append(("ABSURD", "THEFT_OR_FIRE"))
    if rng.random() < P.P_MIGRATION:
        fx.income_factor *= 0.5
        fx.events.append(("ABSURD", "MIGRATION"))
    base, extra = P.P_SPLURGE
    p_splurge = (base + extra * traits.present_bias) * (3 if cal in P.FESTIVAL_MONTHS else 1)
    if rng.random() < p_splurge:
        fx.extra_cost += rng.uniform(*P.SPLURGE) * (0.5 + traits.present_bias)
        fx.events.append(("ABSURD", "SPLURGE"))
    fx.tech_bounce = rng.random() < P.P_TECH_BOUNCE
    if fx.tech_bounce:
        fx.events.append(("ABSURD", "TECHNICAL_BOUNCE"))
    return fx
