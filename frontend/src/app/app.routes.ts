import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    title: 'Atelier Ardoise, qualification de leads par IA (démo)',
    loadComponent: () => import('./features/demo/demo-page').then((m) => m.DemoPage),
  },
  { path: '**', redirectTo: '' },
];
