import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ApiErrorCode, ApiFailure, Health, LeadRequest, QualifiedLead } from './api.models';

const KNOWN_CODES: ApiErrorCode[] = [
  'invalid_lead',
  'spam_detected',
  'rate_limited',
  'demo_paused',
  'llm_unavailable',
  'internal_error',
];

/**
 * Statuts dont le corps peut être remplacé en route : Cloudflare, devant
 * Sevalla, sert sa propre page HTML à la place des 502 et 504 de l'origine.
 * Le code métier est alors perdu, le statut suffit à le retrouver.
 */
const STATUS_FALLBACK: Partial<Record<number, ApiErrorCode>> = {
  502: 'llm_unavailable',
  504: 'llm_unavailable',
};

@Injectable({ providedIn: 'root' })
export class LeadsApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  health(): Observable<Health> {
    return this.http.get<Health>(`${this.baseUrl}/api/health`);
  }

  qualify(request: LeadRequest): Observable<QualifiedLead> {
    return this.http.post<QualifiedLead>(`${this.baseUrl}/api/leads`, request);
  }
}

/** Traduit une erreur HTTP en code métier de l'API (format {"error": {"code", "fields"?}}). */
export function toApiFailure(error: unknown): ApiFailure {
  if (!(error instanceof HttpErrorResponse) || error.status === 0) {
    return { code: 'network', fields: [] };
  }
  const body = error.error?.error;
  const fields = Array.isArray(body?.fields) ? body.fields : [];
  if (KNOWN_CODES.includes(body?.code)) {
    return { code: body.code, fields };
  }
  return { code: STATUS_FALLBACK[error.status] ?? 'internal_error', fields: [] };
}
