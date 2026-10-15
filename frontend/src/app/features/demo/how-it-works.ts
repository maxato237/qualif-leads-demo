import { Component, input } from '@angular/core';

interface GridRow {
  label: string;
  points: string;
  rule: string;
}

const GRID: GridRow[] = [
  { label: 'Base', points: '1', rule: 'Toute demande pertinente part de 1 point.' },
  { label: 'Budget', points: '0 à 4', rule: "Non précisé 1, moins de 1 500 € 0, jusqu'à 5 000 € 2, jusqu'à 15 000 € 3, au-delà 4." },
  { label: 'Délai', points: '0 à 2', rule: 'Sous 3 mois 2, sans échéance ferme 1, non précisé 0.' },
  { label: 'Clarté du besoin', points: '0 à 2', rule: 'Précis 2, en partie défini 1, flou 0.' },
  { label: 'Interlocuteur', points: '0 à 1', rule: 'La personne qui écrit décide : 1.' },
];

/** Section pour le dirigeant d'agence : le principe, la grille de score et les garde-fous. */
@Component({
  selector: 'app-how-it-works',
  templateUrl: './how-it-works.html',
  styleUrl: './how-it-works.css',
})
export class HowItWorks {
  readonly contactUrl = input.required<string>();
  readonly repositoryUrl = input.required<string>();

  protected readonly grid = GRID;
}
