/**
 * Typed calls to the live FastAPI backend (`backend/src/veritrust/api/routes.py`). Request bodies
 * come from the generated OpenAPI types (`make types`); most responses have no `response_model`
 * in the backend yet, so their shapes are written here from routes.py and must follow it.
 * Money arrives as decimal strings in rupees; it is never turned into a JS number here.
 */
import { request } from './http';
import type { components } from '@/types/api';

type Schemas = components['schemas'];
export type CreateApplicationRequest = Schemas['CreateApplicationRequest'];
export type RunAssessmentRequest = Schemas['RunAssessmentRequest'];
export type ScenarioRequest = Schemas['ScenarioSimRequest'];
export type BureauStatus = NonNullable<RunAssessmentRequest['bureau_status']>;
export type ApplicationResponse = Schemas['ApplicationResponse'];
export type VouchSummary = Schemas['VouchSummaryResponse'];

export interface Health {
  status: string;
  version: string;
  timestamp: string;
}

export interface BackendUser {
  user_id: string;
  name: string;
  reputation: string;
  capacity: string;
  status: string;
  is_anchor: boolean;
  n_settled_loans: number;
}

/** One reason code with the evidence it rests on (backend `assess_combined`). */
export interface Factor {
  code: string;
  text: string;
  source: string;
}

/** `POST /api/v1/applications/{id}/assessments` (routes.py `run_assessment`). */
export interface AssessmentResult {
  assessment_id: string;
  application_id: string;
  borrower_id: string;
  verdict: 'APPROVED' | 'RESTRUCTURED_ALTERNATIVE';
  bureau_status: BureauStatus;
  bureau_score: number | null;
  vouch_score: number;
  affordability: {
    disposable_income: string;
    max_affordable_emi: string;
    protected_cash_buffer: string;
    status: string;
  };
  best_plan: {
    principal: string | null;
    term_months: number | null;
    monthly_emi: string | null;
    total_interest: string | null;
  } | null;
  stress_resilience: {
    rating: string;
    shortfall_probability: number;
    adverse_5th_percentile_cash: string;
    income_shock_tolerance_percent: number;
  } | null;
  positive_factors: Factor[];
  risk_factors: Factor[];
  missing_information: string[];
  review_flags: string[];
}

/** `GET /api/v1/assessments/{id}`: the stored side-by-side record, used for the vouch detail. */
export interface CombinedAssessment {
  assessment_id: string;
  borrower_id: string;
  bureau: { status: BureauStatus; score: number | null; source: string | null };
  vouch: {
    vouch_score: string;
    status: 'PROVISIONAL' | 'ACTIVE' | 'RESTRICTED';
    confidence: 'LOW' | 'MEDIUM' | 'HIGH';
    eligible_endorsements: number;
    raw_support: string;
    quality_factor: string;
  };
  data_quality: 'HIGH_CONFIDENCE_VERIFIED' | 'MEDIUM' | 'LOW';
  algorithm_version: string;
}

/** `POST /api/v1/assessments/{id}/scenarios` (routes.py `run_scenario`). */
export interface ScenarioResult {
  base_assessment_id: string;
  is_feasible: boolean;
  monthly_emi: string;
  residual_cash: string;
  income_shock_margin: string;
  binding_constraint: string;
  summary: string;
}

export const backend = {
  health: () => request<Health>('GET', '/health', undefined, 2500),
  users: () => request<BackendUser[]>('GET', '/api/v1/users'),
  vouchSummary: (userId: string) => request<VouchSummary>('GET', `/api/v1/users/${encodeURIComponent(userId)}/vouch-summary`),
  createApplication: (body: CreateApplicationRequest) => request<ApplicationResponse>('POST', '/api/v1/applications', body),
  // The stress test runs thousands of Monte Carlo paths, so it gets a longer timeout.
  runAssessment: (applicationId: string, body: RunAssessmentRequest) =>
    request<AssessmentResult>('POST', `/api/v1/applications/${encodeURIComponent(applicationId)}/assessments`, body, 30_000),
  assessment: (assessmentId: string) => request<CombinedAssessment>('GET', `/api/v1/assessments/${encodeURIComponent(assessmentId)}`),
  scenario: (assessmentId: string, body: ScenarioRequest) =>
    request<ScenarioResult>('POST', `/api/v1/assessments/${encodeURIComponent(assessmentId)}/scenarios`, body),
};
