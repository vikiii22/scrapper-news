import { inject, Injectable } from '@angular/core';
import { filter, Observable, take } from 'rxjs';
import { APP_ENVIRONMENT } from '@core/config/environment.tokens';
import { SESSION_SERVICE } from '@core/auth/auth.tokens';
import { AppLogger } from '@core/platform/platform.contracts';
import { CookieService } from '@features/geolocation/update-state-app-listener.service';

interface PlayCookie {
  readonly raffleId?: string;
  readonly combinations?: readonly string[];
}

export abstract class RedirectLotteryNumberService {
  abstract redirectToLotteryNumber(
    raffleId: string,
    combination: string,
    openPlay: boolean,
  ): Observable<unknown>;
}

@Injectable({ providedIn: 'root' })
export class LandingPlayService {
  private readonly cookies = inject(CookieService);
  private readonly logger = inject(AppLogger);
  private readonly redirectLotteryNumber = inject(RedirectLotteryNumberService);
  private readonly environment = inject(APP_ENVIRONMENT);
  private readonly session = inject(SESSION_SERVICE);

  private readonly playCookieName = 'landing_play';

  checkAndHandlePlayCookie(): void {
    this.session
      .isLoggedIn()
      .pipe(filter((isLoggedIn) => !!isLoggedIn), take(1))
      .subscribe(() => {
        const rawCookie = this.cookies.get(this.playCookieName);

        if (!rawCookie) {
          return;
        }

        try {
          const { raffleId, combinations } = JSON.parse(rawCookie) as PlayCookie;

          if (!raffleId || !combinations?.length) {
            return;
          }

          this.redirectLotteryNumber
            .redirectToLotteryNumber(raffleId, combinations[0], true)
            .subscribe(() => this.deleteCookie());
        } catch (error) {
          this.logger.error('Error parsing play cookie', error);
          this.deleteCookie();
        }
      });
  }

  private deleteCookie(): void {
    this.cookies.delete(this.playCookieName, '/', `.${this.environment.globalDomain}`);
  }
}
