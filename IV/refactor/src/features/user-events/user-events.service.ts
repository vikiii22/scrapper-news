import { inject, Injectable } from '@angular/core';
import { catchError, filter, map, Observable, of, switchMap, tap } from 'rxjs';
import { AppLogger } from '@core/platform/platform.contracts';

export enum UserEventType {
  DEPOSIT = 'deposit',
}

export enum DepositMethod {
  TRANSFERENCE = 'TRANSFERENCE',
}

export interface UserEvent {
  readonly event: UserEventType | string;
  readonly extra1?: number;
}

export interface UserEventsResponse {
  readonly object: readonly UserEvent[];
}

export interface LoadEvent {
  readonly method: DepositMethod;
  readonly amount?: number;
}

export interface UserData {
  readonly shouldFetchEvents?: boolean;
  readonly accountStateCode?: string;
  readonly phone?: string;
  readonly phonePrefix?: string;
}

export abstract class UserEventsDao {
  abstract getUserEventsAndDelete(): Observable<UserEventsResponse>;
}

export abstract class UserService {
  abstract getData(): Observable<UserData | null>;
}

export abstract class MeasuringService {
  abstract sendLoadEvents(events: readonly LoadEvent[]): void;
  abstract sendTagManagerEvent(eventName: string, payload: Readonly<Record<string, unknown>>): void;
}

@Injectable({ providedIn: 'root' })
export class UserEventsService {
  private readonly measuring = inject(MeasuringService);
  private readonly userEventsDao = inject(UserEventsDao);
  private readonly logger = inject(AppLogger);
  private readonly userService = inject(UserService);

  initializeLoginAnalytics(): void {
    this.userService
      .getData()
      .pipe(
        filter((user) => !!user?.shouldFetchEvents),
        switchMap(() => this.getUserEventsAndDelete()),
      )
      .subscribe();
  }

  getUserEventsAndDelete(): Observable<void> {
    return this.userEventsDao.getUserEventsAndDelete().pipe(
      map((response) =>
        (response.object ?? [])
          .filter((event) => event.event === UserEventType.DEPOSIT)
          .map<LoadEvent>((event) => ({
            method: DepositMethod.TRANSFERENCE,
            amount: event.extra1,
          })),
      ),
      tap({
        next: (events) => this.measuring.sendLoadEvents(events),
        error: (error: unknown) =>
          this.logger.error('UserEventsService: Get user events', undefined, { error }),
      }),
      map(() => undefined),
      catchError(() => of(undefined)),
    );
  }
}
