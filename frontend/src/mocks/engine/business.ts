/**
 * Vouch's price card for the landing page's business-model section, from the team's business model
 * (frontend/Vouch_Business_Model.md, sections 5 and 6). Planning assumptions in whole INR, not
 * market prices or customer commitments.
 */
import { D, Decimal } from './params';

export type Model = 'owned' | 'platform';

export const PRICES: Record<Model, { setup: Decimal; recurringPerYear: Decimal; perAssessment: Decimal }> = {
  /** Model A, institution-owned: implementation fee, annual licence, usage fee. */
  owned: { setup: D(300000), recurringPerYear: D(480000), perAssessment: D(10) },
  /** Model B, independent platform: onboarding fee, ₹30,000 a month subscription, usage fee. */
  platform: { setup: D(150000), recurringPerYear: D(30000).mul(12), perAssessment: D(10) },
};
