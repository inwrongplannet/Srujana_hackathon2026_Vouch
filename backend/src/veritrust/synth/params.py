"""Every assumption the synthetic borrower population depends on.

Why: a reviewer (or a judge) can audit the whole world in one file. All values are
illustrative and chosen to give plausible Indian retail-lending shapes; none are market data.
Money is integer paise (INR minor units); rates are Decimal annual fractions.
"""

from decimal import Decimal

SEED = 42
CURRENCY = "INR"
GENERATOR_VERSION = "1.0.0"

# Application cohorts: one per month, so time-based splits and drift tests are possible.
COHORTS = [(2024, m) for m in range(7, 13)] + [(2025, m) for m in range(1, 7)]
HISTORY_MONTHS = 24       # simulated before the application; the bureau grid window
STATEMENT_MONTHS = 12     # longest bank statement a borrower can share
PERFORMANCE_MONTHS = 12   # EMIs observed after disbursal
DEFAULT_ARREARS = 3       # 3 unpaid EMIs = 90+ days past due, the RBI NPA threshold
WRITE_OFF_ARREARS = 8
DPD_CAP = 180

BOUNCE_CHARGE = 59_000    # ₹500 return charge + 18% GST, illustrative

# Missing-value reason codes. Every gap in the observed data carries one.
OBSERVED = "OBSERVED"
PARTIAL = "PARTIAL"              # exists, but only part of it was shared
NO_RECORD = "NO_RECORD"          # does not exist (e.g. never borrowed, so no bureau file)
NOT_PROVIDED = "NOT_PROVIDED"    # exists, but the applicant did not share it
NOT_APPLICABLE = "NOT_APPLICABLE"
WITHHELD = "WITHHELD"            # left blank on purpose; missing not at random
STATUSES = (OBSERVED, PARTIAL, NO_RECORD, NOT_PROVIDED, NOT_APPLICABLE, WITHHELD)

# Bureau payment-grid cell codes (one per month, oldest first).
GRID_NOT_OPEN = "---"
GRID_NOT_REPORTED = "XXX"

# States: (weight, income factor, urban share multiplier). Codes are standard state abbreviations.
STATES = {
    "MH": (0.13, 1.15, 1.10), "KA": (0.09, 1.10, 1.05), "TN": (0.09, 1.05, 1.05),
    "GJ": (0.07, 1.05, 1.00), "TG": (0.07, 1.05, 1.05), "UP": (0.16, 0.80, 0.85),
    "BR": (0.10, 0.70, 0.75), "RJ": (0.08, 0.85, 0.90), "WB": (0.10, 0.85, 0.95),
    "MP": (0.11, 0.80, 0.85),
}

AGE_BANDS = ("21-25", "26-35", "36-45", "46-60")

# Hypothetical macro events (not real history). They make later cohorts behave differently,
# so conformal coverage can be tested under distribution shift.
RAINFALL_DEFICIT = {
    "name": "simulated_rainfall_deficit",
    "states": {"MH", "KA", "TG"},
    "crop_months": {(2025, 10), (2025, 11)},   # kharif harvest hit
    "crop_factor": 0.45,
    "exposure": 0.75,                           # share of farmers in those states affected
    "wage_months": {(2025, m) for m in range(9, 13)},
    "wage_factor": 0.85,                        # rural daily wages soften
}
GIG_INCENTIVE_CUT = {
    "name": "simulated_platform_incentive_cut",
    "months": {(2025, m) for m in range(3, 9)},
    "factor": 0.85,
}

# Seasonal income multipliers by calendar month (1-12).
SEASON = {
    "gig_platform": {7: 0.92, 8: 0.92, 10: 1.12, 11: 1.15, 12: 1.05},
    "kirana_msme": {3: 1.08, 10: 1.25, 11: 1.30, 6: 0.92, 7: 0.92},
}
# Farmers: share of annual crop income by harvest month; the rest is non-farm work.
CROP_CALENDAR = {10: 0.22, 11: 0.17, 3: 0.09, 4: 0.12}   # sums to 0.60
FARM_NONCROP_SHARE = Decimal("0.40")   # dairy, wage labour, remittances

# Existing-loan kinds: (lender type, annual rate, tenure choices, principal as x monthly income
# (median, log-sd), probability the lender reports to the bureau).
LOAN_KINDS = {
    "bank_personal": ("BANK", Decimal("0.14"), (24, 36, 48), (5.0, 0.4), 0.98),
    "nbfc_consumer": ("NBFC", Decimal("0.22"), (6, 9, 12), (1.0, 0.4), 0.96),
    "gold_loan": ("BANK", Decimal("0.11"), (12,), (2.0, 0.5), 0.85),
    "kcc_crop": ("BANK", Decimal("0.07"), (12,), (3.0, 0.4), 0.95),
    "mfi_jlg": ("MFI", Decimal("0.24"), (12, 24), (2.5, 0.3), 0.97),
    "two_wheeler": ("NBFC", Decimal("0.17"), (24, 36), (3.0, 0.3), 0.97),
    "fintech_app": ("FINTECH", Decimal("0.36"), (3, 6), (0.4, 0.5), 0.55),
    "bnpl": ("FINTECH", Decimal("0.30"), (3,), (0.2, 0.5), 0.35),
}

