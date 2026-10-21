import { inject, Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { AsyncKeyValueStorage } from './storage.model';
import { LOCAL_STORAGE } from './browser-storage.service';

/** Observable facade over the synchronous local storage (original `zl`). */
@Injectable({ providedIn: 'root' })
export class AsyncLocalStorageService extends AsyncKeyValueStorage {
  private readonly localStorage = inject(LOCAL_STORAGE);

  clear(): Observable<void> {
    this.localStorage.clear();
    return of(undefined);
  }

  getItem(key: string): Observable<string | null> {
    return of(this.localStorage.getItem(key));
  }

  removeItem(key: string): Observable<void> {
    this.localStorage.removeItem(key);
    return of(undefined);
  }

  setItem(key: string, value: string): Observable<void> {
    this.localStorage.setItem(key, value);
    return of(undefined);
  }
}
