import { inject, Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivate, CanActivateChild, Router, RouterStateSnapshot, UrlTree } from '@angular/router';
import { CampaignTrackingService } from './campaign-tracking.service';

@Injectable({ providedIn: 'root' })
export class CampaignParamsGuard implements CanActivate, CanActivateChild {
  private readonly router = inject(Router);
  private readonly campaignTracking = inject(CampaignTrackingService);

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): boolean | UrlTree {
    return this.preserveCampaignParams(route, state);
  }

  canActivateChild(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): boolean | UrlTree {
    return this.preserveCampaignParams(route, state);
  }

  private preserveCampaignParams(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): boolean | UrlTree {
    const campaignParams = this.campaignTracking.getCampaignParams();

    if (Object.keys(campaignParams).length === 0) {
      return true;
    }

    const queryParams = route.queryParams;
    const missingParam = Object.keys(campaignParams).some((param) => !queryParams[param]);

    if (!missingParam) {
      return true;
    }

    const urlTree = this.router.parseUrl(state.url);
    urlTree.queryParams = { ...campaignParams, ...urlTree.queryParams };
    return urlTree;
  }
}
