import { inject, Injectable } from '@angular/core';
import { EMPTY, finalize, iif, Observable, switchMap, take } from 'rxjs';
import { AsyncKeyValueStorage } from './storage.model';
import { LOCAL_STORAGE } from './browser-storage.service';

@Injectable({ providedIn: 'root' })
export class StorageMigrationService {
  private readonly asyncLocalStorage = inject(AsyncKeyValueStorage);
  private readonly localStorage = inject(LOCAL_STORAGE);

  migrateToLocalStorage(keys: readonly string[]): Observable<void>[] {
    return keys.map((key) => this.migrateKeyToLocalStorage(key));
  }

  migrateKeyToLocalStorage(key: string): Observable<void> {
    return this.asyncLocalStorage.getItem(key).pipe(
      switchMap((value) => {
        if (!value) {
          return EMPTY;
        }

        this.localStorage.setItem(key, value);
        return this.asyncLocalStorage.removeItem(key).pipe(take(1));
      }),
    );
  }

  migrateToIndexedDB(keys: readonly string[]): Observable<void>[] {
    return keys.map((key) => this.migrateKeyToIndexedDB(key));
  }

  migrateKeyToIndexedDB(key: string): Observable<void> {
    const value = this.localStorage.getItem(key);

    return iif(
      () => !!value,
      this.asyncLocalStorage.setItem(key, value as string).pipe(
        take(1),
        finalize(() => this.localStorage.removeItem(key)),
      ),
      EMPTY,
    );
  }
}
