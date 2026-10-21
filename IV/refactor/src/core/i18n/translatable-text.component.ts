import { Component, inject, Input, OnChanges } from '@angular/core';
import { TranslationsService } from '@core/routing/meta-router.service';

export interface Translatable {
  readonly key: string;
  readonly keyData?: Readonly<Record<string, unknown>>;
}

@Component({
  selector: 'tl-translatable-text',
  standalone: true,
  template: '{{ label }}',
})
export class TranslatableTextComponent implements OnChanges {
  private readonly translations = inject(TranslationsService);

  @Input() text?: Translatable | null;

  label = '';

  ngOnChanges(): void {
    if (!this.text?.key) {
      this.label = '';
      return;
    }

    this.translations
      .getCompiledTranslation(this.text.key, this.text.keyData)
      .subscribe((translation) => (this.label = translation));
  }
}
