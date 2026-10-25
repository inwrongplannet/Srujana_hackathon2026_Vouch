"""Worlds: alternate histories of the same calendar, drawn from sourced hazards.

Every borrower lives in one of WORLDS worlds. A world fixes what happens to everyone in it: whether
and when a pandemic starts, which states flood in which monsoon months, and which years bring a
drought. A pandemic is rare (about one in 59 years), so a run that sampled it at its real rate
would rarely contain one; instead PANDEMIC_WORLD_SHARE of worlds get one and `weight` scales each
world back to the real chance over the timeline (importance sampling, as `sample_weight` already
does for planned shocks). Floods and droughts are drawn at their real rates.
"""

import random
from dataclasses import dataclass, field

from . import params as P
from .model import month_index, year_month

STATES = sorted(P.STATES)
START = month_index(*P.TIMELINE[0])
END = month_index(*P.TIMELINE[1])


@dataclass
class World:
    world_id: int
    pandemic_onset: int | None
    weight: float                                   # importance weight back to the real hazard
    floods: set[tuple[str, int]] = field(default_factory=set)   # (state, month index)
    droughts: set[int] = field(default_factory=set)              # calendar years

    def pandemic_phase(self, month: int) -> int | None:
        """Months since the pandemic began (0 = first lockdown month), or None."""
        if self.pandemic_onset is None or month < self.pandemic_onset:
            return None
        return month - self.pandemic_onset

    def flood(self, state: str, month: int) -> bool:
        return (state, month) in self.floods

    def drought(self, year: int) -> bool:
        return year in self.droughts

    def public_events(self, state: str, months: range) -> list[str]:
        """Disasters reported in `state` over `months`: news any lender can read."""
        found = []
        if any(self.pandemic_phase(m) is not None and self.pandemic_phase(m) < P.PANDEMIC_LOCKDOWN_MONTHS for m in months):
            found.append("PANDEMIC_LOCKDOWN")
        found += ["FLOOD" for m in months if self.flood(state, m)]
        found += ["DROUGHT" for y in sorted({year_month(m)[0] for m in months}) if self.drought(y)]
        return found


def pandemic_chance() -> float:
    """Real chance of a pandemic starting somewhere in the timeline. DERIVED from the monthly hazard."""
    return 1.0 - (1.0 - P.PANDEMIC_MONTHLY_HAZARD) ** (END - START + 1)


def build_worlds() -> list[World]:
    """The run's worlds, identical in every run (seeded from SEED and the world id)."""
    forced = round(P.WORLDS * P.PANDEMIC_WORLD_SHARE)
    real = pandemic_chance()
    worlds = []
    for wid in range(P.WORLDS):
        rng = random.Random(f"{P.SEED}:world:{wid}")
        pandemic = wid < forced
        onset = rng.randint(START, END) if pandemic else None
        weight = real / (forced / P.WORLDS) if pandemic else (1.0 - real) / (1.0 - forced / P.WORLDS)
        world = World(world_id=wid, pandemic_onset=onset, weight=weight)
        for m in range(START, END + 1):
            if year_month(m)[1] in P.FLOOD_MONTHS:
                for state in STATES:
                    if rng.random() < P.FLOOD_STATE_MONTH_P:
                        world.floods.add((state, m))
        for year in range(P.TIMELINE[0][0], P.TIMELINE[1][0] + 1):
            if rng.random() < P.DROUGHT_YEAR_P:
                world.droughts.add(year)
        worlds.append(world)
    return worlds


def world_index(index: int) -> int:
    """Which world borrower `index` lives in: uniform, fixed per index."""
    return random.Random(f"{P.SEED}:{index}:world").randrange(P.WORLDS)
