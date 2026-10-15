export interface LeadRequest {
  name: string;
  email: string;
  company: string;
  message: string;
  website: string;
}

export type Category = 'chaud' | 'tiede' | 'froid' | 'hors_cible';
export type DeliveryStatus = 'sent' | 'failed' | 'disabled';

export interface Criterion {
  key: string;
  label: string;
  points: number;
  max_points: number;
  reason: string;
}

export interface QualifiedLead {
  score: { value: number; category: Category; criteria: Criterion[] };
  lead: {
    in_scope: boolean;
    project_type: string;
    project_label: string;
    need: string;
    budget: string;
    deadline: string | null;
    urgency: 'immediate' | 'short' | 'flexible' | 'unknown';
    is_decision_maker: boolean | null;
    clarity: 'precise' | 'partial' | 'vague';
    red_flags: string[];
    summary: string;
    next_action: string;
  };
  delivery: { email: DeliveryStatus; sheet: DeliveryStatus; sheet_url: string | null };
  latency_ms: number;
}

export interface Health {
  status: 'ok';
  sheet_url: string | null;
  email_enabled: boolean;
}

export type LeadField = 'name' | 'email' | 'company' | 'message';

export interface FieldError {
  field: LeadField;
  message: string;
}

export type ApiErrorCode =
  | 'invalid_lead'
  | 'spam_detected'
  | 'rate_limited'
  | 'demo_paused'
  | 'llm_unavailable'
  | 'internal_error'
  | 'network';

export interface ApiFailure {
  code: ApiErrorCode;
  fields: FieldError[];
}