# Fictional lender names for statement narrations. None is a real institution.
LENDER_NAMES = {
    "BANK": ("NIRMAL BANK", "SAHYADRI CO-OP BANK", "UDAY BANK"),
    "NBFC": ("KESAR FINSERV", "TARANG CAPITAL", "MERU FINANCE"),
    "MFI": ("ANKUR MICROFIN", "SAKHI CREDIT"),
    "FINTECH": ("QUIKPAISA", "CASHBEE", "ZIPLEND", "PAYKITE"),
}

# The loan applied for: (annual rate, tenure choices, target EMI as a share of monthly income
# (median, log-sd)). Applicants pick an instalment they think they can carry; the tail overreaches.
PRODUCTS = {
    "personal_loan": (Decimal("0.16"), (12, 24, 36), (0.20, 0.50)),
    "working_capital": (Decimal("0.18"), (12, 24), (0.20, 0.50)),
    "agri_term": (Decimal("0.12"), (12, 24), (0.16, 0.45)),
    "micro_loan": (Decimal("0.24"), (12, 24), (0.15, 0.45)),
}

SEGMENTS = {
    # weight: population share. income: (median monthly ₹, cross-sectional log-sd).
    # cv: month-to-month income noise. urban: urban share. access: mean existing loans.
    # p_prior: chance of past (closed) bureau-reported credit. p_link: chance of sharing a bank
    # statement. deposit: share of income that passes through the bank (low, high).
    # shock: (monthly probability, income multiplier while shocked, max months).
    # stacker / inflator: behaviour propensities. community: chance of community vouches.
    "salaried_formal": {
        "weight": 0.24, "income": (32_000, 0.45), "cv": 0.03, "urban": 0.85,
        "access": 1.1, "p_prior": 0.70, "p_link": 0.85, "deposit": (0.95, 1.0),
        "shock": (0.007, 0.0, 4), "stacker": 0.08, "inflator": 0.05, "community": 0.10,
        "products": {"personal_loan": 1.0},
        "kinds": {"bank_personal": 0.35, "nbfc_consumer": 0.25, "two_wheeler": 0.2,
                  "gold_loan": 0.05, "fintech_app": 0.1, "bnpl": 0.05},
        "expense": (0.50, 0.08), "buffer_months": 0.9,
    },
    "gig_platform": {
        "weight": 0.17, "income": (22_000, 0.35), "cv": 0.20, "urban": 0.95,
        "access": 0.6, "p_prior": 0.30, "p_link": 0.80, "deposit": (0.85, 0.98),
        "shock": (0.018, 0.3, 2), "stacker": 0.14, "inflator": 0.12, "community": 0.15,
        "products": {"personal_loan": 1.0},
        "kinds": {"nbfc_consumer": 0.25, "two_wheeler": 0.25, "fintech_app": 0.3, "bnpl": 0.2},
        "expense": (0.62, 0.08), "buffer_months": 0.4,
    },
    "kirana_msme": {
        "weight": 0.18, "income": (28_000, 0.45), "cv": 0.11, "urban": 0.60,
        "access": 0.8, "p_prior": 0.45, "p_link": 0.60, "deposit": (0.35, 0.85),
        "shock": (0.014, 0.4, 2), "stacker": 0.06, "inflator": 0.15, "community": 0.30,
        "products": {"working_capital": 1.0},
        "kinds": {"bank_personal": 0.2, "nbfc_consumer": 0.2, "gold_loan": 0.25,
                  "mfi_jlg": 0.15, "fintech_app": 0.2},
        "expense": (0.58, 0.08), "buffer_months": 0.6,
        "margin": (0.10, 0.20), "p_gst": 0.45,
    },
    "smallholder_farmer": {
        "weight": 0.15, "income": (14_000, 0.40), "cv": 0.10, "urban": 0.04,
        "access": 0.7, "p_prior": 0.45, "p_link": 0.35, "deposit": (0.30, 0.70),
        "shock": (0.010, 0.6, 3), "stacker": 0.03, "inflator": 0.10, "community": 0.45,
        "products": {"agri_term": 0.8, "micro_loan": 0.2},
        "kinds": {"kcc_crop": 0.5, "gold_loan": 0.3, "mfi_jlg": 0.2},
        "expense": (0.66, 0.07), "buffer_months": 0.8,
    },
    "informal_daily_wage": {
        "weight": 0.26, "income": (12_000, 0.30), "cv": 0.12, "urban": 0.50,
        "access": 0.5, "p_prior": 0.25, "p_link": 0.40, "deposit": (0.20, 0.60),
        "shock": (0.018, 0.25, 2), "stacker": 0.07, "inflator": 0.10, "community": 0.40,
        "products": {"micro_loan": 1.0},
        "kinds": {"mfi_jlg": 0.55, "gold_loan": 0.15, "fintech_app": 0.2, "bnpl": 0.1},
        "expense": (0.69, 0.06), "buffer_months": 0.25,
    },
}

# Observation-layer propensities.
P_FULL_STATEMENT = 0.70          # of linked statements, share with all 12 months
PARTIAL_STATEMENT_MONTHS = (3, 6)
P_WINDOW_DRESSING = 0.03         # base; inflators are far more likely to do it
P_ROUND_TRIP = 0.08              # kirana only
P_DUPLICATE_IMPORT = 0.03        # statement parse duplicates some credit rows
P_TENURE_MISSING = 0.12
P_GRID_GAP = 0.02                # a lender skips a monthly bureau report
P_GST_MISSED = 0.08
P_UNDISCLOSED_LOAN = 0.10        # an honest applicant forgets one small loan

# Naive legacy policy, used only to measure who a history-only lender would turn away.
LEGACY_MAX_DTI = Decimal("0.50")
