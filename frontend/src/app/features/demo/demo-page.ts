import { Component, ElementRef, OnInit, computed, effect, inject, viewChild } from '@angular/core';

import { ApiErrorCode, LeadRequest } from '../../core/api/api.models';
import { LeadStore } from '../../core/lead-store';
import { environment } from '../../../environments/environment';
import { HowItWorks } from './how-it-works';
import { LeadForm } from './lead-form';
import { LeadResult } from './lead-result';

interface ErrorCopy {
  message: string;
  canRetry: boolean;
}

const ERRORS: Record<ApiErrorCode, ErrorCopy> = {
  llm_unavailable: { message: "L'analyse est momentanément indisponible. La demande n'a pas été perdue.", canRetry: true },
  network: { message: "Impossible de joindre le serveur. Vérifiez votre connexion, la demande n'a pas été perdue.", canRetry: true },
  internal_error: { message: "Une erreur est survenue de notre côté. La demande n'a pas été perdue.", canRetry: true },
  rate_limited: { message: 'Vous avez envoyé beaucoup de demandes. Réessayez dans quelques minutes (limite : 10 par heure).', canRetry: false },
  demo_paused: { message: "La démo a atteint son nombre de demandes pour aujourd'hui. Elle revient demain matin.", canRetry: false },
  invalid_lead: { message: 'Certains champs du formulaire sont à corriger.', canRetry: false },
  spam_detected: { message: 'La demande a été refusée.', canRetry: false },
};

const STEPS = ['Lecture du message', "Extraction par l'IA", 'Calcul du score', 'Email et Google Sheet'];

@Component({
  selector: 'app-demo-page',
  imports: [LeadForm, LeadResult, HowItWorks],
  templateUrl: './demo-page.html',
  styleUrl: './demo-page.css',
})
export class DemoPage implements OnInit {
  protected readonly store = inject(LeadStore);
  protected readonly contactUrl = environment.contactUrl;
  protected readonly repositoryUrl = environment.repositoryUrl;
  protected readonly steps = STEPS;

  protected readonly error = computed(() => {
    const failure = this.store.failure();
    return failure && failure.code !== 'invalid_lead' ? ERRORS[failure.code] : null;
  });
  protected readonly fieldErrors = computed(() => this.store.failure()?.fields ?? []);

  private readonly inbox = viewChild.required<ElementRef<HTMLElement>>('inbox');

  constructor() {
    // Sur téléphone, le panneau de l'agence est sous le formulaire : on l'amène à l'écran.
    effect(() => {
      const phase = this.store.phase();
      if (phase === 'loading' || phase === 'done') {
        const inbox = this.inbox().nativeElement;
        if (inbox.getBoundingClientRect().top > window.innerHeight * 0.6) {
          inbox.scrollIntoView({ block: 'start' });
        }
      }
    });
  }

  ngOnInit(): void {
    this.store.loadHealth();
  }

  protected send(request: LeadRequest): void {
    this.store.submit(request);
  }
}
