import { inject, Injectable } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { Meta, Title } from '@angular/platform-browser';
import { Observable } from 'rxjs';
import { AppLogger } from '@core/platform/platform.contracts';

export interface TranslatedTitle {
  readonly translationKey?: string;
  readonly translationData?: Readonly<Record<string, unknown>>;
}

export type RouteTitle = string | TranslatedTitle;

export type RouteMeta = Readonly<Record<string, string>>;

export interface RouteMetaData {
  meta?: RouteMeta & { title?: RouteTitle };
}

export abstract class TranslationsService {
  abstract getTranslation(key: string): Observable<string>;
  abstract getCompiledTranslation(key: string, data?: Readonly<Record<string, unknown>>): Observable<string>;
}

@Injectable({ providedIn: 'root' })
export class MetaRouterService {
  private readonly route = inject(ActivatedRoute);
  private readonly logger = inject(AppLogger);
  private readonly title = inject(Title);
  private readonly translations = inject(TranslationsService);
  private readonly meta = inject(Meta);

  private addedMetas = new Set<string>();

  constructor() {
    this.route.data.pipe(takeUntilDestroyed()).subscribe((data) => {
      const meta = (data as RouteMetaData).meta;

      if (!meta || typeof meta !== 'object') {
        return;
      }

      if (Object.prototype.hasOwnProperty.call(meta, 'title')) {
        this.applyTitle(meta.title);
        delete meta.title;
      }

      this.setMetas(meta as RouteMeta);
    });
  }

  private applyTitle(title: RouteTitle | undefined): void {
    switch (typeof title) {
      case 'string':
        this.title.setTitle(title);
        return;

      case 'object': {
        if (!title.translationKey) {
          this.setDefaultTitle();
          this.logger.warn(`MetaRouterService: title is 'object' but has no translation key: ${title}`);
          return;
        }

        const translation$ = title.translationData
          ? this.translations.getCompiledTranslation(title.translationKey, title.translationData)
          : this.translations.getTranslation(title.translationKey);

        translation$.subscribe((translation) => this.title.setTitle(translation));
        return;
      }

      default:
        this.logger.warn(`MetaRouterService: title is not 'object' or 'string': ${JSON.stringify(title)}`);
        this.setDefaultTitle();
    }
  }

  private setDefaultTitle(): void {
    this.translations.getTranslation('global.appName').subscribe((translation) => this.title.setTitle(translation));
  }

  private setMetas(meta: RouteMeta): void {
    const nextMetas = new Set(Object.keys(meta));

    Array.from(this.addedMetas)
      .filter((name) => !nextMetas.has(name))
      .forEach((name) => this.meta.removeTag(`name="${name}"`));

    this.addedMetas = nextMetas;
    this.addedMetas.forEach((name) => this.meta.updateTag({ name, content: meta[name] }));
  }
}
