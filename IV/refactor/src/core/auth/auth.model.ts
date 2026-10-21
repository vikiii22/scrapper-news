import { Observable } from 'rxjs';

export enum AuthStrategyType {
  JWT = 'JWT',
}

export interface AuthTokens {
  readonly accessToken: string;
  readonly refreshToken: string;
  readonly refreshTokenExpirationDate: number;
}

export interface AuthorizationProvider {
  getAuthorizationHeader(): string | null;
}

export interface JwtAuthStrategy extends AuthorizationProvider {
  readonly type: AuthStrategyType.JWT;
  isAccessTokenExpired(): boolean;
  isRefreshTokenExpired(): boolean;
  markRefreshAttempt(): void;
  updateTokens(accessToken: string, refreshToken: string, refreshTokenExpirationDate: number): void;
}

export interface AuthStrategyManager {
  getActiveStrategy(): JwtAuthStrategy | null;
  refreshAccessToken$(): Observable<AuthTokens>;
  clear(): void;
}

/**
 * Synchronous view of the session used by the HTTP layer (original `Nr`).
 */
export abstract class SessionAuthStore implements AuthorizationProvider {
  abstract isLoggedIn(): boolean;
  abstract shouldRefreshAccessToken(): boolean;
  abstract getAuthorizationHeader(): string | null;
  abstract logout(): void;
}

/**
 * Reactive session facade used by feature services (original `he`).
 */
export abstract class SessionService {
  abstract isLoggedIn(): Observable<boolean>;
  abstract logout(): void;
  abstract logoutNoUnregister(): void;
}

export abstract class DynamicAllowedDomains {
  abstract isAllowed(url: string): boolean;
}
