"""Dependency injection and shared state providers for the VeriTrust FastAPI layer."""

from typing import Optional
from veritrust.engine import TrustEngine
from veritrust.lending import LendingService
from veritrust.scoring import CreditScorer
from veritrust.store import StateStore

_engine: Optional[TrustEngine] = None
_scorer: Optional[CreditScorer] = None
_lending: Optional[LendingService] = None
_store: Optional[StateStore] = None


def get_store() -> StateStore:
    """Return singleton StateStore."""
    global _store
    if _store is None:
        _store = StateStore()
    return _store


def get_services() -> tuple[TrustEngine, CreditScorer, LendingService, StateStore]:
    """Return initialized engine, scorer, lending service, and store."""
    global _engine, _scorer, _lending, _store
    if _engine is None or _scorer is None or _lending is None or _store is None:
        _engine = TrustEngine()
        _scorer = CreditScorer(_engine)
        _lending = LendingService(_engine, _scorer)
        _store = get_store()
        _store.load(_engine, _lending)
    return _engine, _scorer, _lending, _store


def reset_services() -> tuple[TrustEngine, CreditScorer, LendingService, StateStore]:
    """Force re-initialization and seeding of clean services state."""
    global _engine, _scorer, _lending, _store
    _engine = TrustEngine()
    _scorer = CreditScorer(_engine)
    _lending = LendingService(_engine, _scorer)
    _store = get_store()
    _store.seed_defaults(_engine, _lending)
    _store.save(_engine, _lending)
    return _engine, _scorer, _lending, _store
