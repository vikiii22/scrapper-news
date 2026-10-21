import { inject, Injectable } from '@angular/core';
import { NavigationEnd, NavigationStart, Router } from '@angular/router';
import { BehaviorSubject, filter, Observable, take } from 'rxjs';

export type CampaignParams = Record<string, string>;

@Injectable({ providedIn: 'root' })
export class CampaignTrackingService {
  private readonly router = inject(Router);

  private readonly allowedParams = ['cid', 'pid', 'referrer', 'c', 'utm_source', 'utm_campaign'] as const;
  private readonly campaignParamsSubject = new BehaviorSubject<CampaignParams>({});

  readonly campaignParams$: Observable<CampaignParams> = this.campaignParamsSubject.asObservable();

  initialize(): void {
    this.captureInitialCampaignParams();
    this.setupNavigationListener();
  }

  setCampaignParams(params: CampaignParams): void {
    this.campaignParamsSubject.next(params);
  }

  getCampaignParams(): CampaignParams {
    return this.campaignParamsSubject.value;
  }

  clearCampaignParams(): void {
    this.campaignParamsSubject.next({});
  }

  private captureInitialCampaignParams(): void {
    this.router.events.pipe(filter((event) => event instanceof NavigationStart), take(1)).subscribe(() => {
      const navigation = this.router.getCurrentNavigation();
      const queryParams = navigation?.extractedUrl?.queryParams;

      if (!queryParams) {
        return;
      }

      const params: CampaignParams = {};
      for (const param of this.allowedParams) {
        const value = queryParams[param];
        if (typeof value === 'string') {
          params[param] = value;
        }
      }

      if (Object.keys(params).length > 0) {
        this.setCampaignParams(params);
      }
    });
  }

  private setupNavigationListener(): void {
    this.router.events.pipe(filter((event) => event instanceof NavigationEnd)).subscribe((event) => {
      const params = this.getCampaignParams();

      if (Object.keys(params).length === 0) {
        return;
      }

      const urlTree = this.router.parseUrl((event as NavigationEnd).urlAfterRedirects);
      const missingParam = Object.keys(params).some((param) => !urlTree.queryParams[param]);

      if (missingParam) {
        void this.router.navigate([], {
          queryParams: params,
          queryParamsHandling: 'merge',
          replaceUrl: true,
        });
      }
    });
  }
}
