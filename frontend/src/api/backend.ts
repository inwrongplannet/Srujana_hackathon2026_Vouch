/**
 * Typed calls to the live FastAPI backend (`backend/src/veritrust/api/`). Every request and
 * response type comes from the generated OpenAPI types (`make types` -> `src/types/api.d.ts`);
 * nothing here is hand-written. Money, scores and weights arrive as decimal strings and are never
 * turned into JS numbers here.
 */
import { request } from './http';
import type { components } from '@/types/api';

type Schemas = components['schemas'];
export type Health = Schemas['HealthResponse'];
export type BackendUser = Schemas['UserSummary'];
export type VouchSummary = Schemas['VouchSummaryResponse'];
export type CreateApplicationRequest = Schemas['CreateApplicationRequest'];
export type ApplicationResponse = Schemas['ApplicationResponse'];
export type RunAssessmentRequest = Schemas['RunAssessmentRequest'];
export type BureauStatus = NonNullable<RunAssessmentRequest['bureau_status']>;
export type AssessmentResult = Schemas['AssessmentResponse'];
export type Factor = Schemas['ReasonFactor'];
export type CombinedAssessment = Schemas['CombinedAssessment'];
export type ScenarioRequest = Schemas['ScenarioSimRequest'];
export type ScenarioResult = Schemas['ScenarioResponse'];
export type Decision = Schemas['DecisionRequest']['decision'];
export type DecisionResult = Schemas['DecisionResponse'];
export type DefaultResult = Schemas['DefaultResponse'];
export type VouchRequest = Schemas['VouchRequestResponse'];
export type CommunityMember = Schemas['MemberView'];
export type CommunityAsk = Schemas['AskView'];
export type CommunityVouch = Schemas['VouchBody'];
export type VouchPreview = Schemas['PreviewView'];
export type PredictRequest = Schemas['PredictRequest'];
export type PredictResponse = Schemas['PredictResponse'];
export type PlatformTreasury = Schemas['PlatformTreasurySummary'];
export type TransactionSummary = Schemas['TransactionSummary'];
export type RepayResponse = Schemas['RepayResponse'];
export type LoanSummary = Schemas['LoanSummary'];

const enc = encodeURIComponent;
const viewer = (viewerId?: string) => (viewerId ? `?viewer_id=${enc(viewerId)}` : '');

export const backend = {
  health: () => request<Health>('GET', '/health', undefined, 2500),
  users: () => request<BackendUser[]>('GET', '/api/v1/users'),
  vouchSummary: (userId: string) => request<VouchSummary>('GET', `/api/v1/users/${enc(userId)}/vouch-summary`),

  createApplication: (body: CreateApplicationRequest) => request<ApplicationResponse>('POST', '/api/v1/applications', body),
  // The stress test runs thousands of Monte Carlo paths, so it gets a longer timeout.
  runAssessment: (applicationId: string, body: RunAssessmentRequest) =>
    request<AssessmentResult>('POST', `/api/v1/applications/${enc(applicationId)}/assessments`, body, 30_000),
  assessment: (assessmentId: string) => request<CombinedAssessment>('GET', `/api/v1/assessments/${enc(assessmentId)}`),
  scenario: (assessmentId: string, body: ScenarioRequest) =>
    request<ScenarioResult>('POST', `/api/v1/assessments/${enc(assessmentId)}/scenarios`, body),
  decide: (applicationId: string, decision: Decision) =>
    request<DecisionResult>('POST', `/api/v1/applications/${enc(applicationId)}/decision`, { decision }),
  defaultLoan: (loanId: string, delta0?: string) => request<DefaultResult>('POST', `/api/v1/loans/${enc(loanId)}/default`, { delta0 }),
  loans: () => request<LoanSummary[]>('GET', '/api/v1/loans'),
  repay: (loanId: string, amount: string) => request<RepayResponse>('POST', '/api/v1/loans/repay', { loan_id: loanId, amount }),
  treasury: () => request<PlatformTreasury>('GET', '/api/v1/platform/treasury'),
  transactions: () => request<TransactionSummary[]>('GET', '/api/v1/transactions'),
  // Every PredictRequest field has a backend default (or a lookup by borrower_id), so callers send only what they know.
  predict: (body: Partial<PredictRequest>) => request<PredictResponse>('POST', '/api/v1/predict', body),
  predictSample: () => request<PredictRequest>('GET', '/api/v1/predict/sample'),

  askForVouch: (requesterId: string, voucherId: string, note: string) =>
    request<VouchRequest>('POST', '/api/v1/vouch-requests', { requester_id: requesterId, voucher_id: voucherId, note }),
  vouchRequests: (voucherId: string) => request<VouchRequest[]>('GET', `/api/v1/vouch-requests?voucher_id=${enc(voucherId)}`),
  answerVouch: (requestId: string, accept: boolean) =>
    request<VouchRequest>('POST', `/api/v1/vouch-requests/${enc(requestId)}/respond`, { accept }),

  community: {
    members: () => request<CommunityMember[]>('GET', '/api/v1/community/members'),
    asks: (viewerId?: string) => request<CommunityAsk[]>('GET', `/api/v1/community/asks${viewer(viewerId)}`),
    ask: (askId: string, viewerId?: string) => request<CommunityAsk>('GET', `/api/v1/community/asks/${enc(askId)}${viewer(viewerId)}`),
    preview: (askId: string, body: CommunityVouch) => request<VouchPreview>('POST', `/api/v1/community/asks/${enc(askId)}/vouch-preview`, body),
    vouch: (askId: string, body: CommunityVouch) => request<CommunityAsk>('POST', `/api/v1/community/asks/${enc(askId)}/vouches`, body),
    postSetback: (askId: string, text: string) => request<CommunityAsk>('POST', `/api/v1/community/asks/${enc(askId)}/setback`, { text }),
    respond: (askId: string, voucherId: string, choice: 'STAND_BY' | 'STEP_BACK') =>
      request<CommunityAsk>('POST', `/api/v1/community/asks/${enc(askId)}/setback/respond`, { voucher_id: voucherId, choice }),
    setShown: (askId: string, key: string, shown: boolean) =>
      request<CommunityAsk>('POST', `/api/v1/community/asks/${enc(askId)}/verified/${enc(key)}`, { shown }),
  },
};
