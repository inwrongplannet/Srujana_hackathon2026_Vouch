/**
 * Recorded Assessment desk runs, shown when the backend is down or a call fails, so the desk never
 * dead-ends on an error. Real responses: assessments, details and the base what-if from the backend
 * with OR-Tools, predictions from the same codebase's /predict. Every applicant was recorded asking
 * for INR 150000 over 12 months at 24% with no bureau file.
 * Recorded on 25 Oct 2026; re-record rather than edit by hand.
 */
import type { AssessmentResult, BackendUser, PredictResponse, ScenarioResult } from '@/api/backend';

export const RECORDED_INPUT = { principal: '150000', term: 12, rate: '24', bureau: 'NO_FILE' } as const;

export const RECORDED_USERS: BackendUser[] = [
  {
    "user_id": "MEENA",
    "name": "Meena Patil (Kirana store, Old Hubballi)",
    "reputation": "10.0",
    "capacity": "10.0",
    "status": "ACTIVE",
    "is_anchor": false,
    "n_settled_loans": 0
  },
  {
    "user_id": "RAMESH",
    "name": "Ramesh Hegde (Cloth wholesaler)",
    "reputation": "8.0",
    "capacity": "8.0",
    "status": "ACTIVE",
    "is_anchor": false,
    "n_settled_loans": 0
  },
  {
    "user_id": "ANAND",
    "name": "Anand Kulkarni (Retired bank officer)",
    "reputation": "6.0",
    "capacity": "6.0",
    "status": "ACTIVE",
    "is_anchor": false,
    "n_settled_loans": 0
  },
  {
    "user_id": "LAKSHMI",
    "name": "Lakshmi Naik (Tailoring unit, Hubballi)",
    "reputation": "0.0",
    "capacity": "0.0",
    "status": "ACTIVE",
    "is_anchor": false,
    "n_settled_loans": 0
  },
  {
    "user_id": "SURESH",
    "name": "Suresh Kulkarni (Auto-rickshaw driver)",
    "reputation": "0.0",
    "capacity": "0.0",
    "status": "ACTIVE",
    "is_anchor": false,
    "n_settled_loans": 0
  },
  {
    "user_id": "IMRAN",
    "name": "Imran Mulla (Mobile repair stall)",
    "reputation": "0.0",
    "capacity": "0.0",
    "status": "ACTIVE",
    "is_anchor": false,
    "n_settled_loans": 0
  }
];

export interface RecordedRun {
  applicationId: string;
  result: AssessmentResult;
  /**
   * Typed loosely: the backend declares some CombinedAssessment fields as plain dicts, which the
   * generated types render as Record<string, never>, so a real response cannot be written as a literal.
   */
  detail: unknown;
  scenario: ScenarioResult;
  predict: PredictResponse;
}

