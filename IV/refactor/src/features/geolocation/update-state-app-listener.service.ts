import { inject, Injectable } from '@angular/core';
import { combineLatest, filter, map, Observable, of, switchMap, tap } from 'rxjs';
import { APP_ENVIRONMENT } from '@core/config/environment.tokens';
import { AppLogger } from '@core/platform/platform.contracts';
import { SESSION_SERVICE } from '@core/auth/auth.tokens';
import { UserData, UserService } from '@features/user-events/user-events.service';

export interface State {
  readonly code: string;
  readonly name?: string;
}

export abstract class StatesService {
  abstract getData(): Observable<readonly State[]>;
}

export abstract class StateAppDataService {
  abstract setData(state: State | undefined): void;
}

export abstract class StatesDao {
  abstract getStateCodeByIp(): Observable<string | null>;
}

export abstract class CookieService {
  abstract check(name: string): boolean;
  abstract get(name: string): string | null;
  abstract set(name: string, value: string, expirationDays?: number): void;
  abstract delete(name: string, path?: string, domain?: string): void;
}

@Injectable({ providedIn: 'root' })
export class UpdateStateAppListenerService {
  private readonly statesService = inject(StatesService);
  private readonly stateAppData = inject(StateAppDataService);
  private readonly session = inject(SESSION_SERVICE);
  private readonly userService = inject(UserService);
  private readonly statesDao = inject(StatesDao);
  private readonly cookies = inject(CookieService);
  private readonly logger = inject(AppLogger);
  private readonly environment = inject(APP_ENVIRONMENT);

  private readonly geolocationCookie = 'user_location_state';
  private readonly geolocationCacheDurationDays = 1;

  init(): void {
    const stateCode$ = this.session.isLoggedIn().pipe(
      switchMap((isLoggedIn) => {
        if (isLoggedIn) {
          return this.userService.getData().pipe(
            filter((user): user is UserData => !!user),
            map((user) =>
              user.accountStateCode
                ? user.accountStateCode
                : this.environment.geolocation.defaultAnonimousStateCode,
            ),
          );
        }

        if (this.cookies.check(this.geolocationCookie)) {
          return of(this.cookies.get(this.geolocationCookie));
        }

        return this.statesDao.getStateCodeByIp().pipe(
          tap((stateCode) => {
            if (stateCode) {
              this.cookies.set(this.geolocationCookie, stateCode, this.geolocationCacheDurationDays);
            }
          }),
        );
      }),
    );

    combineLatest([this.statesService.getData(), stateCode$])
      .pipe(
        map(([states, stateCode]) => states.find((state) => state.code === stateCode)),
        tap((state) => {
          if (!state) {
            this.logger.error('WEB-3100: UpdateStateAppListenerService.init: state is null');
          }
        }),
      )
      .subscribe((state) => this.stateAppData.setData(state));
  }
}
