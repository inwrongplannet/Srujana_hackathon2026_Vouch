"""The world layer: derived numbers, worlds and weights, and the new mechanics, with known answers."""

import random

import pytest

from veritrust.synth import params as P
from veritrust.synth.behaviour import Traits, step
from veritrust.synth.model import Loan, month_index
from veritrust.synth.people import sample_borrower
from veritrust.synth.simulate import simulate, simulate_group
from veritrust.synth.world import World, build_worlds, pandemic_chance


def test_derived_rates_match_their_sources():
    # Quarterly PLFS flows to monthly: 1 - (1 - q)^(1/3).
    assert P.JOB_LOSS_MONTHLY["salaried_formal"] == pytest.approx(1 - (1 - 0.0152) ** (1 / 3), abs=1e-5)
    assert P.JOB_LOSS_MONTHLY["informal_daily_wage"] == pytest.approx(1 - (1 - 0.0498) ** (1 / 3), abs=1e-5)
    assert P.REEMPLOY_MONTHLY == pytest.approx(1 - (1 - 0.2065) ** (1 / 3), abs=1e-3)
    # Pandemic: once in 59 years. Hospital: 2.6% and 3.4% a year. Flood: 2.6% a year over 4 months at 15%.
    assert P.PANDEMIC_MONTHLY_HAZARD == pytest.approx(1 - (1 - 1 / 59) ** (1 / 12), abs=1e-5)
    assert P.HOSPITAL_MONTHLY[False] == pytest.approx(1 - (1 - 0.026) ** (1 / 12), abs=1e-5)
    assert P.FLOOD_STATE_MONTH_P == pytest.approx(0.026 / (4 * 0.15), abs=1e-3)
    assert P.FLOOD_INCOME_FACTOR == pytest.approx(1 - 15.2 / 30, abs=0.01)
    # Household income kept: 0.37 x 4.8 = 1.78 earners -> 1 - 1/1.78 = 0.44.
    assert P.JOB_LOSS_INCOME_KEPT == pytest.approx(1 - 1 / (0.37 * 4.8), abs=0.005)
    assert sum(P.PANDEMIC_PATHS.values()) == pytest.approx(1.0)


def test_worlds_are_deterministic_and_weights_restore_the_real_chance():
    worlds = build_worlds()
    assert [w.pandemic_onset for w in worlds] == [w.pandemic_onset for w in build_worlds()]
    forced = sum(1 for w in worlds if w.pandemic_onset is not None)
    assert forced == round(P.WORLDS * P.PANDEMIC_WORLD_SHARE)
    # With equal borrowers per world, the weighted pandemic share equals the real chance.
    weighted = sum(w.weight for w in worlds if w.pandemic_onset is not None) / sum(w.weight for w in worlds)
    assert weighted == pytest.approx(pandemic_chance(), rel=1e-9)
    assert 0.06 < pandemic_chance() < 0.075   # 1 - (1 - 0.00142)^49


def _borrower(segment="informal_daily_wage"):
    b = sample_borrower(7, random.Random(7))
    b.segment = segment
    return b


def test_heat_moves_income_within_the_year_without_losing_any():
    b = _borrower()
    calm = World(world_id=0, pandemic_onset=None, weight=1.0)
    factors = []
    for cal in range(1, 13):
        t = Traits(world=calm)
        fx = step(b, t, month_index(2025, cal), random.Random(0), [])
        factors.append(fx.income_factor / __import__("math").exp(t.level))   # strip the noise walk
    assert factors[3] == pytest.approx(P.HEAT_FACTOR["informal_daily_wage"])
    assert sum(factors) / 12 == pytest.approx(1.0, abs=1e-9)


def test_lockdown_takes_all_income_and_flags_the_moratorium():
    b = _borrower("kirana_msme")          # no heat season, so the month after lockdown is clean
    onset = month_index(2025, 3)
    world = World(world_id=0, pandemic_onset=onset, weight=1.0)
    t = Traits(world=world, pandemic_path="LOST_RECOVERED")
    fx = step(b, t, onset, random.Random(1), ["L1"])
    assert fx.income_factor == 0.0 and fx.moratorium
    assert ("COVARIATE", "PANDEMIC_JOB_LOSS") in fx.events
    assert fx.endorser_hit == pytest.approx(0.28 + 0.10)
    back = step(b, t, onset + P.PANDEMIC_LOCKDOWN_MONTHS, random.Random(1), [])
    # Back in work, earning the SWI change for self-employed (-18%) times the noise walk.
    assert back.income_factor == pytest.approx((1 - 0.18) * __import__("math").exp(t.level))


def test_moratorium_defers_instead_of_bouncing(monkeypatch):
    # Loans open when the pandemic starts can be deferred, as in 2020; here every one opts in.
    monkeypatch.setattr(P, "MORATORIUM_UPTAKE", 1.0)
    b = _borrower("salaried_formal")
    b.savings, b.base_income = 0, 1_000_000
    b.loans = []
    onset = b.app_month + 1
    b.traits = Traits(world=World(world_id=0, pandemic_onset=onset, weight=1.0), pandemic_path="LOST_RECOVERED")
    new = Loan(loan_id="NEW", kind="personal_loan", lender_type="APPLIED", lender="X", principal=50_000_000,
               rate=__import__("decimal").Decimal("0.2"), tenure=12, emi=5_000_000, start=b.app_month, emi_day=5,
               reported=True, declared=True, is_new=True)
    _, performance = simulate(b, random.Random(3), new, aux=random.Random(4))
    deferred = [t for t in performance if ("COVARIATE", "MORATORIUM_DEFERRAL") in t.events]
    assert deferred and new.start > b.app_month          # the schedule moved instead of a bounce


def test_a_group_of_one_is_the_solo_simulation():
    a, b = _borrower(), _borrower()
    world = World(world_id=0, pandemic_onset=None, weight=1.0)
    a.traits, b.traits = Traits(world=world), Traits(world=world)
    loan = lambda x: Loan(loan_id="N", kind="micro_loan", lender_type="APPLIED", lender="X", principal=1_000_000,
                          rate=__import__("decimal").Decimal("0.24"), tenure=12, emi=95_000, start=x.app_month,
                          emi_day=5, reported=True, declared=True, is_new=True)
    solo = simulate(a, random.Random(9), loan(a), aux=random.Random(10))
    grouped = simulate_group([(b, random.Random(9), loan(b), random.Random(10))])[0]
    assert [t.income for t in solo[0] + solo[1]] == [t.income for t in grouped[0] + grouped[1]]
