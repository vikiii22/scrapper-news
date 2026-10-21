import { inject, Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivate, CanActivateChild, RouterStateSnapshot } from '@angular/router';
import { AppLogger, PlatformRoutesService, ResponsiveService } from '@core/platform/platform.contracts';
import { APP_ROUTES } from '@core/routing/routes.token';

@Injectable({ providedIn: 'root' })
export class PlatformRouteGuard implements CanActivate, CanActivateChild {
  private readonly logger = inject(AppLogger);
  private readonly platformRoutes = inject(PlatformRoutesService);
  private readonly responsive = inject(ResponsiveService);
  private readonly routes = inject(APP_ROUTES);

  canActivate(_route: ActivatedRouteSnapshot, state: RouterStateSnapshot): boolean {
    const isNotFoundPage = state.url.includes(this.routes.notFound);
    const matchesPlatform = this.responsive.isDesktop() === state.url.startsWith('/m/');
    const isAllowed = matchesPlatform || isNotFoundPage;

    if (!isAllowed) {
      if (state.url !== '/' && !state.url.startsWith('/?')) {
        this.logger.warn(
          `Tried to route to ${state.url} when isDesktop is ${this.responsive.isDesktop()}`,
        );
      }

      this.platformRoutes.navigateAdyacentTo(state.url);
    }

    return isAllowed;
  }

  canActivateChild(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): boolean {
    return this.canActivate(route, state);
  }
}
