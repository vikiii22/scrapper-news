import { InjectionToken } from '@angular/core';
import { AuthStrategyManager, DynamicAllowedDomains, SessionAuthStore, SessionService } from './auth.model';

export const AUTH_STRATEGY_MANAGER = new InjectionToken<AuthStrategyManager>('AUTH_STRATEGY_MANAGER');
export const SESSION_AUTH_STORE = new InjectionToken<SessionAuthStore>('SESSION_AUTH_STORE');
export const SESSION_SERVICE = new InjectionToken<SessionService>('SESSION_SERVICE');
export const DYNAMIC_ALLOWED_DOMAINS = new InjectionToken<DynamicAllowedDomains>('DYNAMIC_ALLOWED_DOMAINS');

export const TOKEN_EXPIRED_HEADER = 'X-Token-Expired';
export const AUTHORIZATION_HEADER = 'Authorization';
