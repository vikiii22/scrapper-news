import { inject, Injectable, NgZone } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { catchError, defer, distinctUntilChanged, filter, iif, map, Observable, of, switchMap, tap, throwError } from 'rxjs';
import { APP_ENVIRONMENT } from '@core/config/environment.tokens';
import { AppLogger, PlatformRoutesService, ResponsiveService } from '@core/platform/platform.contracts';
import { WINDOW } from '@core/platform/window.token';
import { CampaignTrackingService } from '@core/routing/campaign-tracking.service';
import { LOCAL_STORAGE } from '@core/storage/browser-storage.service';
import { AsyncKeyValueStorage } from '@core/storage/storage.model';
import { LandingPlayService } from '@features/play/landing-play.service';
import { MeasuringService } from '@features/user-events/user-events.service';
import {
  DeleteAllInfoInVersionService,
  TrackeablePromoService,
  VersionMismatchService,
} from './version-hooks.service';

@Injectable({ providedIn: 'root' })
export class AppInitializerService {
  private readonly tuLoteroLocalStorage = inject(AsyncKeyValueStorage);
  private readonly localStorage = inject(LOCAL_STORAGE);
  private readonly logger = inject(AppLogger);
  private readonly measuring = inject(MeasuringService);
  private readonly router = inject(Router);
  private readonly trackeablePromo = inject(TrackeablePromoService);
  private readonly versionMismatch = inject(VersionMismatchService);
  private readonly deleteAllInfoInVersion = inject(DeleteAllInfoInVersionService);
  private readonly zone = inject(NgZone);
  private readonly platformRoutes = inject(PlatformRoutesService);
  private readonly responsive = inject(ResponsiveService);
  private readonly landingPlay = inject(LandingPlayService);
  private readonly campaignTracking = inject(CampaignTrackingService);
  private readonly environment = inject(APP_ENVIRONMENT);
  private readonly window = inject(WINDOW);

  initialize(): void {
    if (!this.platformRoutes.assertRoutePlatform()) {
      this.platformRoutes.navigateAdyacentRoute('merge');
    }

    this.responsive.breakpointChange
      .pipe(map(() => this.responsive.getPlatform()), distinctUntilChanged())
      .subscribe(() => {
        if (!this.platformRoutes.assertRoutePlatform()) {
          this.platformRoutes.navigateAdyacentRoute();
        }
      });

    this.landingPlay.checkAndHandlePlayCookie();
  }

  checkDataIntegrity(): Observable<void> {
    const storedVersion = this.localStorage.getItem(this.environment.localStorageKeys['appVersion']);
    const appVersion = this.environment.appVersion;

    return of(undefined).pipe(
      switchMap(() =>
        iif(
          () => !storedVersion || storedVersion !== appVersion,
          this.deleteAllInfoInVersion.deleteAllInfo().pipe(
            switchMap((mustDelete) => iif(() => mustDelete, this.removeAllInfo(), of(undefined))),
          ),
          of(undefined),
        ),
      ),
      switchMap(() =>
        iif(
          () => !!storedVersion && storedVersion !== appVersion,
          defer(() =>
            this.versionMismatch.runHooks(Number(storedVersion)).pipe(
              catchError((error: unknown) => {
                this.logger.error(error as string);
                return of(undefined);
              }),
            ),
          ),
          of(undefined),
        ),
      ),
      tap(() => this.localStorage.setItem(this.environment.localStorageKeys['appVersion'], appVersion)),
    );
  }

  initializeAnalytics(): void {
    if (!this.environment.production) {
      return;
    }

    this.zone.runOutsideAngular(() => {
      this.router.events
        .pipe(filter((event) => event instanceof NavigationEnd))
        .subscribe((event) =>
          this.measuring.sendTagManagerEvent('page_view', {
            viewUrl: (event as NavigationEnd).urlAfterRedirects,
            appVersion: this.environment.appVersion,
          }),
        );
    });
  }

  trackPromoCode(): void {
    const params = new URLSearchParams(this.window.location.search);
    const promoParam = this.environment.locale.routes.promoParam;

    if (params.has(promoParam)) {
      this.trackeablePromo.savePromocode(params.get(promoParam));
    }
  }

  initializeCampaignTracking(): void {
    this.campaignTracking.initialize();
  }

  private removeAllInfo(): Observable<void> {
    return this.tuLoteroLocalStorage.removeItem(this.environment.localStorageKeys['allInfo']).pipe(
      switchMap(() => this.tuLoteroLocalStorage.removeItem(this.environment.localStorageKeys['endpoint'])),
      catchError((error: unknown) => {
        this.logger.error('Error when try delete allInfo', error);
        return throwError(() => error);
      }),
    );
  }
}
