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

# SCENARIO, not history: a hypothetical cut in platform incentives, kept only so later cohorts
# behave differently and models can be tested under distribution shift. Droughts, floods and
# pandemics are drawn from sourced hazards per world (section "The world" below).
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
    # Personal shocks are not set here: they come from JOB_LOSS_MONTHLY and HOSPITAL_MONTHLY below.
    # stacker / inflator: behaviour propensities. community: chance of community vouches.
    "salaried_formal": {
        "weight": 0.24, "income": (32_000, 0.45), "cv": 0.03, "urban": 0.85,
        "access": 1.1, "p_prior": 0.70, "p_link": 0.85, "deposit": (0.95, 1.0),
        "stacker": 0.08, "inflator": 0.05, "community": 0.10,
        "products": {"personal_loan": 1.0},
        "kinds": {"bank_personal": 0.35, "nbfc_consumer": 0.25, "two_wheeler": 0.2,
                  "gold_loan": 0.05, "fintech_app": 0.1, "bnpl": 0.05},
        "expense": (0.50, 0.08), "buffer_months": 0.9,
    },
    "gig_platform": {
        "weight": 0.17, "income": (22_000, 0.35), "cv": 0.20, "urban": 0.95,
        "access": 0.6, "p_prior": 0.30, "p_link": 0.80, "deposit": (0.85, 0.98),
        "stacker": 0.14, "inflator": 0.12, "community": 0.15,
        "products": {"personal_loan": 1.0},
        "kinds": {"nbfc_consumer": 0.25, "two_wheeler": 0.25, "fintech_app": 0.3, "bnpl": 0.2},
        "expense": (0.62, 0.08), "buffer_months": 0.4,
    },
    "kirana_msme": {
        "weight": 0.18, "income": (28_000, 0.45), "cv": 0.11, "urban": 0.60,
        "access": 0.8, "p_prior": 0.45, "p_link": 0.60, "deposit": (0.35, 0.85),
        "stacker": 0.06, "inflator": 0.15, "community": 0.30,
        "products": {"working_capital": 1.0},
        "kinds": {"bank_personal": 0.2, "nbfc_consumer": 0.2, "gold_loan": 0.25,
                  "mfi_jlg": 0.15, "fintech_app": 0.2},
        "expense": (0.58, 0.08), "buffer_months": 0.6,
        "margin": (0.10, 0.20), "p_gst": 0.45,
    },
    "smallholder_farmer": {
        "weight": 0.15, "income": (14_000, 0.40), "cv": 0.10, "urban": 0.04,
        "access": 0.7, "p_prior": 0.45, "p_link": 0.35, "deposit": (0.30, 0.70),
        "stacker": 0.03, "inflator": 0.10, "community": 0.45,
        "products": {"agri_term": 0.8, "micro_loan": 0.2},
        "kinds": {"kcc_crop": 0.5, "gold_loan": 0.3, "mfi_jlg": 0.2},
        "expense": (0.66, 0.07), "buffer_months": 0.8,
    },
    "informal_daily_wage": {
        "weight": 0.26, "income": (12_000, 0.30), "cv": 0.12, "urban": 0.50,
        "access": 0.5, "p_prior": 0.25, "p_link": 0.40, "deposit": (0.20, 0.60),
        "stacker": 0.07, "inflator": 0.10, "community": 0.40,
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

# --- Shocks, bureau-style score and vouch graph (market-shock dataset, docs/DECISIONS.md) ---

# Share of simulated borrowers given one planned shock shortly before they apply. Deliberately
# oversampled so the shocked group is large enough to test (about 1,450 per arm detects a 4 pp
# gap at 80% power); `sample_weight` rescales it to SHOCK_REAL_INCIDENCE.
SHOCK_SHARE = {"active_credit": 0.45, "other": 0.12}   # by stratum: has a live reported loan or not
# Assumed real six-month chance of a shock big enough to dent a bureau score. Anchors, not a
# measurement: NSS 75th round in-patient care 2.9% of persons a year; PLFS quarterly exits from
# work 2.6-7.4% for urban men; NSS 77th round crop loss reported by 38% of farm households.
SHOCK_REAL_INCIDENCE = 0.05
# Shock-study cohort: extra borrowers, ids from STUDY_OFFSET + 1, drawn from the same generator but
# kept only if they carry live reported credit (only they can show a bureau drop), each given one
# planned shock. A designed sample for the shock question, tagged cohort=shock_study; it is not
# part of the main population, so its rows carry no sample_weight.
STUDY_OFFSET = 500_000
STUDY_MAX_DRAWS = 200
SHOCK_LEAD = (6, 2)                     # shock starts 6 to 2 months before the application month
SHOCK_TYPES = {
    "salaried_formal": {"MEDICAL": 0.45, "JOB_LOSS": 0.35, "FAMILY": 0.20},
    "gig_platform": {"MEDICAL": 0.40, "JOB_LOSS": 0.40, "FAMILY": 0.20},
    "kirana_msme": {"BUSINESS_DISRUPTION": 0.45, "MEDICAL": 0.40, "FAMILY": 0.15},
    "smallholder_farmer": {"CROP": 0.55, "MEDICAL": 0.35, "FAMILY": 0.10},
    "informal_daily_wage": {"MEDICAL": 0.50, "JOB_LOSS": 0.30, "FAMILY": 0.20},
}
SHOCK_SEVERITY = (0.45, 0.35, 0.20)     # DESIGN: weights of severity 1, 2, 3
# Planned-shock sizes (study design picks who is shocked and when; the size comes from sources).
# MEDICAL out-of-pocket cost per hospital case, INR, by severity = public, average, private care,
# rural / urban. SOURCED: NSS 75th round, Report 586 summary, pp.3-4.
SHOCK_MEDICAL_MINOR = {1: {False: 407_200, True: 440_800}, 2: {False: 1_593_700, True: 2_203_100},
                       3: {False: 2_615_700, True: 3_204_700}}
# FAMILY (a wedding): about 4 months' income on average. SOURCED: Bloch, Rao and Desai 2004 (JHR;
# 2002 working paper, section 2). Severity is the size tercile; the spread is NOISE.
SHOCK_FAMILY_MONTHS = 4.0
SHOCK_FAMILY_SD = 0.5
# JOB_LOSS: no pay until back in work at REEMPLOY_MONTHLY (PLFS, below). CROP: one kharif harvest
# at the unirrigated drought factor (DROUGHT_CROP_FACTOR, below).
# BUSINESS_DISRUPTION: ASSUMPTION, no source found: (income multiplier, months) by severity.
SHOCK_BUSINESS = {1: (0.65, 2), 2: (0.40, 3), 3: (0.15, 4)}
EXPENSE_SHOCKS = {"MEDICAL", "FAMILY"}
# Health expenditure coverage: about 14% rural and 19% urban. SOURCED: NSS Report 586 summary. The
# out-of-pocket cost above is already net of it, so `insured` is recorded, not deducted again.
P_INSURED = {False: 0.14, True: 0.19}       # urban?
P_SHOCK_ENQUIRY = 0.6                   # short of cash during a shock, a borrower with a file asks for credit
P_ENQUIRY_APPROVED = 0.55

# Illustrative bureau-style scorecard, 300-900. Not CIBIL or any real bureau's method: points move
# only with what the simulated bureau sees (DPD, write-offs, utilisation, enquiries, new lines).
SCORE_RANGE = (300, 900)
SCORE_BASE = 720
SCORE_HISTORY_POINTS = 60               # earned linearly over SCORE_HISTORY_MONTHS of history
SCORE_HISTORY_MONTHS = 120
SCORE_DPD_POINTS = {30: 40, 60: 80, 90: 130}   # by current worst days past due
SCORE_PER_LATE_MONTH = 12               # per month with 30+ DPD in the last 24 months
SCORE_LATE_MONTHS_CAP = 120
SCORE_WRITE_OFF_POINTS = 150
SCORE_UTILISATION_FREE = Decimal("0.70")       # utilisation above this costs points
SCORE_UTILISATION_POINTS = 60           # per 1.00 of utilisation above the free level
SCORE_PER_ENQUIRY = 8                   # in the last 6 months
SCORE_ENQUIRY_CAP = 48
SCORE_PER_NEW_LINE = 10                 # opened in the last 6 months
SCORE_NEW_LINE_CAP = 40
THIN_FILE_MONTHS = 6
SCORE_BANDS = ((550, "POOR"), (650, "FAIR"), (700, "GOOD"), (750, "VERY_GOOD"), (901, "EXCELLENT"))
SHOCK_DROP_POINTS = -50                 # a "bureau shock": score falls this much within 3 months of the shock
SHOCK_DROP_WINDOW = 3
UTILISATION_JUMP = Decimal("0.10")

# Vouch graph. Score formula from the Vouch scoring proposal: w = R/100 * h * exp(-lambda*U) * g,
# S = 100 * (1 - exp(-W/tau)). Commitments are reputation points, never money.
VOUCH_TAU = Decimal(3)
VOUCH_LAMBDA = Decimal(1)
VOUCH_COVERAGE = {"salaried_formal": 0.45, "gig_platform": 0.45, "kirana_msme": 0.65,
                  "smallholder_farmer": 0.70, "informal_daily_wage": 0.60}
VOUCHERS_PER_STATE = 12000                 # about one endorsement per endorser at 35,000 borrowers; most people vouch for one or two others
P_INSTITUTION = 0.08                    # employer or SHG federation rather than a person
VOUCH_BUDGET = (60, 100)                # reputation budget, points
VOUCH_STAKE = (8, 25)                   # points staked on one endorsement
VOUCH_EXPIRY = (12, 24)                 # months an endorsement lasts unless renewed
VOUCH_AGE = (1, 48)                     # months before the application an endorsement was first given
P_RENEW = 0.7
P_WITHDRAW_MONTHLY = 0.004              # background churn
P_WITHDRAW_AFTER_SHOCK = 0.55           # times (1 - discipline)^2: endorsers who know them walk away
P_RING = 0.10                           # of low-discipline borrowers (< 0.45), share who buy a ring of fake endorsements
RING_SIZE = (5, 9)
RING_PENALTY = Decimal("0.10")          # edge quality kept by a reciprocal ring edge
VOUCH_SUPPORT_SHARE = 0.35              # support a fully backed network can mobilise, x monthly income per unit of W
VOUCH_HELD_FLOOR = 50
VOUCH_HELD_SLACK = 5
VOUCH_RELATIONSHIPS = {"COLLEAGUE": (0.80, 1.00), "FAMILY": (0.55, 0.75), "COMMUNITY": (0.75, 0.95),
                       "TRADE": (0.70, 0.95), "NEIGHBOUR": (0.65, 0.90)}   # edge-quality range
VOUCH_LEARNING_RATE = Decimal("0.10")
VOUCH_EXPECTED_REPAY = Decimal("0.92")  # p in the reputation update
P_DISPUTE = 0.08
VOUCH_ALGORITHM = "vouch-v0.2"
SCORE_ALGORITHM = "bureau-sim-v1"

# --- The world: sourced shocks, connected people and labelled noise (world.py, behaviour.py) ---
#
# Every value below carries one label:
#   SOURCED  a published figure, cited with table or page
#   DERIVED  arithmetic on sourced figures, shown
#   DESIGN   a sampling choice (how much of something we simulate), undone by weights
#   NOISE    deliberate randomness to break patterns; not a claim about behaviour
#   ASSUMPTION  no source found; the value is a placeholder and says so
# Sources in full: data/combined/README.md (Sources and licences) and docs/DECISIONS.md.

# Worlds: alternate histories of the same calendar. All borrowers in a world share its pandemic,
# floods and droughts; a peer group never spans worlds.
WORLDS = 40                                   # DESIGN
TIMELINE = ((2022, 7), (2026, 7))             # DESIGN: first history month to last loan month

# Pandemic of COVID-19 intensity: recurs about every 59 years (95% CI 55-64). SOURCED: Marani et
# al. 2021, PNAS 118(35), Discussion. DERIVED: monthly hazard 1 - (1 - 1/59)^(1/12) = 0.00142.
PANDEMIC_MONTHLY_HAZARD = 0.00142
PANDEMIC_WORLD_SHARE = 0.30                   # DESIGN: pandemics forced into 30% of worlds, then weighted
PANDEMIC_LOCKDOWN_MONTHS = 2                  # SOURCED: national lockdown 25 Mar to 31 May 2020 (MHA orders)
# Worker trajectories Dec 2019 -> Apr 2020 -> Dec 2020. SOURCED: Azim Premji University, State of
# Working India 2021, p.63, Table 3.2: no effect 57%, lost and recovered 28%, lost and not back by
# Dec 2020 (8 months) 10%, lost later 5%.
PANDEMIC_PATHS = {"UNAFFECTED": 0.57, "LOST_RECOVERED": 0.28, "NO_RECOVERY": 0.10, "DELAYED_LOSS": 0.05}
PANDEMIC_NO_RECOVERY_MONTHS = 8               # SOURCED: same table, not back by Dec 2020
# Earnings change of those in work, Sep-Oct 2019 to 2020. SOURCED: SWI 2021, p.93, Table 4.4:
# casual -13%, self-employed -18%, permanent salaried -5%. Applied for the 6 months after lockdown.
PANDEMIC_EARNINGS_CHANGE = {"salaried_formal": -0.05, "informal_daily_wage": -0.13, "gig_platform": -0.18,
                            "kirana_msme": -0.18, "smallholder_farmer": -0.18}
PANDEMIC_EARNINGS_MONTHS = 6                  # DERIVED: lockdown end (Jun) to the Sep-Oct survey
# Farming was exempt from the lockdown. SOURCED: MHA order of 15 Apr 2020 (secondary: MHA annexure).
PANDEMIC_EXEMPT = {"smallholder_farmer"}
# Loan moratorium: EMIs due Mar-Aug 2020 could be deferred; individuals took it on 41% of loans.
# SOURCED (secondary): RBI Report on Trend and Progress of Banking 2019-20, via insolvencytracker.
MORATORIUM_MONTHS = 6
MORATORIUM_UPTAKE = 0.41

# Floods: 31.88 million people a year affected, 1953-2016. SOURCED: CWC State-wise Flood Damage
# Statistics, Table III. DERIVED: / 1,210.9 million (Census 2011) = 2.6% of people a year, in Jun-Sep.
# Kerala 2018 reached 5.4 million of about 35 million people, about 15% of the state. SOURCED:
# Kerala PDNA (Govt of Kerala, UN, World Bank, EU), Jan 2019, p.13. DERIVED: a state-month flood
# hits 15% of its people, so a state floods in a monsoon month with p = 0.026 / (4 x 0.15) = 0.043.
FLOOD_MONTHS = {6, 7, 8, 9}
FLOOD_EXPOSURE = 0.15
FLOOD_STATE_MONTH_P = 0.043
# 15.2 lost workdays per affected worker. SOURCED: Kerala PDNA p.264 and p.269, Table 3. DERIVED:
# income x (1 - 15.2 / 30) = 0.49 in the flood month.
FLOOD_INCOME_FACTOR = 0.49

# Heat: outdoor work (agriculture, construction) loses 5.87% of working hours a year. SOURCED: ILO
# 2019, Working on a Warmer Planet, Table 6.2, p.58; services lose 0.63%. DERIVED: concentrated in
# Apr-Jun, income x (1 - 0.0587 x 4) = 0.765 for outdoor work, x (1 - 0.0063 x 4) = 0.975 for gig.
# Base incomes are observed yearly averages, which already include those lost hours, so heat only
# moves income within the year: the other nine months get (12 - 3 x factor) / 9, keeping the mean.
HEAT_MONTHS = {4, 5, 6}
HEAT_FACTOR = {"informal_daily_wage": 0.765, "smallholder_farmer": 0.765, "gig_platform": 0.975}

# Drought: 26 drought years in 1871-2015. SOURCED (secondary): IITM rainfall series. DERIVED: 0.179
# a year. Kharif farm revenue in a dry shock: -7% irrigated, -14.3% unirrigated. SOURCED: Economic
# Survey 2017-18, ch.6, via Subramanian, Khare and Hari 2018 (Ideas for India).
DROUGHT_YEAR_P = 0.179
DROUGHT_CROP_FACTOR = {True: 0.93, False: 0.857}   # irrigated?
P_IRRIGATED = 0.5                             # ASSUMPTION: no irrigated-share figure in our sources

# A hypothetical cut in platform incentives, kept only to test models under distribution shift.
# SCENARIO, not history: GIG_INCENTIVE_CUT above.

# Personal shocks. Job loss = moving into unemployment. SOURCED: Bhattacharya 2021,
# arXiv:2110.05482, Table 4 (urban PLFS panel 2017Q3-2019Q4, men): salaried 1.52%, casual 4.98%,
# self-employed 1.34% a quarter. DERIVED: monthly = 1 - (1 - q)^(1/3). Moves out of the labour
# force are left out: they are mostly retirement, study or care, not a shock.
JOB_LOSS_MONTHLY = {"salaried_formal": 0.00509, "informal_daily_wage": 0.01688, "gig_platform": 0.00449,
                    "kirana_msme": 0.00449, "smallholder_farmer": 0.0}
# Unemployed back in work: 20.65% a quarter. SOURCED: same table. DERIVED: 7.4% a month.
REEMPLOY_MONTHLY = 0.074
# Share of household income kept while the borrower is out of work: the other earners carry on.
# 35-39% of household members earn (SOURCED: PLFS microdata, Tripathi, Shravan and Jayadev, RAS
# 2026, Table 4); an average household has 4.8 people (SOURCED, secondary: NFHS-3 via Wikipedia).
# DERIVED: 0.37 x 4.8 = 1.78 earners, so with equal earnings 1 - 1 / 1.78 = 0.44 is kept.
# In a pandemic lockdown the household loses everything instead (SWI 2021, p.25: the poorest 20%
# of households lost their entire income in April and May 2020).
JOB_LOSS_INCOME_KEPT = 0.44
# How much cash people keep aside (starting buffers, segment `buffer_months`, and the precautionary
# cushion rebuilt before spending a surplus): ASSUMPTION, kept from the original generator.
BUFFER_SCALE = 1.0
# Borrower selection: the PLFS rates above describe all urban men, but lenders screen applicants for
# steady work, so borrowers lose jobs less often. No source gives the size of that difference, so
# this one multiplier on JOB_LOSS_MONTHLY is CALIBRATED against the 2.5% PAR30 Crisil reported for
# microfinance in Dec 2019, measured on loans a bureau-only lender approves in normal worlds. 0.25
# gives about 3.7%; reaching 2.5% would need no job loss at all, so the gap is reported, not hidden
# (validate_world.py, data/combined/README.md).
JOB_LOSS_SELECTION = 0.25
# Hospitalisation: 2.6% of rural and 3.4% of urban people a year; out-of-pocket cost per case INR
# 15,937 rural and 22,031 urban. SOURCED: NSS 75th round, Report 586 summary, pp.3-4. DERIVED:
# monthly 1 - (1 - p)^(1/12). The cost is already net of insurance, so no insurance step follows.
HOSPITAL_MONTHLY = {False: 0.00219, True: 0.00288}          # urban?
HOSPITAL_COST_MINOR = {False: 1_593_700, True: 2_203_100}   # mean, paise
HOSPITAL_COST_SD = 0.8                        # NOISE: lognormal spread around the sourced mean
# When cash runs short, family or friends are the main source of emergency money for 32.8% of
# adults. SOURCED: World Bank Global Findex 2021, India, series fin24 (main source).
P_FAMILY_COVERS = 0.328
# Theft: 47.3 per lakh people a year. SOURCED: NCRB, Crime in India 2022, Table 1A.4. DERIVED:
# 3.9e-5 a month. The share of savings lost is NOISE.
THEFT_MONTHLY = 0.000039
THEFT_LOSS = (0.3, 1.0)                       # NOISE

# Peers. A neighbourhood group of GROUP_SIZE borrowers in the same world, state and area is
# simulated month by month together. When peers go from all repaying to none repaying, own
# repayment falls 10-15 points. SOURCED: Breza 2012, MIT PhD thesis ch.1 (Krishna district,
# Andhra Pradesh). PEER_PULL is the monthly chance of a deliberate missed EMI added at a peer
# arrears share of 1; DERIVED by calibration so the simulated gap is 12.5 points
# (tests/test_world.py, test_peer_effect_matches_breza).
GROUP_SIZE = 5                                # DESIGN
PEER_PULL = 0.37

# Endorsers are people too: a disaster that hits the borrower hits each endorser with the same
# exposure, and a hit endorser cannot help that month. No separate "support shrink" coefficient is
# assumed (none was found); the effect follows from the exposure rates above. Only 9.2% of informal
# help comes from inside the village (SOURCED: Mobarak and Rosenzweig 2013, AER P&P), so a local
# flood leaves most help intact while a pandemic does not.

# NOISE: randomness that breaks patterns. None of it is a claim about how people behave.
NOISE_INCOME_RHO = 0.95                       # persistent log-income walk
NOISE_INCOME_SD = {"salaried_formal": 0.015, "gig_platform": 0.04, "kirana_msme": 0.035,
                   "smallholder_farmer": 0.03, "informal_daily_wage": 0.035}
NOISE_DISCIPLINE_SD = 0.015                   # discipline drifts a little each month
NOISE_LUMPY_MONTHLY = 0.01                    # an unexplained one-off cost
NOISE_LUMPY_SIZE = (0.2, 1.0)                 # x monthly income; small, so noise scatters outcomes
                                              # rather than shifting the default rate
NOISE_GLITCH_MONTHLY = 0.004                  # an auto-debit fails although the money was there
NOISE_HARVEST_SD = 0.18                       # season-to-season crop scatter
