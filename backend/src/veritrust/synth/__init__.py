"""Synthetic credit-assessment dataset: simulated lives, observed with realistic gaps.

Stages: people (hidden traits) -> simulate (months of cash flow, default emerges) ->
observe (what a lender sees, with reason-coded gaps) -> transactions (statement lines) ->
features (model row from observed data only) -> generate (CSV files + manifest).
"""
