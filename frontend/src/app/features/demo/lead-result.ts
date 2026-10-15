import { Component, computed, input, output } from '@angular/core';

import { Category, DeliveryStatus, QualifiedLead } from '../../core/api/api.models';

const CATEGORY_LABELS: Record<Category, string> = {
  chaud: 'Lead chaud',
  tiede: 'Lead tiède',
  froid: 'Lead froid',
  hors_cible: 'Hors cible',
};

const EMAIL_LABELS: Record<DeliveryStatus, string> = {
  sent: "Email envoyé à l'équipe commerciale",
  failed: "Email non envoyé (service d'envoi indisponible)",
  disabled: 'Email désactivé sur cette installation',
};

const SHEET_LABELS: Record<DeliveryStatus, string> = {
  sent: 'Ligne ajoutée au Google Sheet des leads',
  failed: 'Ligne non ajoutée (Google Sheets indisponible)',
  disabled: 'Google Sheet désactivé sur cette installation',
};

/** Ce que reçoit l'agence : score, résumé, détail du calcul et confirmations d'envoi. */
@Component({
  selector: 'app-lead-result',
  templateUrl: './lead-result.html',
  styleUrl: './lead-result.css',
})
export class LeadResult {
  readonly result = input.required<QualifiedLead>();
  readonly another = output<void>();

  protected readonly categoryLabel = computed(() => CATEGORY_LABELS[this.result().score.category]);
  protected readonly seconds = computed(() =>
    (this.result().latency_ms / 1000).toLocaleString('fr-FR', { maximumFractionDigits: 1 }),
  );
  protected readonly emailLabel = computed(() => EMAIL_LABELS[this.result().delivery.email]);
  protected readonly sheetLabel = computed(() => SHEET_LABELS[this.result().delivery.sheet]);
}
