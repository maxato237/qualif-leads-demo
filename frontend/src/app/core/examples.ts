import { LeadRequest } from './api/api.models';

export interface LeadExample {
  id: string;
  label: string;
  hint: string;
  lead: Omit<LeadRequest, 'website'>;
}

/** Demandes fictives pour essayer la démo en un clic. Adresses en example.com : aucune n'existe. */
export const EXAMPLES: LeadExample[] = [
  {
    id: 'ecommerce',
    label: 'Boutique en ligne',
    hint: 'Budget et date précis',
    lead: {
      name: 'Claire Martin',
      email: 'claire.martin@example.com',
      company: 'Cave des Chartrons',
      message:
        "Bonjour, je suis la gérante d'une cave à vins à Bordeaux. Nous voulons ouvrir une boutique en ligne (environ 300 références, paiement par carte, retrait en boutique ou livraison) avant le 1er décembre pour les fêtes. Budget prévu entre 12 et 18 k€. Pouvez-vous nous rappeler cette semaine ?",
    },
  },
  {
    id: 'refonte',
    label: 'Refonte de site',
    hint: 'Besoin réel, budget à définir',
    lead: {
      name: 'Julien Morel',
      email: 'j.morel@example.com',
      company: 'Cabinet Kiné Bastide',
      message:
        "Bonjour, notre site date de 2016 et n'est pas lisible sur téléphone. Je suis le gérant du cabinet et j'aimerais une refonte avec prise de rendez-vous en ligne, dans l'année si possible. Je n'ai pas encore de budget en tête, qu'est-ce que vous proposeriez ?",
    },
  },
  {
    id: 'irrealiste',
    label: 'Demande irréaliste',
    hint: 'Gros projet, petit budget',
    lead: {
      name: 'Kevin Durand',
      email: 'kevin.d@example.com',
      company: '',
      message:
        "Salut, je veux un site comme Amazon avec une appli mobile et un espace vendeurs, il me le faut pour demain. J'ai 300 euros. C'est possible ?",
    },
  },
  {
    id: 'demarchage',
    label: 'Démarchage',
    hint: "Pas un client pour l'agence",
    lead: {
      name: 'Service commercial',
      email: 'offres@example.com',
      company: 'Backlinks Pro',
      message:
        'Bonjour, nous proposons des packs de 500 backlinks premium pour booster le référencement de vos clients. Tarif agence : 49 euros le pack. Intéressé ?',
    },
  },
];
