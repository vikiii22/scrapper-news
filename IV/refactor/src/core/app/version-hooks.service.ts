import { HttpClient } from '@angular/common/http';
import { inject, Injectable, Injector } from '@angular/core';
import { catchError, EMPTY, forkJoin, map, Observable, of } from 'rxjs';
import { APP_ENVIRONMENT } from '@core/config/environment.tokens';
import { LocaleService } from '@core/i18n/locale.service';
import { AppLogger } from '@core/platform/platform.contracts';
import { LOCAL_STORAGE } from '@core/storage/browser-storage.service';
import { StorageMigrationService } from '@core/storage/storage-migration.service';

export abstract class DeviceLocaleService {
  abstract sendNativeLocaleIfNeeded(locale: string): Observable<void>;
}

@Injectable({ providedIn: 'root' })
export class VersionMismatchService {
  private readonly environment = inject(APP_ENVIRONMENT);
  private readonly localStorage = inject(LOCAL_STORAGE);
  private readonly localeService = inject(LocaleService);
  private readonly deviceLocaleService = inject(DeviceLocaleService);

  runHooks(previousVersion: number): Observable<void> {
    const keys = this.environment.localStorageKeys;

    if (previousVersion >= 1092 && previousVersion <= 1097) {
      this.localStorage.removeItem(keys['kycLaunched']);
      this.localStorage.removeItem(keys['counterShares']);
      this.localStorage.removeItem(keys['boothsLastDate']);
    }

    if (previousVersion > 1155 && previousVersion <= 1156) {
      this.clearUnusedKeys();
    }

    if (previousVersion >= 1188 && previousVersion < 1189) {
      this.removeKey(keys['ticketsGameFilters']);
    }

    if (previousVersion <= 1321) {
      [
        keys['reviews'],
        keys['reviewsLastDate'],
        keys['ratings'],
        keys['ratingsLastDate'],
        keys['winners'],
        keys['winnersLastDate'],
      ].forEach((key) => this.removeKey(key));
    }

    if (previousVersion <= 1387) {
      this.removeKey('0x14');
    }

    return this.deviceLocaleService
      .sendNativeLocaleIfNeeded(this.localeService.getLocale())
      .pipe(
        map(() => undefined),
        catchError(() => of(undefined)),
      );
  }

  private clearUnusedKeys(): void {
    const knownKeys = Object.keys(this.environment.localStorageKeys);
    const unusedKeys: string[] = [];

    for (let index = 0; index < this.localStorage.length; index++) {
      const key = this.localStorage.key(index);

      if (key && !knownKeys.includes(key)) {
        unusedKeys.push(key);
      }
    }

    unusedKeys.forEach((key) => this.localStorage.removeItem(key));
  }

  private removeKey(key: string | undefined): void {
    if (key) {
      this.localStorage.removeItem(key);
    }
  }
}

@Injectable({ providedIn: 'root' })
export class StorageMigrationHooksService {
  private readonly localStorage = inject(LOCAL_STORAGE);
  private readonly injector = inject(Injector);
  private readonly environment = inject(APP_ENVIRONMENT);

  runHooks(previousVersion: number): Observable<void> {
    const keys = this.environment.localStorageKeys;

    if (previousVersion >= 1092 && previousVersion <= 1097) {
      this.localStorage.removeItem(keys['kycLaunched']);
      this.localStorage.removeItem(keys['counterShares']);
      this.localStorage.removeItem(keys['boothsLastDate']);
    }

    if (previousVersion > 1287) {
      this.localStorage.removeItem('tl_failed_login');
    }

    const migrationService = this.injector.get(StorageMigrationService, null);

    if (!migrationService) {
      return EMPTY;
    }

    const allInfoKey = keys['allInfo'];
    const migrations = this.environment.enableLocalStorageMigration
      ? migrationService.migrateToIndexedDB([allInfoKey])
      : migrationService.migrateToLocalStorage([allInfoKey]);

    return forkJoin(migrations).pipe(map(() => undefined));
  }
}

export interface VersionRange {
  readonly min: number;
  readonly max: number;
}

export class VersionRangeModel implements VersionRange {
  constructor(
    readonly min: number,
    readonly max: number,
  ) {}

  static createFromBackend(range: VersionRange): VersionRangeModel {
    return new VersionRangeModel(range.min, range.max);
  }
}

interface VersionFileResponse {
  readonly noDeleteAllInfoInVersion: VersionRange;
}

export abstract class CacheBustService {
  abstract getCacheBust(): string;
}

@Injectable({ providedIn: 'root' })
export class DeleteAllInfoInVersionService {
  private readonly http = inject(HttpClient);
  private readonly logger = inject(AppLogger);
  private readonly environment = inject(APP_ENVIRONMENT);
  private readonly localStorage = inject(LOCAL_STORAGE);
  private readonly cacheBust = inject(CacheBustService);

  deleteAllInfo(): Observable<boolean> {
    const cacheBust = this.cacheBust.getCacheBust();

    return this.http
      .get<VersionFileResponse>(
        `${this.environment.noDeleteAllInfoInVersionURL}?ngsw-bypass=1&cache-bust=${cacheBust}`,
      )
      .pipe(
        map((response) => VersionRangeModel.createFromBackend(response.noDeleteAllInfoInVersion)),
        map((range) => this.mustDeleteAllInfo(range)),
        catchError((error: unknown) => {
          this.logger.warn('No se ha podido obtener el fichero versions-web.json', { error });
          return of(true);
        }),
      );
  }

  private mustDeleteAllInfo(range: VersionRangeModel | null): boolean {
    if (!range) {
      return true;
    }

    if (range.max < range.min) {
      this.logger.error(
        'File versions-web.json has an incorrect min-max range, as the min value is greater than the max value or vice versa.',
      );
    }

    const storedVersion = Number(this.localStorage.getItem(this.environment.localStorageKeys['appVersion']));
    const currentVersion = Number(this.environment.appVersion);

    return !(range.max >= range.min && storedVersion >= range.min && currentVersion <= range.max);
  }
}

export abstract class TrackeablePromoService {
  abstract savePromocode(promoCode: string | null): void;
}