export const RECORDED_RUNS: Record<string, RecordedRun> = {
  "MEENA": {
    "applicationId": "APP_3F9AF8FD",
    "result": {
      "assessment_id": "ASM_1B3D075CBC00",
      "application_id": "APP_3F9AF8FD",
      "borrower_id": "MEENA",
      "verdict": "RESTRUCTURED_ALTERNATIVE",
      "bureau_status": "NO_FILE",
      "bureau_score": null,
      "vouch_score": "60.2",
      "affordability": {
        "gross_monthly_income": "0.00",
        "non_discretionary_outflows": "0.00",
        "disposable_income": "-3900.00",
        "max_affordable_emi": "0.00",
        "protected_cash_buffer": "3900.00",
        "status": "INSUFFICIENT",
        "binding_rule": "DISPOSABLE_INCOME"
      },
      "best_plan": null,
      "stress_resilience": {
        "rating": "FRAGILE",
        "shortfall_probability": 1.0,
        "adverse_5th_percentile_cash": "-21489.73",
        "income_shock_tolerance_percent": 0.0
      },
      "reason_codes": [
        "COMMUNITY_VOUCH_ACTIVE",
        "STRESS_TEST_FRAGILE"
      ],
      "positive_factors": [
        {
          "code": "COMMUNITY_VOUCH_ACTIVE",
          "text": "Endorsed by 1 active community member(s) with Vouch score 60.2",
          "source": "WEB_OF_TRUST_GRAPH"
        }
      ],
      "risk_factors": [],
      "missing_information": [
        "Credit bureau history is unavailable on file (thin-file applicant)",
        "No income or expense data shared yet: affordability is unknown, not poor"
      ],
      "review_flags": []
    },
    "detail": {
      "assessment_id": "ASM_1B3D075CBC00",
      "application_id": "APP_3F9AF8FD",
      "borrower_id": "MEENA",
      "bureau": {
        "status": "NO_FILE",
        "score": null,
        "source": null,
        "as_of": null
      },
      "vouch": {
        "vouch_score": "60.2",
        "status": "ACTIVE",
        "confidence": "MEDIUM",
        "eligible_endorsements": 1,
        "raw_support": "0.8916",
        "quality_factor": "0.5000"
      },
      "affordability": {
        "status": "INSUFFICIENT",
        "gross_monthly_income": "0.00",
        "non_discretionary_outflows": "0.00",
        "disposable_income": "-3900.00",
        "protected_cash_buffer": "3000.00",
        "max_affordable_emi": "0.00",
        "binding_constraint": "DISPOSABLE_INCOME"
      },
      "data_quality": "LOW",
      "positive_factors": [
        {
          "code": "COMMUNITY_VOUCH_ACTIVE",
          "text": "Endorsed by 1 active community member(s) with Vouch score 60.2",
          "source": "WEB_OF_TRUST_GRAPH"
        }
      ],
      "risk_factors": [],
      "missing_information": [
        "Credit bureau history is unavailable on file (thin-file applicant)",
        "No income or expense data shared yet: affordability is unknown, not poor"
      ],
      "review_flags": [],
      "algorithm_version": "vouch-v2.0",
      "timestamp": "2026-10-25T16:40:48.922309Z"
    },
    "scenario": {
      "base_assessment_id": "ASM_1B3D075CBC00",
      "is_feasible": false,
      "monthly_emi": "14183.94",
      "residual_cash": "-14183.94",
      "income_shock_margin": "35459.85",
      "binding_constraint": "INSOLVENT_DISPOSABLE_INCOME",
      "summary": "Requested monthly instalment of INR 14,183.94 exceeds your maximum affordable instalment of INR 0.00 by INR 14,183.94. Requested principal of INR 150,000.00 exceeds your approved credit ceiling of INR 34,206.84 by INR 115,793.16."
    },
    "predict": {
      "borrower_id": "MEENA",
      "prediction": {
        "default_probability": 0.0392,
        "repayment_probability": 0.9608,
        "credit_score": 785,
        "risk_tier": "LOW_RISK",
        "decision": "DECLINE_CANDIDATE",
        "conformal_set": [
          "REPAY",
          "DEFAULT"
        ],
        "confidence_level": 0.9,
        "epistemic_uncertainty": 0.5
      },
      "explanation": {
        "summary": "The requested loan does not fit: its EMI of INR 14,183.94 is above the maximum affordable instalment of INR 11,462.50 (DISPOSABLE_INCOME). Default probability on these terms is 3.9%; see the remedies for terms that fit.",
        "positive_factors": [
          {
            "code": "VOUCH_REPUTATION",
            "text": "Freshness-adjusted Web-of-Trust score: 60.2",
            "feature": "vouch_score",
            "observed": "60.2",
            "log_odds": -0.7,
            "direction": "lowers_risk"
          },
          {
            "code": "EMI_BOUNCE",
            "text": "Bounced auto-debits in the last 3 months: 0",
            "feature": "bank_bounces_3m",
            "observed": "0",
            "log_odds": -0.3,
            "direction": "lowers_risk"
          },
          {
            "code": "VOUCH_PRESENT",
            "text": "Community peer vouches: 1",
            "feature": "vouch_count",
            "observed": "1",
            "log_odds": -0.25,
            "direction": "lowers_risk"
          },
          {
            "code": "TENURE",
            "text": "Months in current occupation: 24 months",
            "feature": "occupation_tenure_months",
            "observed": "24 months",
            "log_odds": -0.25,
            "direction": "lowers_risk"
          },
          {
            "code": "INCOME_LEVEL",
            "text": "Estimated monthly income: INR 35,000.00",
            "feature": "income_est_minor",
            "observed": "INR 35,000.00",
            "log_odds": -0.2,
            "direction": "lowers_risk"
          },
          {
            "code": "INCOME_UNSTABLE",
            "text": "Month-to-month income variation: 0.10",
            "feature": "bank_income_cv",
            "observed": "0.10",
            "log_odds": -0.2,
            "direction": "lowers_risk"
          },
          {
            "code": "MONTHLY_SURPLUS",
            "text": "Median monthly surplus before EMIs: INR 17,500.00",
            "feature": "bank_surplus_median_minor",
            "observed": "INR 17,500.00",
            "log_odds": -0.1,
            "direction": "lowers_risk"
          }
        ],
        "risk_factors": [
          {
            "code": "DTI_ABOVE_CAP",
            "text": "Debt-to-income after the new EMI: 0.48",
            "feature": "dti_est",
            "observed": "0.48",
            "log_odds": 0.55,
            "direction": "raises_risk"
          },
          {
            "code": "AMOUNT_TO_INCOME_HIGH",
            "text": "Requested amount relative to income: 4.29",
            "feature": "amount_to_income",
            "observed": "4.29",
            "log_odds": 0.5,
            "direction": "raises_risk"
          }
        ],
        "missing_information": [
          {
            "code": "MISSING_BUREAU_FILE",
            "text": "Credit bureau history is unavailable on file (thin-file applicant; alternative cash-flow and vouch evidence utilized)",
            "status": "NO_FILE"
          },
          {
            "code": "MISSING_GST",
            "text": "GST filings do not apply to this micro-enterprise category",
            "status": "NOT_APPLICABLE"
          }
        ]
      },
      "temporal_freshness": {
        "evidence_age_months": 0.0,
        "vouch_confidence": 1.0,
        "cashflow_confidence": 1.0,
        "repayment_confidence": 1.0,
        "composite_confidence": 1.0,
        "is_stale": false,
        "staleness_warning": null
      },
      "multidimensional_scores": {
        "financial_capacity_score": 60.6,
        "evidence_reliability_score": 75.0,
        "graph_reputation_score": 60.2,
        "stress_resilience_score": 22.2
      },
      "counterfactual_remedy": {
        "target_decision": "ELIGIBLE",
        "is_already_eligible": false,
        "max_recommended_principal": "121219.85",
        "recommended_tenure_months": 18,
        "sustainable_emi": "11462.50",
        "required_additional_monthly_income": "7775.54",
        "actionable_recommendations": [
          "Reduce requested principal from INR 150,000.00 to INR 121,219.85 to align monthly EMI with sustainable disposable cash flow.",
          "Extend loan tenure from 12 to 18 months, lowering monthly EMI to INR 10,005.32.",
          "Add 1 to 2 community endorsements from active guild anchors to boost Graph Reputation score above 50.0.",
          "An additional verified monthly income of INR 7,775.54 would satisfy underwriting bounds."
        ]
      }
    }
  },
  "RAMESH": {
    "applicationId": "APP_5763DB54",
    "result": {
      "assessment_id": "ASM_984AE73B98E4",
      "application_id": "APP_5763DB54",
      "borrower_id": "RAMESH",
      "verdict": "RESTRUCTURED_ALTERNATIVE",
      "bureau_status": "NO_FILE",
      "bureau_score": null,
      "vouch_score": "60.2",
      "affordability": {
        "gross_monthly_income": "0.00",
        "non_discretionary_outflows": "0.00",
        "disposable_income": "-3900.00",
        "max_affordable_emi": "0.00",
        "protected_cash_buffer": "3900.00",
        "status": "INSUFFICIENT",
        "binding_rule": "DISPOSABLE_INCOME"
      },
      "best_plan": null,
      "stress_resilience": {
        "rating": "FRAGILE",
        "shortfall_probability": 1.0,
        "adverse_5th_percentile_cash": "-21489.73",
        "income_shock_tolerance_percent": 0.0
      },
      "reason_codes": [
        "COMMUNITY_VOUCH_ACTIVE",
        "STRESS_TEST_FRAGILE"
      ],
      "positive_factors": [
        {
          "code": "COMMUNITY_VOUCH_ACTIVE",
          "text": "Endorsed by 1 active community member(s) with Vouch score 60.2",
          "source": "WEB_OF_TRUST_GRAPH"
        }
      ],
      "risk_factors": [],
      "missing_information": [
        "Credit bureau history is unavailable on file (thin-file applicant)",
        "No income or expense data shared yet: affordability is unknown, not poor"
      ],
      "review_flags": []
    },
    "detail": {
      "assessment_id": "ASM_984AE73B98E4",
      "application_id": "APP_5763DB54",
      "borrower_id": "RAMESH",
      "bureau": {
        "status": "NO_FILE",
        "score": null,
        "source": null,
        "as_of": null
      },
      "vouch": {
        "vouch_score": "60.2",
        "status": "ACTIVE",
        "confidence": "MEDIUM",
        "eligible_endorsements": 1,
        "raw_support": "0.8916",
        "quality_factor": "0.5000"
      },
      "affordability": {
        "status": "INSUFFICIENT",
        "gross_monthly_income": "0.00",
        "non_discretionary_outflows": "0.00",
        "disposable_income": "-3900.00",
        "protected_cash_buffer": "3000.00",
        "max_affordable_emi": "0.00",
        "binding_constraint": "DISPOSABLE_INCOME"
      },
      "data_quality": "LOW",
      "positive_factors": [
        {
          "code": "COMMUNITY_VOUCH_ACTIVE",
          "text": "Endorsed by 1 active community member(s) with Vouch score 60.2",
          "source": "WEB_OF_TRUST_GRAPH"
        }
      ],
      "risk_factors": [],
      "missing_information": [
        "Credit bureau history is unavailable on file (thin-file applicant)",
        "No income or expense data shared yet: affordability is unknown, not poor"
      ],
      "review_flags": [],
      "algorithm_version": "vouch-v2.0",
      "timestamp": "2026-10-25T16:40:49.184323Z"
    },
    "scenario": {
      "base_assessment_id": "ASM_984AE73B98E4",
      "is_feasible": false,
      "monthly_emi": "14183.94",
      "residual_cash": "-14183.94",
      "income_shock_margin": "35459.85",
      "binding_constraint": "INSOLVENT_DISPOSABLE_INCOME",
      "summary": "Requested monthly instalment of INR 14,183.94 exceeds your maximum affordable instalment of INR 0.00 by INR 14,183.94. Requested principal of INR 150,000.00 exceeds your approved credit ceiling of INR 34,206.84 by INR 115,793.16."
    },
    "predict": {
      "borrower_id": "RAMESH",
      "prediction": {
        "default_probability": 0.0392,
        "repayment_probability": 0.9608,
        "credit_score": 785,
        "risk_tier": "LOW_RISK",
        "decision": "DECLINE_CANDIDATE",
        "conformal_set": [
          "REPAY",
          "DEFAULT"
        ],
        "confidence_level": 0.9,
        "epistemic_uncertainty": 0.5
      },
      "explanation": {
        "summary": "The requested loan does not fit: its EMI of INR 14,183.94 is above the maximum affordable instalment of INR 11,462.50 (DISPOSABLE_INCOME). Default probability on these terms is 3.9%; see the remedies for terms that fit.",
        "positive_factors": [
          {
            "code": "VOUCH_REPUTATION",
            "text": "Freshness-adjusted Web-of-Trust score: 60.2",
            "feature": "vouch_score",
            "observed": "60.2",
            "log_odds": -0.7,
            "direction": "lowers_risk"
          },
          {
            "code": "EMI_BOUNCE",
            "text": "Bounced auto-debits in the last 3 months: 0",
            "feature": "bank_bounces_3m",
            "observed": "0",
            "log_odds": -0.3,
            "direction": "lowers_risk"
          },
          {
            "code": "VOUCH_PRESENT",
            "text": "Community peer vouches: 1",
            "feature": "vouch_count",
            "observed": "1",
            "log_odds": -0.25,
            "direction": "lowers_risk"
          },
          {
            "code": "TENURE",
            "text": "Months in current occupation: 24 months",
            "feature": "occupation_tenure_months",
            "observed": "24 months",
            "log_odds": -0.25,
            "direction": "lowers_risk"
          },
          {
            "code": "INCOME_LEVEL",
            "text": "Estimated monthly income: INR 35,000.00",
            "feature": "income_est_minor",
            "observed": "INR 35,000.00",
            "log_odds": -0.2,
            "direction": "lowers_risk"
          },
          {
            "code": "INCOME_UNSTABLE",
            "text": "Month-to-month income variation: 0.10",
            "feature": "bank_income_cv",
            "observed": "0.10",
            "log_odds": -0.2,
            "direction": "lowers_risk"
          },
          {
            "code": "MONTHLY_SURPLUS",
            "text": "Median monthly surplus before EMIs: INR 17,500.00",
            "feature": "bank_surplus_median_minor",
            "observed": "INR 17,500.00",
            "log_odds": -0.1,
            "direction": "lowers_risk"
          }
        ],
        "risk_factors": [
          {
            "code": "DTI_ABOVE_CAP",
            "text": "Debt-to-income after the new EMI: 0.48",
            "feature": "dti_est",
            "observed": "0.48",
            "log_odds": 0.55,
            "direction": "raises_risk"
          },
          {
            "code": "AMOUNT_TO_INCOME_HIGH",
            "text": "Requested amount relative to income: 4.29",
            "feature": "amount_to_income",
            "observed": "4.29",
            "log_odds": 0.5,
            "direction": "raises_risk"
          }
        ],
        "missing_information": [
          {
            "code": "MISSING_BUREAU_FILE",
            "text": "Credit bureau history is unavailable on file (thin-file applicant; alternative cash-flow and vouch evidence utilized)",
            "status": "NO_FILE"
          },
          {
            "code": "MISSING_GST",
            "text": "GST filings do not apply to this micro-enterprise category",
            "status": "NOT_APPLICABLE"
          }
        ]
      },
      "temporal_freshness": {
        "evidence_age_months": 0.0,
        "vouch_confidence": 1.0,
        "cashflow_confidence": 1.0,
        "repayment_confidence": 1.0,
        "composite_confidence": 1.0,
        "is_stale": false,
        "staleness_warning": null
      },
      "multidimensional_scores": {
        "financial_capacity_score": 60.6,
        "evidence_reliability_score": 75.0,
        "graph_reputation_score": 60.2,
        "stress_resilience_score": 22.2
      },
      "counterfactual_remedy": {
        "target_decision": "ELIGIBLE",
        "is_already_eligible": false,
        "max_recommended_principal": "121219.85",
        "recommended_tenure_months": 18,
        "sustainable_emi": "11462.50",
        "required_additional_monthly_income": "7775.54",
        "actionable_recommendations": [
          "Reduce requested principal from INR 150,000.00 to INR 121,219.85 to align monthly EMI with sustainable disposable cash flow.",
          "Extend loan tenure from 12 to 18 months, lowering monthly EMI to INR 10,005.32.",
          "Add 1 to 2 community endorsements from active guild anchors to boost Graph Reputation score above 50.0.",
          "An additional verified monthly income of INR 7,775.54 would satisfy underwriting bounds."
        ]
      }
    }
  },
  "ANAND": {
    "applicationId": "APP_D3267CEF",
    "result": {
      "assessment_id": "ASM_C97D4F1CAE4D",
      "application_id": "APP_D3267CEF",
      "borrower_id": "ANAND",
      "verdict": "RESTRUCTURED_ALTERNATIVE",
      "bureau_status": "NO_FILE",
      "bureau_score": null,
      "vouch_score": "60.2",
      "affordability": {
        "gross_monthly_income": "0.00",
        "non_discretionary_outflows": "0.00",
        "disposable_income": "-3900.00",
        "max_affordable_emi": "0.00",
        "protected_cash_buffer": "3900.00",
        "status": "INSUFFICIENT",
        "binding_rule": "DISPOSABLE_INCOME"
      },
      "best_plan": null,
      "stress_resilience": {
        "rating": "FRAGILE",
        "shortfall_probability": 1.0,
        "adverse_5th_percentile_cash": "-21489.73",
        "income_shock_tolerance_percent": 0.0
      },
      "reason_codes": [
        "COMMUNITY_VOUCH_ACTIVE",
        "STRESS_TEST_FRAGILE"
      ],
      "positive_factors": [
        {
          "code": "COMMUNITY_VOUCH_ACTIVE",
          "text": "Endorsed by 1 active community member(s) with Vouch score 60.2",
          "source": "WEB_OF_TRUST_GRAPH"
        }
      ],
      "risk_factors": [],
      "missing_information": [
        "Credit bureau history is unavailable on file (thin-file applicant)",
        "No income or expense data shared yet: affordability is unknown, not poor"
      ],
      "review_flags": []
    },
    "detail": {
      "assessment_id": "ASM_C97D4F1CAE4D",
      "application_id": "APP_D3267CEF",
      "borrower_id": "ANAND",
      "bureau": {
        "status": "NO_FILE",
        "score": null,
        "source": null,
        "as_of": null
      },
      "vouch": {
        "vouch_score": "60.2",
        "status": "ACTIVE",
        "confidence": "MEDIUM",
        "eligible_endorsements": 1,
        "raw_support": "0.8916",
        "quality_factor": "0.5000"
      },
      "affordability": {
        "status": "INSUFFICIENT",
        "gross_monthly_income": "0.00",
        "non_discretionary_outflows": "0.00",
        "disposable_income": "-3900.00",
        "protected_cash_buffer": "3000.00",
        "max_affordable_emi": "0.00",
        "binding_constraint": "DISPOSABLE_INCOME"
      },
      "data_quality": "LOW",
      "positive_factors": [
        {
          "code": "COMMUNITY_VOUCH_ACTIVE",
          "text": "Endorsed by 1 active community member(s) with Vouch score 60.2",
          "source": "WEB_OF_TRUST_GRAPH"
        }
      ],
      "risk_factors": [],
      "missing_information": [
        "Credit bureau history is unavailable on file (thin-file applicant)",
        "No income or expense data shared yet: affordability is unknown, not poor"
      ],
      "review_flags": [],
      "algorithm_version": "vouch-v2.0",
      "timestamp": "2026-10-25T16:40:49.397418Z"
    },
    "scenario": {
      "base_assessment_id": "ASM_C97D4F1CAE4D",
      "is_feasible": false,
      "monthly_emi": "14183.94",
      "residual_cash": "-14183.94",
      "income_shock_margin": "35459.85",
      "binding_constraint": "INSOLVENT_DISPOSABLE_INCOME",
      "summary": "Requested monthly instalment of INR 14,183.94 exceeds your maximum affordable instalment of INR 0.00 by INR 14,183.94. Requested principal of INR 150,000.00 exceeds your approved credit ceiling of INR 34,206.84 by INR 115,793.16."
    },
    "predict": {
      "borrower_id": "ANAND",
      "prediction": {
        "default_probability": 0.0392,
        "repayment_probability": 0.9608,
        "credit_score": 785,
        "risk_tier": "LOW_RISK",
        "decision": "DECLINE_CANDIDATE",
        "conformal_set": [
          "REPAY",
          "DEFAULT"
        ],
        "confidence_level": 0.9,
        "epistemic_uncertainty": 0.5
      },
      "explanation": {
        "summary": "The requested loan does not fit: its EMI of INR 14,183.94 is above the maximum affordable instalment of INR 11,462.50 (DISPOSABLE_INCOME). Default probability on these terms is 3.9%; see the remedies for terms that fit.",
        "positive_factors": [
          {
            "code": "VOUCH_REPUTATION",
            "text": "Freshness-adjusted Web-of-Trust score: 60.2",
            "feature": "vouch_score",
            "observed": "60.2",
            "log_odds": -0.7,
            "direction": "lowers_risk"
          },
          {
            "code": "EMI_BOUNCE",
            "text": "Bounced auto-debits in the last 3 months: 0",
            "feature": "bank_bounces_3m",
            "observed": "0",
            "log_odds": -0.3,
            "direction": "lowers_risk"
          },
          {
            "code": "VOUCH_PRESENT",
            "text": "Community peer vouches: 1",
            "feature": "vouch_count",
            "observed": "1",
            "log_odds": -0.25,
            "direction": "lowers_risk"
          },
          {
            "code": "TENURE",
            "text": "Months in current occupation: 24 months",
            "feature": "occupation_tenure_months",
            "observed": "24 months",
            "log_odds": -0.25,
            "direction": "lowers_risk"
          },
          {
            "code": "INCOME_LEVEL",
            "text": "Estimated monthly income: INR 35,000.00",
            "feature": "income_est_minor",
            "observed": "INR 35,000.00",
            "log_odds": -0.2,
            "direction": "lowers_risk"
          },
          {
            "code": "INCOME_UNSTABLE",
            "text": "Month-to-month income variation: 0.10",
            "feature": "bank_income_cv",
            "observed": "0.10",
            "log_odds": -0.2,
            "direction": "lowers_risk"
          },
          {
            "code": "MONTHLY_SURPLUS",
            "text": "Median monthly surplus before EMIs: INR 17,500.00",
            "feature": "bank_surplus_median_minor",
            "observed": "INR 17,500.00",
            "log_odds": -0.1,
            "direction": "lowers_risk"
          }
        ],
        "risk_factors": [
          {
            "code": "DTI_ABOVE_CAP",
            "text": "Debt-to-income after the new EMI: 0.48",
            "feature": "dti_est",
            "observed": "0.48",
            "log_odds": 0.55,
            "direction": "raises_risk"
          },
          {
            "code": "AMOUNT_TO_INCOME_HIGH",
            "text": "Requested amount relative to income: 4.29",
            "feature": "amount_to_income",
            "observed": "4.29",
            "log_odds": 0.5,
            "direction": "raises_risk"
          }
        ],
        "missing_information": [
          {
            "code": "MISSING_BUREAU_FILE",
            "text": "Credit bureau history is unavailable on file (thin-file applicant; alternative cash-flow and vouch evidence utilized)",
            "status": "NO_FILE"
          },
          {
            "code": "MISSING_GST",
            "text": "GST filings do not apply to this micro-enterprise category",
            "status": "NOT_APPLICABLE"
          }
        ]
      },
      "temporal_freshness": {
        "evidence_age_months": 0.0,
        "vouch_confidence": 1.0,
        "cashflow_confidence": 1.0,
        "repayment_confidence": 1.0,
        "composite_confidence": 1.0,
        "is_stale": false,
        "staleness_warning": null
      },
      "multidimensional_scores": {
        "financial_capacity_score": 60.6,
        "evidence_reliability_score": 75.0,
        "graph_reputation_score": 60.2,
        "stress_resilience_score": 22.2
      },
      "counterfactual_remedy": {
        "target_decision": "ELIGIBLE",
        "is_already_eligible": false,
        "max_recommended_principal": "121219.85",
        "recommended_tenure_months": 18,
        "sustainable_emi": "11462.50",
        "required_additional_monthly_income": "7775.54",
        "actionable_recommendations": [
          "Reduce requested principal from INR 150,000.00 to INR 121,219.85 to align monthly EMI with sustainable disposable cash flow.",
          "Extend loan tenure from 12 to 18 months, lowering monthly EMI to INR 10,005.32.",
          "Add 1 to 2 community endorsements from active guild anchors to boost Graph Reputation score above 50.0.",
          "An additional verified monthly income of INR 7,775.54 would satisfy underwriting bounds."
        ]
      }
    }
  },
  "LAKSHMI": {
    "applicationId": "APP_420F6543",
    "result": {
      "assessment_id": "ASM_023DD7331A99",
      "application_id": "APP_420F6543",
      "borrower_id": "LAKSHMI",
      "verdict": "RESTRUCTURED_ALTERNATIVE",
      "bureau_status": "NO_FILE",
      "bureau_score": null,
      "vouch_score": "63.5",
      "affordability": {
        "gross_monthly_income": "38000.00",
        "non_discretionary_outflows": "22500.00",
        "disposable_income": "8945.00",
        "max_affordable_emi": "8945.00",
        "protected_cash_buffer": "6555.00",
        "status": "SUFFICIENT",
        "binding_rule": "DISPOSABLE_INCOME"
      },
      "best_plan": {
        "principal": "150000.00",
        "term_months": 24,
        "monthly_emi": "7930.66",
        "total_interest": "40335.84"
      },
      "stress_resilience": {
        "rating": "MODERATE",
        "shortfall_probability": 0.131,
        "adverse_5th_percentile_cash": "-4710.64",
        "income_shock_tolerance_percent": 19.92
      },
      "reason_codes": [
        "INCOME_PRESENT",
        "INCOME_STABLE",
        "COMMUNITY_VOUCH_ACTIVE",
        "DISPOSABLE_INCOME_SUFFICIENT",
        "AFFORDABILITY_DEFICIT",
        "STRESS_TEST_MODERATE"
      ],
      "positive_factors": [
        {
          "code": "INCOME_PRESENT",
          "text": "Verified recurring monthly income of INR 38,000.00 documented",
          "source": "BANK_STATEMENT"
        },
        {
          "code": "INCOME_STABLE",
          "text": "Income volatility is low (9.9%), indicating predictable earnings",
          "source": "ACCOUNT_AGGREGATOR"
        },
        {
          "code": "COMMUNITY_VOUCH_ACTIVE",
          "text": "Endorsed by 2 active community member(s) with Vouch score 63.5",
          "source": "WEB_OF_TRUST_GRAPH"
        },
        {
          "code": "DISPOSABLE_INCOME_SUFFICIENT",
          "text": "Net disposable monthly surplus of INR 8,945.00 after non-discretionary expenses and buffer",
          "source": "AFFORDABILITY_ENGINE"
        }
      ],
      "risk_factors": [
        {
          "code": "AFFORDABILITY_DEFICIT",
          "text": "Requested instalment of INR 14,183.94 exceeds affordable limit of INR 8,945.00",
          "source": "AFFORDABILITY_ENGINE"
        }
      ],
      "missing_information": [
        "Credit bureau history is unavailable on file (thin-file applicant)"
      ],
      "review_flags": [
        "RESTRUCTURING_RECOMMENDED"
      ]
    },
    "detail": {
      "assessment_id": "ASM_023DD7331A99",
      "application_id": "APP_420F6543",
      "borrower_id": "LAKSHMI",
      "bureau": {
        "status": "NO_FILE",
        "score": null,
        "source": null,
        "as_of": null
      },
      "vouch": {
        "vouch_score": "63.5",
        "status": "ACTIVE",
        "confidence": "MEDIUM",
        "eligible_endorsements": 2,
        "raw_support": "0.9412",
        "quality_factor": "0.5000"
      },
      "affordability": {
        "status": "SUFFICIENT",
        "gross_monthly_income": "38000.00",
        "non_discretionary_outflows": "22500.00",
        "disposable_income": "8945.00",
        "protected_cash_buffer": "5700.00",
        "max_affordable_emi": "8945.00",
        "binding_constraint": "DISPOSABLE_INCOME"
      },
      "data_quality": "MEDIUM",
      "positive_factors": [
        {
          "code": "INCOME_PRESENT",
          "text": "Verified recurring monthly income of INR 38,000.00 documented",
          "source": "BANK_STATEMENT"
        },
        {
          "code": "INCOME_STABLE",
          "text": "Income volatility is low (9.9%), indicating predictable earnings",
          "source": "ACCOUNT_AGGREGATOR"
        },
        {
          "code": "COMMUNITY_VOUCH_ACTIVE",
          "text": "Endorsed by 2 active community member(s) with Vouch score 63.5",
          "source": "WEB_OF_TRUST_GRAPH"
        },
        {
          "code": "DISPOSABLE_INCOME_SUFFICIENT",
          "text": "Net disposable monthly surplus of INR 8,945.00 after non-discretionary expenses and buffer",
          "source": "AFFORDABILITY_ENGINE"
        }
      ],
      "risk_factors": [
        {
          "code": "AFFORDABILITY_DEFICIT",
          "text": "Requested instalment of INR 14,183.94 exceeds affordable limit of INR 8,945.00",
          "source": "AFFORDABILITY_ENGINE"
        }
      ],
      "missing_information": [
        "Credit bureau history is unavailable on file (thin-file applicant)"
      ],
      "review_flags": [
        "RESTRUCTURING_RECOMMENDED"
      ],
      "algorithm_version": "vouch-v2.0",
      "timestamp": "2026-10-25T16:40:49.452490Z"
    },
    "scenario": {
      "base_assessment_id": "ASM_023DD7331A99",
      "is_feasible": false,
      "monthly_emi": "14183.94",
      "residual_cash": "1316.06",
      "income_shock_margin": "5157.58",
      "binding_constraint": "INSTALMENT_CAP_DISPOSABLE_INCOME",
      "summary": "Requested monthly instalment of INR 14,183.94 exceeds your maximum affordable instalment of INR 8,945.00 by INR 5,238.94."
    },
    "predict": {
      "borrower_id": "LAKSHMI",
      "prediction": {
        "default_probability": 0.0127,
        "repayment_probability": 0.9873,
        "credit_score": 851,
        "risk_tier": "LOW_RISK",
        "decision": "DECLINE_CANDIDATE",
        "conformal_set": [
          "REPAY"
        ],
        "confidence_level": 0.9,
        "epistemic_uncertainty": 0.2703
      },
      "explanation": {
        "summary": "The requested loan does not fit: its EMI of INR 14,183.94 is above the maximum affordable instalment of INR 8,945.00 (DISPOSABLE_INCOME). Default probability on these terms is 1.3%; see the remedies for terms that fit.",
        "positive_factors": [
          {
            "code": "VOUCH_REPUTATION",
            "text": "Freshness-adjusted Web-of-Trust score: 63.5",
            "feature": "vouch_score",
            "observed": "63.5",
            "log_odds": -0.7,
            "direction": "lowers_risk"
          },
          {
            "code": "EMI_BOUNCE",
            "text": "Bounced auto-debits in the last 3 months: 0",
            "feature": "bank_bounces_3m",
            "observed": "0",
            "log_odds": -0.3,
            "direction": "lowers_risk"
          },
          {
            "code": "VOUCH_PRESENT",
            "text": "Community peer vouches: 2",
            "feature": "vouch_count",
            "observed": "2",
            "log_odds": -0.25,
            "direction": "lowers_risk"
          },
          {
            "code": "TENURE",
            "text": "Months in current occupation: 24 months",
            "feature": "occupation_tenure_months",
            "observed": "24 months",
            "log_odds": -0.25,
            "direction": "lowers_risk"
          },
          {
            "code": "INCOME_LEVEL",
            "text": "Estimated monthly income: INR 38,000.00",
            "feature": "income_est_minor",
            "observed": "INR 38,000.00",
            "log_odds": -0.2,
            "direction": "lowers_risk"
          },
          {
            "code": "INCOME_UNSTABLE",
            "text": "Month-to-month income variation: 0.10",
            "feature": "bank_income_cv",
            "observed": "0.10",
            "log_odds": -0.2,
            "direction": "lowers_risk"
          },
          {
            "code": "DTI_ABOVE_CAP",
            "text": "Debt-to-income after the new EMI: 0.43",
            "feature": "dti_est",
            "observed": "0.43",
            "log_odds": -0.15,
            "direction": "lowers_risk"
          },
          {
            "code": "MONTHLY_SURPLUS",
            "text": "Median monthly surplus before EMIs: INR 15,500.00",
            "feature": "bank_surplus_median_minor",
            "observed": "INR 15,500.00",
            "log_odds": -0.1,
            "direction": "lowers_risk"
          }
        ],
        "risk_factors": [
          {
            "code": "AMOUNT_TO_INCOME_HIGH",
            "text": "Requested amount relative to income: 3.95",
            "feature": "amount_to_income",
            "observed": "3.95",
            "log_odds": 0.05,
            "direction": "raises_risk"
          }
        ],
        "missing_information": [
          {
            "code": "MISSING_BUREAU_FILE",
            "text": "Credit bureau history is unavailable on file (thin-file applicant; alternative cash-flow and vouch evidence utilized)",
            "status": "NO_FILE"
          },
          {
            "code": "MISSING_GST",
            "text": "GST filings do not apply to this micro-enterprise category",
            "status": "NOT_APPLICABLE"
          }
        ]
      },
      "temporal_freshness": {
        "evidence_age_months": 0.0,
        "vouch_confidence": 1.0,
        "cashflow_confidence": 1.0,
        "repayment_confidence": 1.0,
        "composite_confidence": 1.0,
        "is_stale": false,
        "staleness_warning": null
      },
      "multidimensional_scores": {
        "financial_capacity_score": 47.3,
        "evidence_reliability_score": 75.0,
        "graph_reputation_score": 63.5,
        "stress_resilience_score": 16.7
      },
      "counterfactual_remedy": {
        "target_decision": "ELIGIBLE",
        "is_already_eligible": false,
        "max_recommended_principal": "94596.43",
        "recommended_tenure_months": 24,
        "sustainable_emi": "8945.00",
        "required_additional_monthly_income": "14968.40",
        "actionable_recommendations": [
          "Reduce requested principal from INR 150,000.00 to INR 94,596.43 to align monthly EMI with sustainable disposable cash flow.",
          "Extend loan tenure from 12 to 24 months, lowering monthly EMI to INR 7,930.66.",
          "Add 1 to 2 community endorsements from active guild anchors to boost Graph Reputation score above 50.0.",
          "An additional verified monthly income of INR 14,968.40 would satisfy underwriting bounds."
        ]
      }
    }
  },
  "SURESH": {
    "applicationId": "APP_DA9721CB",
    "result": {
      "assessment_id": "ASM_88C99297970F",
      "application_id": "APP_DA9721CB",
      "borrower_id": "SURESH",
      "verdict": "RESTRUCTURED_ALTERNATIVE",
      "bureau_status": "NO_FILE",
      "bureau_score": null,
      "vouch_score": "63.5",
      "affordability": {
        "gross_monthly_income": "32000.00",
        "non_discretionary_outflows": "25500.00",
        "disposable_income": "980.00",
        "max_affordable_emi": "980.00",
        "protected_cash_buffer": "5520.00",
        "status": "BORDERLINE",
        "binding_rule": "DISPOSABLE_INCOME"
      },
      "best_plan": {
        "principal": "30000.00",
        "term_months": 48,
        "monthly_emi": "978.06",
        "total_interest": "16946.88"
      },
      "stress_resilience": {
        "rating": "FRAGILE",
        "shortfall_probability": 0.163,
        "adverse_5th_percentile_cash": "-4698.98",
        "income_shock_tolerance_percent": 17.26
      },
      "reason_codes": [
        "INCOME_PRESENT",
        "INCOME_STABLE",
        "COMMUNITY_VOUCH_ACTIVE",
        "DISPOSABLE_INCOME_SUFFICIENT",
        "AFFORDABILITY_DEFICIT",
        "STRESS_TEST_FRAGILE"
      ],
      "positive_factors": [
        {
          "code": "INCOME_PRESENT",
          "text": "Verified recurring monthly income of INR 32,000.00 documented",
          "source": "BANK_STATEMENT"
        },
        {
          "code": "INCOME_STABLE",
          "text": "Income volatility is low (15.0%), indicating predictable earnings",
          "source": "ACCOUNT_AGGREGATOR"
        },
        {
          "code": "COMMUNITY_VOUCH_ACTIVE",
          "text": "Endorsed by 1 active community member(s) with Vouch score 63.5",
          "source": "WEB_OF_TRUST_GRAPH"
        },
        {
          "code": "DISPOSABLE_INCOME_SUFFICIENT",
          "text": "Net disposable monthly surplus of INR 980.00 after non-discretionary expenses and buffer",
          "source": "AFFORDABILITY_ENGINE"
        }
      ],
      "risk_factors": [
        {
          "code": "AFFORDABILITY_DEFICIT",
          "text": "Requested instalment of INR 14,183.94 exceeds affordable limit of INR 980.00",
          "source": "AFFORDABILITY_ENGINE"
        }
      ],
      "missing_information": [
        "Credit bureau history is unavailable on file (thin-file applicant)"
      ],
      "review_flags": [
        "RESTRUCTURING_RECOMMENDED"
      ]
    },
    "detail": {
      "assessment_id": "ASM_88C99297970F",
      "application_id": "APP_DA9721CB",
      "borrower_id": "SURESH",
      "bureau": {
        "status": "NO_FILE",
        "score": null,
        "source": null,
        "as_of": null
      },
      "vouch": {
        "vouch_score": "63.5",
        "status": "ACTIVE",
        "confidence": "MEDIUM",
        "eligible_endorsements": 1,
        "raw_support": "0.9412",
        "quality_factor": "0.5000"
      },
      "affordability": {
        "status": "BORDERLINE",
        "gross_monthly_income": "32000.00",
        "non_discretionary_outflows": "25500.00",
        "disposable_income": "980.00",
        "protected_cash_buffer": "4800.00",
        "max_affordable_emi": "980.00",
        "binding_constraint": "DISPOSABLE_INCOME"
      },
      "data_quality": "MEDIUM",
      "positive_factors": [
        {
          "code": "INCOME_PRESENT",
          "text": "Verified recurring monthly income of INR 32,000.00 documented",
          "source": "BANK_STATEMENT"
        },
        {
          "code": "INCOME_STABLE",
          "text": "Income volatility is low (15.0%), indicating predictable earnings",
          "source": "ACCOUNT_AGGREGATOR"
        },
        {
          "code": "COMMUNITY_VOUCH_ACTIVE",
          "text": "Endorsed by 1 active community member(s) with Vouch score 63.5",
          "source": "WEB_OF_TRUST_GRAPH"
        },
        {
          "code": "DISPOSABLE_INCOME_SUFFICIENT",
          "text": "Net disposable monthly surplus of INR 980.00 after non-discretionary expenses and buffer",
          "source": "AFFORDABILITY_ENGINE"
        }
      ],
      "risk_factors": [
        {
          "code": "AFFORDABILITY_DEFICIT",
          "text": "Requested instalment of INR 14,183.94 exceeds affordable limit of INR 980.00",
          "source": "AFFORDABILITY_ENGINE"
        }
      ],
      "missing_information": [
        "Credit bureau history is unavailable on file (thin-file applicant)"
      ],
      "review_flags": [
        "RESTRUCTURING_RECOMMENDED"
      ],
      "algorithm_version": "vouch-v2.0",
      "timestamp": "2026-10-25T16:40:49.672265Z"
    },
    "scenario": {
      "base_assessment_id": "ASM_88C99297970F",
      "is_feasible": false,
      "monthly_emi": "14183.94",
      "residual_cash": "-7683.94",
      "income_shock_margin": "14686.99",
      "binding_constraint": "INSTALMENT_CAP_DISPOSABLE_INCOME",
      "summary": "Requested monthly instalment of INR 14,183.94 exceeds your maximum affordable instalment of INR 980.00 by INR 13,203.94."
    },
    "predict": {
      "borrower_id": "SURESH",
      "prediction": {
        "default_probability": 0.1611,
        "repayment_probability": 0.8389,
        "credit_score": 695,
        "risk_tier": "HIGH_RISK",
        "decision": "DECLINE_CANDIDATE",
        "conformal_set": [
          "REPAY"
        ],
        "confidence_level": 0.9,
        "epistemic_uncertainty": 0.3571
      },
      "explanation": {
        "summary": "The requested loan does not fit: its EMI of INR 14,183.94 is above the maximum affordable instalment of INR 980.00 (DISPOSABLE_INCOME). Default probability on these terms is 16.1%; see the remedies for terms that fit.",
        "positive_factors": [
          {
            "code": "VOUCH_REPUTATION",
            "text": "Freshness-adjusted Web-of-Trust score: 63.5",
            "feature": "vouch_score",
            "observed": "63.5",
            "log_odds": -0.7,
            "direction": "lowers_risk"
          },
          {
            "code": "EMI_BOUNCE",
            "text": "Bounced auto-debits in the last 3 months: 0",
            "feature": "bank_bounces_3m",
            "observed": "0",
            "log_odds": -0.3,
            "direction": "lowers_risk"
          },
          {
            "code": "VOUCH_PRESENT",
            "text": "Community peer vouches: 1",
            "feature": "vouch_count",
            "observed": "1",
            "log_odds": -0.25,
            "direction": "lowers_risk"
          },
          {
            "code": "TENURE",
            "text": "Months in current occupation: 24 months",
            "feature": "occupation_tenure_months",
            "observed": "24 months",
            "log_odds": -0.25,
            "direction": "lowers_risk"
          },
          {
            "code": "INCOME_LEVEL",
            "text": "Estimated monthly income: INR 32,000.00",
            "feature": "income_est_minor",
            "observed": "INR 32,000.00",
            "log_odds": -0.2,
            "direction": "lowers_risk"
          },
          {
            "code": "INCOME_UNSTABLE",
            "text": "Month-to-month income variation: 0.10",
            "feature": "bank_income_cv",
            "observed": "0.10",
            "log_odds": -0.2,
            "direction": "lowers_risk"
          }
        ],
        "risk_factors": [
          {
            "code": "DTI_ABOVE_CAP",
            "text": "Debt-to-income after the new EMI: 0.74",
            "feature": "dti_est",
            "observed": "0.74",
            "log_odds": 1.4,
            "direction": "raises_risk"
          },
          {
            "code": "MONTHLY_SURPLUS",
            "text": "Median monthly surplus before EMIs: INR 6,500.00",
            "feature": "bank_surplus_median_minor",
            "observed": "INR 6,500.00",
            "log_odds": 0.6,
            "direction": "raises_risk"
          },
          {
            "code": "AMOUNT_TO_INCOME_HIGH",
            "text": "Requested amount relative to income: 4.69",
            "feature": "amount_to_income",
            "observed": "4.69",
            "log_odds": 0.5,
            "direction": "raises_risk"
          }
        ],
        "missing_information": [
          {
            "code": "MISSING_BUREAU_FILE",
            "text": "Credit bureau history is unavailable on file (thin-file applicant; alternative cash-flow and vouch evidence utilized)",
            "status": "NO_FILE"
          },
          {
            "code": "MISSING_GST",
            "text": "GST filings do not apply to this micro-enterprise category",
            "status": "NOT_APPLICABLE"
          }
        ]
      },
      "temporal_freshness": {
        "evidence_age_months": 0.0,
        "vouch_confidence": 1.0,
        "cashflow_confidence": 1.0,
        "repayment_confidence": 1.0,
        "composite_confidence": 1.0,
        "is_stale": false,
        "staleness_warning": null
      },
      "multidimensional_scores": {
        "financial_capacity_score": 5.2,
        "evidence_reliability_score": 75.0,
        "graph_reputation_score": 63.5,
        "stress_resilience_score": 0.2
      },
      "counterfactual_remedy": {
        "target_decision": "ELIGIBLE",
        "is_already_eligible": false,
        "max_recommended_principal": "10363.83",
        "recommended_tenure_months": 12,
        "sustainable_emi": "980.00",
        "required_additional_monthly_income": "37725.54",
        "actionable_recommendations": [
          "Reduce requested principal from INR 150,000.00 to INR 10,363.83 to align monthly EMI with sustainable disposable cash flow.",
          "Add 1 to 2 community endorsements from active guild anchors to boost Graph Reputation score above 50.0.",
          "An additional verified monthly income of INR 37,725.54 would satisfy underwriting bounds."
        ]
      }
    }
  },
  "IMRAN": {
    "applicationId": "APP_B4019903",
    "result": {
      "assessment_id": "ASM_A1E770768A09",
      "application_id": "APP_B4019903",
      "borrower_id": "IMRAN",
      "verdict": "RESTRUCTURED_ALTERNATIVE",
      "bureau_status": "NO_FILE",
      "bureau_score": null,
      "vouch_score": "0.0",
      "affordability": {
        "gross_monthly_income": "22000.00",
        "non_discretionary_outflows": "10000.00",
        "disposable_income": "8205.00",
        "max_affordable_emi": "8205.00",
        "protected_cash_buffer": "3795.00",
        "status": "SUFFICIENT",
        "binding_rule": "DISPOSABLE_INCOME"
      },
      "best_plan": null,
      "stress_resilience": {
        "rating": "FRAGILE",
        "shortfall_probability": 0.9975,
        "adverse_5th_percentile_cash": "-14400.06",
        "income_shock_tolerance_percent": 0.0
      },
      "reason_codes": [
        "INCOME_PRESENT",
        "INCOME_STABLE",
        "DISPOSABLE_INCOME_SUFFICIENT",
        "AFFORDABILITY_DEFICIT",
        "STRESS_TEST_FRAGILE"
      ],
      "positive_factors": [
        {
          "code": "INCOME_PRESENT",
          "text": "Verified recurring monthly income of INR 22,000.00 documented",
          "source": "BANK_STATEMENT"
        },
        {
          "code": "INCOME_STABLE",
          "text": "Income volatility is low (15.0%), indicating predictable earnings",
          "source": "ACCOUNT_AGGREGATOR"
        },
        {
          "code": "DISPOSABLE_INCOME_SUFFICIENT",
          "text": "Net disposable monthly surplus of INR 8,205.00 after non-discretionary expenses and buffer",
          "source": "AFFORDABILITY_ENGINE"
        }
      ],
      "risk_factors": [
        {
          "code": "AFFORDABILITY_DEFICIT",
          "text": "Requested instalment of INR 14,183.94 exceeds affordable limit of INR 8,205.00",
          "source": "AFFORDABILITY_ENGINE"
        }
      ],
      "missing_information": [
        "Credit bureau history is unavailable on file (thin-file applicant)",
        "Living costs and cash-flow statements not fully documented",
        "Operating costs not shared: a conservative INR 10,000 a month is assumed"
      ],
      "review_flags": [
        "DATA_COMPLETENESS_REVIEW",
        "RESTRUCTURING_RECOMMENDED"
      ]
    },
    "detail": {
      "assessment_id": "ASM_A1E770768A09",
      "application_id": "APP_B4019903",
      "borrower_id": "IMRAN",
      "bureau": {
        "status": "NO_FILE",
        "score": null,
        "source": null,
        "as_of": null
      },
      "vouch": {
        "vouch_score": "0.0",
        "status": "PROVISIONAL",
        "confidence": "LOW",
        "eligible_endorsements": 0,
        "raw_support": "0.0000",
        "quality_factor": "0.5000"
      },
      "affordability": {
        "status": "SUFFICIENT",
        "gross_monthly_income": "22000.00",
        "non_discretionary_outflows": "10000.00",
        "disposable_income": "8205.00",
        "protected_cash_buffer": "3300.00",
        "max_affordable_emi": "8205.00",
        "binding_constraint": "DISPOSABLE_INCOME"
      },
      "data_quality": "MEDIUM",
      "positive_factors": [
        {
          "code": "INCOME_PRESENT",
          "text": "Verified recurring monthly income of INR 22,000.00 documented",
          "source": "BANK_STATEMENT"
        },
        {
          "code": "INCOME_STABLE",
          "text": "Income volatility is low (15.0%), indicating predictable earnings",
          "source": "ACCOUNT_AGGREGATOR"
        },
        {
          "code": "DISPOSABLE_INCOME_SUFFICIENT",
          "text": "Net disposable monthly surplus of INR 8,205.00 after non-discretionary expenses and buffer",
          "source": "AFFORDABILITY_ENGINE"
        }
      ],
      "risk_factors": [
        {
          "code": "AFFORDABILITY_DEFICIT",
          "text": "Requested instalment of INR 14,183.94 exceeds affordable limit of INR 8,205.00",
          "source": "AFFORDABILITY_ENGINE"
        }
      ],
      "missing_information": [
        "Credit bureau history is unavailable on file (thin-file applicant)",
        "Living costs and cash-flow statements not fully documented",
        "Operating costs not shared: a conservative INR 10,000 a month is assumed"
      ],
      "review_flags": [
        "DATA_COMPLETENESS_REVIEW",
        "RESTRUCTURING_RECOMMENDED"
      ],
      "algorithm_version": "vouch-v2.0",
      "timestamp": "2026-10-25T16:40:49.940098Z"
    },
    "scenario": {
      "base_assessment_id": "ASM_A1E770768A09",
      "is_feasible": false,
      "monthly_emi": "14183.94",
      "residual_cash": "-2183.94",
      "income_shock_margin": "13459.85",
      "binding_constraint": "INSTALMENT_CAP_DISPOSABLE_INCOME",
      "summary": "Requested monthly instalment of INR 14,183.94 exceeds your maximum affordable instalment of INR 8,205.00 by INR 5,978.94. Requested principal of INR 150,000.00 exceeds your approved credit ceiling of INR 0.00 by INR 150,000.00."
    },
    "predict": {
      "borrower_id": "IMRAN",
      "prediction": {
        "default_probability": 0.4626,
        "repayment_probability": 0.5374,
        "credit_score": 609,
        "risk_tier": "VERY_HIGH_RISK",
        "decision": "DECLINE_CANDIDATE",
        "conformal_set": [
          "REPAY",
          "DEFAULT"
        ],
        "confidence_level": 0.9,
        "epistemic_uncertainty": 0.5714
      },
      "explanation": {
        "summary": "The requested loan does not fit: its EMI of INR 14,183.94 is above the maximum affordable instalment of INR 8,205.00 (DISPOSABLE_INCOME). Default probability on these terms is 46.3%; see the remedies for terms that fit.",
        "positive_factors": [
          {
            "code": "EMI_BOUNCE",
            "text": "Bounced auto-debits in the last 3 months: 0",
            "feature": "bank_bounces_3m",
            "observed": "0",
            "log_odds": -0.3,
            "direction": "lowers_risk"
          },
          {
            "code": "TENURE",
            "text": "Months in current occupation: 24 months",
            "feature": "occupation_tenure_months",
            "observed": "24 months",
            "log_odds": -0.25,
            "direction": "lowers_risk"
          },
          {
            "code": "INCOME_UNSTABLE",
            "text": "Month-to-month income variation: 0.10",
            "feature": "bank_income_cv",
            "observed": "0.10",
            "log_odds": -0.2,
            "direction": "lowers_risk"
          },
          {
            "code": "INCOME_LEVEL",
            "text": "Estimated monthly income: INR 22,000.00",
            "feature": "income_est_minor",
            "observed": "INR 22,000.00",
            "log_odds": 0.0,
            "direction": "lowers_risk"
          }
        ],
        "risk_factors": [
          {
            "code": "DTI_ABOVE_CAP",
            "text": "Debt-to-income after the new EMI: 0.64",
            "feature": "dti_est",
            "observed": "0.64",
            "log_odds": 1.4,
            "direction": "raises_risk"
          },
          {
            "code": "MONTHLY_SURPLUS",
            "text": "Median monthly surplus before EMIs: INR 12,000.00",
            "feature": "bank_surplus_median_minor",
            "observed": "INR 12,000.00",
            "log_odds": 0.6,
            "direction": "raises_risk"
          },
          {
            "code": "AMOUNT_TO_INCOME_HIGH",
            "text": "Requested amount relative to income: 6.82",
            "feature": "amount_to_income",
            "observed": "6.82",
            "log_odds": 0.5,
            "direction": "raises_risk"
          },
          {
            "code": "VOUCH_PRESENT",
            "text": "Community peer vouches: 0",
            "feature": "vouch_count",
            "observed": "0",
            "log_odds": 0.2,
            "direction": "raises_risk"
          },
          {
            "code": "VOUCH_REPUTATION",
            "text": "Freshness-adjusted Web-of-Trust score: 0.0",
            "feature": "vouch_score",
            "observed": "0.0",
            "log_odds": 0.15,
            "direction": "raises_risk"
          }
        ],
        "missing_information": [
          {
            "code": "MISSING_BUREAU_FILE",
            "text": "Credit bureau history is unavailable on file (thin-file applicant; alternative cash-flow and vouch evidence utilized)",
            "status": "NO_FILE"
          },
          {
            "code": "MISSING_GST",
            "text": "GST filings do not apply to this micro-enterprise category",
            "status": "NOT_APPLICABLE"
          }
        ]
      },
      "temporal_freshness": {
        "evidence_age_months": 0.0,
        "vouch_confidence": 1.0,
        "cashflow_confidence": 1.0,
        "repayment_confidence": 1.0,
        "composite_confidence": 1.0,
        "is_stale": false,
        "staleness_warning": null
      },
      "multidimensional_scores": {
        "financial_capacity_score": 43.4,
        "evidence_reliability_score": 75.0,
        "graph_reputation_score": 0.0,
        "stress_resilience_score": 16.1
      },
      "counterfactual_remedy": {
        "target_decision": "ELIGIBLE",
        "is_already_eligible": false,
        "max_recommended_principal": "86770.67",
        "recommended_tenure_months": 24,
        "sustainable_emi": "8205.00",
        "required_additional_monthly_income": "17082.69",
        "actionable_recommendations": [
          "Reduce requested principal from INR 150,000.00 to INR 86,770.67 to align monthly EMI with sustainable disposable cash flow.",
          "Extend loan tenure from 12 to 24 months, lowering monthly EMI to INR 7,930.66.",
          "Add 1 to 2 community endorsements from active guild anchors to boost Graph Reputation score above 50.0.",
          "An additional verified monthly income of INR 17,082.69 would satisfy underwriting bounds."
        ]
      }
    }
  }
};
