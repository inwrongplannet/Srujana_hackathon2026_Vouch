"""What happens to a borrower each month, beyond their own rules: the world and their own luck.

All rates come from `params.py` "The world" section, each labelled SOURCED, DERIVED, DESIGN, NOISE
or ASSUMPTION:
- Covariate events from the borrower's world: a pandemic (State of Working India 2021 worker
  paths and earnings changes, a lockdown, an RBI-style moratorium), floods (CWC and the Kerala
  PDNA), heat (ILO) and droughts (IITM, Economic Survey).
- Personal shocks: job loss and re-employment (PLFS panel), hospital stays and their
  out-of-pocket cost (NSS 75th round).
- Endorsers are people: a covariate event hits each one with the borrower's exposure rate, and a
  hit endorser cannot help that month.
- Noise that breaks patterns and claims nothing: an income walk, drifting discipline, theft at the
  NCRB rate, unexplained one-off costs and failed auto-debits.
Every event is logged per month, so the answer key can say what really happened.
"""

import math
import random
from dataclasses import dataclass, field

from . import params as P
from .model import Borrower, year_month
from .world import World

COVARIATE, IDIOSYNCRATIC, NOISE = "COVARIATE", "IDIOSYNCRATIC", "NOISE"


@dataclass
class Traits:
    """A borrower's draws from the world (hidden truth) and the state of their walks."""

    world: World
    pandemic_path: str = "UNAFFECTED"
    delayed_at: int = 0                    # DELAYED_LOSS: months after onset the job goes
    irrigated: bool = False                # farmers only
    level: float = 0.0                     # NOISE: log-income walk
    out_of_work: str = ""                  # "", "JOB_LOSS" or "PANDEMIC"
    out_months: int = 0                    # months spent out of work in the simulation
    moratorium_loans: set[str] = field(default_factory=set)


def sample_traits(b: Borrower, world: World, rng: random.Random) -> Traits:
    traits = Traits(world=world)
    if b.segment not in P.PANDEMIC_EXEMPT:
        paths = list(P.PANDEMIC_PATHS)
        traits.pandemic_path = rng.choices(paths, weights=[P.PANDEMIC_PATHS[k] for k in paths])[0]
    traits.delayed_at = rng.randint(P.PANDEMIC_LOCKDOWN_MONTHS, P.PANDEMIC_NO_RECOVERY_MONTHS - 1)
    traits.irrigated = rng.random() < P.P_IRRIGATED
    return traits


@dataclass
class MonthEffects:
    income_factor: float = 1.0
    expense: int = 0                       # paise, one-time (hospital bill)
    extra_cost: float = 0.0                # x monthly income, one-time (NOISE)
    savings_lost: float = 0.0              # share of savings lost (theft, NOISE size)
    endorser_hit: float = 0.0              # chance each endorser is hit by the same event this month
    moratorium: bool = False
    glitch: bool = False
    personal: str = ""                     # "job_loss" or "hospital": the personal shock this month
    discipline: float = 0.0
    events: list[tuple[str, str]] = field(default_factory=list)   # (category, name)


def _pandemic(b: Borrower, t: Traits, phase: int, fx: MonthEffects) -> None:
    """Worker paths, earnings change, moratorium and endorser exposure, months into a pandemic."""
    lockdown = phase < P.PANDEMIC_LOCKDOWN_MONTHS
    if lockdown:
        fx.events.append((COVARIATE, "PANDEMIC_LOCKDOWN"))
    if phase < P.MORATORIUM_MONTHS:
        fx.moratorium = True
    path = t.pandemic_path
    if lockdown and path in ("LOST_RECOVERED", "NO_RECOVERY") and t.out_of_work != "PANDEMIC":
        t.out_of_work = "PANDEMIC"
        fx.events.append((COVARIATE, "PANDEMIC_JOB_LOSS"))
    elif path == "LOST_RECOVERED" and phase == P.PANDEMIC_LOCKDOWN_MONTHS and t.out_of_work == "PANDEMIC":
        t.out_of_work = ""
    elif path == "DELAYED_LOSS" and phase == t.delayed_at and not t.out_of_work:
        t.out_of_work = "PANDEMIC"
        fx.events.append((COVARIATE, "PANDEMIC_JOB_LOSS"))
    elif path == "NO_RECOVERY" and phase >= P.PANDEMIC_NO_RECOVERY_MONTHS and t.out_of_work == "PANDEMIC":
        t.out_of_work = "JOB_LOSS"         # from here, back in work at the normal PLFS rate
    end = P.PANDEMIC_LOCKDOWN_MONTHS + P.PANDEMIC_EARNINGS_MONTHS
    if not lockdown and phase < end and not t.out_of_work:
        fx.income_factor *= 1.0 + P.PANDEMIC_EARNINGS_CHANGE[b.segment]
    # DERIVED from the same paths: share of endorsers out of work at this phase.
    if lockdown:
        fx.endorser_hit = max(fx.endorser_hit, P.PANDEMIC_PATHS["LOST_RECOVERED"] + P.PANDEMIC_PATHS["NO_RECOVERY"])
    elif phase < P.PANDEMIC_NO_RECOVERY_MONTHS:
        fx.endorser_hit = max(fx.endorser_hit, P.PANDEMIC_PATHS["NO_RECOVERY"] + P.PANDEMIC_PATHS["DELAYED_LOSS"])


