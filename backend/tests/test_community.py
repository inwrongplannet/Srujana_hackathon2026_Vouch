"""Community vouching engine: the same known answers as frontend/src/mocks/engine/community.test.ts."""

from decimal import Decimal

from veritrust.community import (
    CommunityStore,
    Member,
    Vouch,
    community_score,
    quality,
    reliability,
    reward_preview,
    staked,
    track_record,
    utilisation,
    weight,
)


def member(resolved: int, repaid: int, committed: str = "0", member_id: str = "m") -> Member:
    return Member(member_id, "M", "", Decimal(80), Decimal(100), Decimal(committed), resolved, repaid)


def q4(d: Decimal) -> str:
    return str(d.quantize(Decimal("0.0001")))


def test_track_record_is_smoothed():
    """No record is 0.5; 6 of 7 is 7/9."""
    assert q4(track_record(member(0, 0))) == "0.5000"
    assert q4(track_record(member(7, 6))) == "0.7778"


def test_evidence_counts_only_once_the_voucher_has_a_record():
    assert q4(reliability(member(0, 0), "EVIDENCE")) == "0.0000"
    # 2 of the 5 outcomes needed: 0.75 * 0.4 = 0.30.
    assert q4(reliability(member(2, 2), "EVIDENCE")) == "0.3000"
    assert q4(reliability(member(7, 6), "EVIDENCE")) == "0.7778"


def test_relationship_quality_grows_with_years_known():
    # Neighbour 0.80 x (0.6 + 0.4 * 9/10) = 0.768.
    assert q4(quality(Vouch("m", "KNOWN", Decimal(10), "NEIGHBOUR", 9))) == "0.7680"


def test_refuses_a_stake_over_budget():
    assert utilisation(member(0, 0, "95"), Decimal(10)) is None
    assert str(utilisation(member(0, 0, "35"), Decimal(15)).quantize(Decimal("0.01"))) == "0.50"


def test_known_weight():
    # 0.8 * (7/9) * e^-0.5 * 0.768 = 0.28979...
    w = weight(member(7, 6, "35"), Vouch("m", "KNOWN", Decimal(15), "NEIGHBOUR", 9))
    assert q4(w) == "0.2898"


def test_evidence_counts_up_to_cap_plus_two_thirds_of_known():
    members = {"s": member(20, 20, member_id="s"), "k": member(20, 20, member_id="k")}
    strangers = [Vouch("s", "EVIDENCE", Decimal(5)) for _ in range(10)]
    alone = community_score(members, strangers)
    assert str(alone.evidence_counted.quantize(Decimal("0.01"))) == "0.60"
    mixed = community_score(members, strangers + [Vouch("k", "KNOWN", Decimal(5), "TRADE", 10)])
    assert q4(mixed.evidence_counted) == q4(Decimal("0.6") + mixed.known * 2 / 3)
    assert mixed.score > alone.score


def test_no_vouches_is_no_score_not_zero():
    assert community_score({}, []).score is None


def test_backing_an_underrated_borrower_earns_more():
    # 100 * 0.1 * 0.5 * (1 - 0.80) = 1.00 points; a safe bet at 0.95 gives 0.25; loss -4.00.
    gain, loss = reward_preview(Decimal("0.5"), Decimal("0.80"))
    assert str(gain.quantize(Decimal("0.01"))) == "1.00"
    assert str(loss.quantize(Decimal("0.01"))) == "-4.00"
    assert str(reward_preview(Decimal("0.5"), Decimal("0.95"))[0].quantize(Decimal("0.01"))) == "0.25"


def test_a_vouch_keeps_the_utilisation_it_was_staked_at():
    m = member(7, 6, "35")
    v = staked(m, Vouch("m", "KNOWN", Decimal(15), "NEIGHBOUR", 9))
    before = weight(m, v)
    m.committed = Decimal(80)
    assert weight(m, v) == before


def test_store_vouch_step_back_frees_the_stake():
    store = CommunityStore()
    meena = store.members["MEENA"]
    store.vouch("LAKSHMI", Vouch("MEENA", "KNOWN", Decimal(15), "NEIGHBOUR", 9))
    assert meena.committed == Decimal(50)
    store.respond("SURESH", "MEENA", "STEP_BACK")
    assert meena.committed == Decimal(35)
    assert all(v.voucher_id != "MEENA" for v in store.asks["SURESH"].vouches)
