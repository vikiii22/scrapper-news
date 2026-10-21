import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class DemoState {
  readonly mode = signal<'ok' | 'expired' | 'unauthorized'>('ok');
  readonly loggedIn = signal(true);
  readonly accessToken = signal('access-token-v1');
  readonly refreshCalls = signal(0);

  setMode(mode: 'ok' | 'expired' | 'unauthorized'): void {
    this.mode.set(mode);
  }
}
