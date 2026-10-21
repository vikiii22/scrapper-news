import { Observable } from 'rxjs';

export interface KeyValueStorage {
  readonly length: number;
  clear(): void;
  getItem(key: string): string | null;
  key(index: number): string | null;
  removeItem(key: string): void;
  setItem(key: string, value: string): boolean;
}

export abstract class AsyncKeyValueStorage {
  abstract getItem(key: string): Observable<string | null>;
  abstract setItem(key: string, value: string): Observable<void>;
  abstract removeItem(key: string): Observable<void>;
  abstract clear(): Observable<void>;
}
