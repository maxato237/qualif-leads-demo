import { Component, computed, effect, inject, input, output, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { FieldError, LeadField, LeadRequest } from '../../core/api/api.models';
import { EXAMPLES, LeadExample } from '../../core/examples';

const MESSAGE_MIN = 20;
const MESSAGE_MAX = 2000;

/** Formulaire de contact du site de l'agence, avec des exemples prêts à envoyer. */
@Component({
  selector: 'app-lead-form',
  imports: [ReactiveFormsModule],
  templateUrl: './lead-form.html',
  styleUrl: './lead-form.css',
})
export class LeadForm {
  readonly pending = input(false);
  readonly serverErrors = input<FieldError[]>([]);
  readonly submitted = output<LeadRequest>();

  protected readonly examples = EXAMPLES;
  protected readonly messageMax = MESSAGE_MAX;
  protected readonly activeExample = signal<string | null>(null);
  private readonly showErrors = signal(false);

  protected readonly form = inject(FormBuilder).nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(80)]],
    email: ['', [Validators.required, Validators.email, Validators.maxLength(120)]],
    company: ['', [Validators.maxLength(80)]],
    message: ['', [Validators.required, Validators.minLength(MESSAGE_MIN), Validators.maxLength(MESSAGE_MAX)]],
    // Champ piège : invisible et hors tabulation, seul un robot le remplit.
    website: [''],
  });

  private readonly messageValue = toSignal(this.form.controls.message.valueChanges, { initialValue: '' });
  protected readonly messageLength = computed(() => this.messageValue().length);

  constructor() {
    // Une erreur renvoyée par l'API s'affiche sous le champ concerné.
    effect(() => {
      for (const error of this.serverErrors()) {
        this.form.controls[error.field]?.setErrors({ server: error.message });
      }
      if (this.serverErrors().length) {
        this.showErrors.set(true);
      }
    });
  }

  protected useExample(example: LeadExample): void {
    this.form.setValue({ ...example.lead, website: '' });
    this.activeExample.set(example.id);
    this.showErrors.set(false);
  }

  protected errorFor(field: LeadField): string | null {
    const control = this.form.controls[field];
    if (!control.errors || !(this.showErrors() || control.touched)) {
      return null;
    }
    if (control.errors['server']) {
      return control.errors['server'];
    }
    return {
      name: 'Indiquez un nom (2 à 80 caractères).',
      email: 'Indiquez une adresse email valide.',
      company: 'Le nom de société fait 80 caractères au plus.',
      message: 'Décrivez votre projet en 20 à 2 000 caractères.',
    }[field];
  }

  protected submit(): void {
    if (this.form.invalid) {
      this.showErrors.set(true);
      this.form.markAllAsTouched();
      return;
    }
    this.submitted.emit(this.form.getRawValue());
  }
}
