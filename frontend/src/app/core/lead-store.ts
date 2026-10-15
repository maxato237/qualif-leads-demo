import { Injectable, computed, inject, signal } from '@angular/core';

import { ApiFailure, LeadRequest, QualifiedLead } from './api/api.models';
import { LeadsApi, toApiFailure } from './api/leads-api';

type Phase = 'idle' | 'loading' | 'done' | 'error';

/** État de la démo : une demande à la fois, son résultat ou son erreur. */
@Injectable({ providedIn: 'root' })
export class LeadStore {
  private readonly api = inject(LeadsApi);

  private readonly phaseState = signal<Phase>('idle');
  private readonly resultState = signal<QualifiedLead | null>(null);
  private readonly failureState = signal<ApiFailure | null>(null);
  private readonly sheetUrlState = signal<string | null>(null);
  private lastRequest: LeadRequest | null = null;

  readonly phase = this.phaseState.asReadonly();
  readonly result = this.resultState.asReadonly();
  readonly failure = this.failureState.asReadonly();
  readonly sheetUrl = this.sheetUrlState.asReadonly();
  readonly pending = computed(() => this.phaseState() === 'loading');

  loadHealth(): void {
    this.api.health().subscribe({
      next: (health) => this.sheetUrlState.set(health.sheet_url),
      // Sans réponse, la démo reste utilisable : seul le lien vers le Sheet manque.
      error: () => this.sheetUrlState.set(null),
    });
  }

  submit(request: LeadRequest): void {
    if (this.pending()) {
      return;
    }
    this.lastRequest = request;
    this.phaseState.set('loading');
    this.failureState.set(null);
    this.api.qualify(request).subscribe({
      next: (result) => {
        this.resultState.set(result);
        if (result.delivery.sheet_url) {
          this.sheetUrlState.set(result.delivery.sheet_url);
        }
        this.phaseState.set('done');
      },
      error: (error) => {
        this.failureState.set(toApiFailure(error));
        this.phaseState.set('error');
      },
    });
  }

  retry(): void {
    if (this.lastRequest) {
      this.submit(this.lastRequest);
    }
  }

  reset(): void {
    this.phaseState.set('idle');
    this.resultState.set(null);
    this.failureState.set(null);
  }
}
