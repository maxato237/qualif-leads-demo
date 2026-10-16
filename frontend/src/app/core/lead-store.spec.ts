import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { LeadRequest, QualifiedLead } from './api/api.models';
import { LeadStore } from './lead-store';

const REQUEST: LeadRequest = {
  name: 'Claire Martin',
  email: 'claire.martin@example.com',
  company: 'Cave des Chartrons',
  message: 'Boutique en ligne avant le 1er décembre, budget 12 à 18 k€.',
  website: '',
};

const RESULT: QualifiedLead = {
  score: { value: 10, category: 'chaud', criteria: [] },
  lead: {
    in_scope: true,
    project_type: 'e_commerce',
    project_label: 'Boutique en ligne',
    need: 'Boutique de vins',
    budget: '12 000 € à 18 000 €',
    deadline: 'avant le 1er décembre',
    urgency: 'short',
    is_decision_maker: true,
    clarity: 'precise',
    red_flags: [],
    summary: 'Caviste pressé.',
    next_action: 'Rappeler cette semaine.',
  },
  delivery: { email: 'sent', sheet: 'sent', sheet_url: 'https://docs.google.com/spreadsheets/d/demo' },
  email_preview: { sender: 'Atelier Ardoise (démo) <demo@example.com>', subject: '[Lead 10/10, chaud] Boutique en ligne, Cave des Chartrons', body: 'Nouveau lead : 10/10 (Chaud)' },
  latency_ms: 3400,
};

describe('LeadStore', () => {
  let store: LeadStore;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(LeadStore);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('envoie la demande, puis garde le résultat et le lien du Sheet', () => {
    store.submit(REQUEST);
    expect(store.phase()).toBe('loading');

    const request = http.expectOne('/api/leads');
    expect(request.request.body).toEqual(REQUEST);
    request.flush(RESULT);

    expect(store.phase()).toBe('done');
    expect(store.result()?.score.value).toBe(10);
    expect(store.sheetUrl()).toBe('https://docs.google.com/spreadsheets/d/demo');
  });

  it("n'envoie pas deux fois pendant l'analyse", () => {
    store.submit(REQUEST);
    store.submit(REQUEST);
    http.expectOne('/api/leads').flush(RESULT);
  });

  it("remonte les champs à corriger renvoyés par l'API", () => {
    store.submit(REQUEST);
    http.expectOne('/api/leads').flush(
      { error: { code: 'invalid_lead', message: 'x', fields: [{ field: 'email', message: 'Email invalide.' }] } },
      { status: 400, statusText: 'Bad Request' },
    );
    expect(store.failure()).toEqual({ code: 'invalid_lead', fields: [{ field: 'email', message: 'Email invalide.' }] });
  });

  it('retrouve le code depuis le statut quand Cloudflare a remplacé le corps, puis réessaie', () => {
    const cloudflarePage = '<!DOCTYPE html><title>502: Bad gateway</title>';
    store.submit(REQUEST);
    http.expectOne('/api/leads').flush(cloudflarePage, { status: 502, statusText: 'Bad Gateway' });
    expect(store.failure()?.code).toBe('llm_unavailable');

    store.retry();
    const retry = http.expectOne('/api/leads');
    expect(retry.request.body).toEqual(REQUEST);
    retry.flush(RESULT);
    expect(store.failure()).toBeNull();
  });

  it('signale une coupure réseau', () => {
    store.submit(REQUEST);
    http.expectOne('/api/leads').error(new ProgressEvent('error'));
    expect(store.failure()?.code).toBe('network');
  });

  it('reste utilisable si /api/health ne répond pas', () => {
    store.loadHealth();
    http.expectOne('/api/health').error(new ProgressEvent('error'));
    expect(store.sheetUrl()).toBeNull();
  });
});
