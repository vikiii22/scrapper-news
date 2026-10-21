import { inject, Injectable } from '@angular/core';
import { NavigationExtras, Router } from '@angular/router';
import { Observable, Subject } from 'rxjs';
import { AppLogger } from '@core/platform/platform.contracts';

export interface RouteCommand {
  readonly command: readonly unknown[];
  readonly extras?: NavigationExtras;
}

export interface PageTrace {
  readonly url: string | RouteCommand;
  readonly titleKey: string;
  readonly data?: unknown;
}

export interface PageTraceDump {
  readonly url: string;
  readonly titleKey: string;
  readonly hasData: boolean;
}

export abstract class PreviousRouteService {
  abstract getCurrentHistory(): readonly string[];
}

export abstract class RouterHistoryService {
  abstract dump(): unknown;
}

@Injectable()
export class PageControllerService {
  private readonly router = inject(Router);
  private readonly logger = inject(AppLogger);
  private readonly previousRoute = inject(PreviousRouteService);
  private readonly routerHistory = inject(RouterHistoryService);

  private readonly traceLog: PageTrace[] = [];
  private resolver: Subject<unknown> | null = null;
  private titleKey = '';
  private data: unknown;

  open(target: string | RouteCommand, titleKey: string, data?: unknown): Observable<unknown> {
    this.titleKey = titleKey;
    this.data = data;

    if (typeof target === 'string') {
      void this.router.navigate([target]);
    } else {
      void this.router.navigate([...target.command], target.extras);
    }

    this.resolver = new Subject<unknown>();
    this.traceLog.push({ url: target, titleKey, data });

    return this.resolver.asObservable();
  }

  resolve(value: unknown): void {
    const lastTrace = this.traceLog.pop();

    if (!this.resolver) {
      this.logMissingResolver('resolve', lastTrace);
      return;
    }

    this.resolver.next(value);
    this.resolver.complete();
  }

  reject(error: unknown): void {
    const lastTrace = this.traceLog.pop();

    if (!this.resolver) {
      this.logMissingResolver('reject', lastTrace);
      return;
    }

    this.resolver.error(error);
  }

  dump(): readonly PageTraceDump[] {
    return this.traceLog.map((trace) => ({
      url: this.serializeUrl(trace.url),
      titleKey: trace.titleKey,
      hasData: !!trace.data,
    }));
  }

  private serializeUrl(target: string | RouteCommand): string {
    return typeof target === 'string' ? target : target.command.join('/');
  }

  private logMissingResolver(operation: 'resolve' | 'reject', lastTrace?: PageTrace): void {
    this.logger.error(`PageControllerService.${operation} called without a matching open()`, undefined, {
      lastTrace,
      currentUrl: this.router.url,
      routeHistory: this.previousRoute.getCurrentHistory(),
      routerHistory: this.routerHistory.dump(),
    });
  }
}