def step(b: Borrower, t: Traits, month: int, rng: random.Random, open_loans: list[str]) -> MonthEffects:
    """Advance the walks and draw this month's world, personal and noise effects."""
    fx = MonthEffects()
    year, cal = year_month(month)

    t.level = P.NOISE_INCOME_RHO * t.level + rng.gauss(0.0, P.NOISE_INCOME_SD[b.segment])
    fx.income_factor = math.exp(t.level)
    b.discipline = min(0.99, max(0.05, b.discipline + rng.gauss(0.0, P.NOISE_DISCIPLINE_SD)))
    fx.discipline = b.discipline

    phase = t.world.pandemic_phase(month)
    if phase is not None:
        if phase == 0:
            t.moratorium_loans = {loan_id for loan_id in open_loans if rng.random() < P.MORATORIUM_UPTAKE}
        _pandemic(b, t, phase, fx)
    if t.world.flood(b.state, month):
        fx.endorser_hit = max(fx.endorser_hit, P.FLOOD_EXPOSURE)
        if rng.random() < P.FLOOD_EXPOSURE:
            fx.income_factor *= P.FLOOD_INCOME_FACTOR
            fx.events.append((COVARIATE, "FLOOD"))
    heat = P.HEAT_FACTOR.get(b.segment)
    if heat is not None:
        # Mean-preserving: the hot months lose, the rest make it up (base income is a yearly mean).
        hot = len(P.HEAT_MONTHS)
        fx.income_factor *= heat if cal in P.HEAT_MONTHS else (12 - hot * heat) / (12 - hot)
    if b.segment == "smallholder_farmer" and cal == 10 and t.world.drought(year):
        fx.events.append((COVARIATE, "DROUGHT"))

    # Personal job loss and return to work (PLFS); farmers have no employer to lose.
    if not t.out_of_work and rng.random() < P.JOB_LOSS_MONTHLY[b.segment] * P.JOB_LOSS_SELECTION:
        t.out_of_work = "JOB_LOSS"
        fx.personal = "job_loss"
        fx.events.append((IDIOSYNCRATIC, "JOB_LOSS"))
    elif t.out_of_work == "JOB_LOSS" and rng.random() < P.REEMPLOY_MONTHLY:
        t.out_of_work = ""
    if t.out_of_work:
        # Other earners carry on, except in a lockdown, when the household loses everything (SWI).
        lockdown = phase is not None and phase < P.PANDEMIC_LOCKDOWN_MONTHS and t.out_of_work == "PANDEMIC"
        fx.income_factor *= 0.0 if lockdown else P.JOB_LOSS_INCOME_KEPT
        t.out_months += 1
        fx.personal = fx.personal or ("job_loss" if t.out_of_work == "JOB_LOSS" else "")

    if rng.random() < P.HOSPITAL_MONTHLY[b.urban]:
        mean = P.HOSPITAL_COST_MINOR[b.urban]
        # Lognormal with the sourced mean: median = mean / exp(sd^2 / 2).
        fx.expense = int(mean / math.exp(P.HOSPITAL_COST_SD ** 2 / 2) * math.exp(rng.gauss(0.0, P.HOSPITAL_COST_SD)))
        fx.personal = fx.personal or "hospital"
        fx.events.append((IDIOSYNCRATIC, "HOSPITAL"))

    if rng.random() < P.THEFT_MONTHLY:
        fx.savings_lost = rng.uniform(*P.THEFT_LOSS)
        fx.events.append((NOISE, "THEFT"))
    if rng.random() < P.NOISE_LUMPY_MONTHLY:
        fx.extra_cost = rng.uniform(*P.NOISE_LUMPY_SIZE)
        fx.events.append((NOISE, "UNEXPLAINED_COST"))
    if rng.random() < P.NOISE_GLITCH_MONTHLY:
        fx.glitch = True
        fx.events.append((NOISE, "DEBIT_GLITCH"))
    return fx


def public_events(b: Borrower, months: range) -> list[str]:
    """Disasters reported in the borrower's state over `months` (public news a lender can read)."""
    if not isinstance(b.traits, Traits):
        return []
    return b.traits.world.public_events(b.state, months)
