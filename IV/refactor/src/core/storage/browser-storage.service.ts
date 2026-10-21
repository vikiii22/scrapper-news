import { InjectionToken } from '@angular/core';
import { KeyValueStorage } from './storage.model';

export const LOCAL_STORAGE = new InjectionToken<KeyValueStorage>('LOCAL_STORAGE');
export const SESSION_STORAGE = new InjectionToken<KeyValueStorage>('SESSION_STORAGE');

type StorageKind = 'localStorage' | 'sessionStorage';

export function isStorageAvailable(kind: StorageKind): boolean {
  try {
    const storage = window[kind];
    const probeKey = '__storage_probe__';

    storage.setItem(probeKey, probeKey);
    storage.removeItem(probeKey);
    return true;
  } catch {
    return false;
  }
}

export class BrowserStorageService implements KeyValueStorage {
  constructor(private readonly storage: Storage) {}

  static isAvailable(kind: StorageKind): boolean {
    return isStorageAvailable(kind);
  }

  get length(): number {
    return this.storage.length;
  }

  clear(): void {
    this.storage.clear();
  }

  getItem(key: string): string | null {
    return this.storage.getItem(key);
  }

  key(index: number): string | null {
    return this.storage.key(index);
  }

  removeItem(key: string): void {
    this.storage.removeItem(key);
  }

  setItem(key: string, value: string): boolean {
    try {
      this.storage.setItem(key, value);
      return true;
    } catch {
      return false;
    }
  }
}

export class InMemoryStorageService implements KeyValueStorage {
  private readonly data = new Map<string, string>();

  get length(): number {
    return this.data.size;
  }

  clear(): void {
    this.data.clear();
  }

  getItem(key: string): string | null {
    return this.data.get(key) || null;
  }

  key(index: number): string | null {
    return Array.from(this.data.keys())[this.length - 1 - index] || null;
  }

  removeItem(key: string): void {
    this.data.delete(key);
  }

  setItem(key: string, value: string): boolean {
    try {
      this.data.set(key, value);
      return true;
    } catch {
      return false;
    }
  }
}

export const localStorageFactory = (): KeyValueStorage =>
  BrowserStorageService.isAvailable('localStorage')
    ? new BrowserStorageService(window.localStorage)
    : new InMemoryStorageService();

export const sessionStorageFactory = (): KeyValueStorage =>
  BrowserStorageService.isAvailable('sessionStorage')
    ? new BrowserStorageService(window.sessionStorage)
    : new InMemoryStorageService();
