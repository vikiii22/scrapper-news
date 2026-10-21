import { HttpErrorResponse, HttpEvent, HttpHandlerFn, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { catchError, EMPTY, Observable, Subject, switchMap, tap, throwError } from 'rxjs';
import { AuthStrategyManager, AuthStrategyType, JwtAuthStrategy } from './auth.model';
import { AUTH_STRATEGY_MANAGER, AUTHORIZATION_HEADER, TOKEN_EXPIRED_HEADER } from './auth.tokens';
import { SKIP_AUTH } from '@core/http/http.context';

@Injectable({ providedIn: 'root' })
export class TokenRefreshCoordinator {
  private readonly authStrategyManager = inject(AUTH_STRATEGY_MANAGER);

  private isRefreshing = false;
  private refresh$: Subject<void> | null = null;

  intercept(request: HttpRequest<unknown>, next: HttpHandlerFn): Observable<HttpEvent<unknown>> {
    if (request.context.get(SKIP_AUTH)) {
      return next(request);
    }

    if (!request.headers.has(TOKEN_EXPIRED_HEADER)) {
      return next(request);
    }

    return this.handleProactiveRefresh(request, next);
  }

  private handleProactiveRefresh(
    request: HttpRequest<unknown>,
    next: HttpHandlerFn,
  ): Observable<HttpEvent<unknown>> {
    const cleanRequest = request.clone({
      headers: request.headers.delete(TOKEN_EXPIRED_HEADER),
    });

    if (!this.isJwtStrategy()) {
      return next(cleanRequest);
    }

    const strategy = this.authStrategyManager.getActiveStrategy() as JwtAuthStrategy;

    if (strategy.isRefreshTokenExpired()) {
      if (strategy.isAccessTokenExpired()) {
        this.authStrategyManager.clear();
        return throwError(() => new HttpErrorResponse({ status: 401 }));
      }

      return next(this.withAuthorization(cleanRequest, strategy));
    }

    if (strategy.isAccessTokenExpired()) {
      return this.refreshToken$(strategy, true).pipe(
        switchMap(() => next(this.withAuthorization(cleanRequest, strategy))),
      );
    }

    this.refreshToken$(strategy, false)
      .pipe(catchError(() => EMPTY))
      .subscribe();

    return next(this.withAuthorization(cleanRequest, strategy));
  }

  private refreshToken$(strategy: JwtAuthStrategy, clearOnAuthError: boolean): Observable<void> {
    if (!this.isRefreshing) {
      this.isRefreshing = true;
      strategy.markRefreshAttempt();

      const refreshSubject = new Subject<void>();
      this.refresh$ = refreshSubject;

      this.authStrategyManager
        .refreshAccessToken$()
        .pipe(
          tap(({ accessToken, refreshToken, refreshTokenExpirationDate }) => {
            strategy.updateTokens(accessToken, refreshToken, refreshTokenExpirationDate);
          }),
          catchError((error: unknown) => {
            if (clearOnAuthError && this.isAuthError(error)) {
              this.authStrategyManager.clear();
            }
            return throwError(() => error);
          }),
        )
        .subscribe({
          next: () => {
            refreshSubject.next();
            refreshSubject.complete();
            this.isRefreshing = false;
            this.refresh$ = null;
          },
          error: (error: unknown) => {
            refreshSubject.error(error);
            this.isRefreshing = false;
            this.refresh$ = null;
          },
        });

      return refreshSubject.asObservable();
    }

    return this.refresh$?.asObservable() ?? EMPTY;
  }

  private withAuthorization(request: HttpRequest<unknown>, strategy: JwtAuthStrategy): HttpRequest<unknown> {
    const authorization = strategy.getAuthorizationHeader();

    return authorization
      ? request.clone({
          headers: request.headers.set(AUTHORIZATION_HEADER, authorization),
        })
      : request;
  }

  private isAuthError(error: unknown): boolean {
    return error instanceof HttpErrorResponse && (error.status === 401 || error.status === 403);
  }

  private isJwtStrategy(): boolean {
    return this.authStrategyManager.getActiveStrategy()?.type === AuthStrategyType.JWT;
  }
}

export const tokenRefreshInterceptor: HttpInterceptorFn = (request, next) =>
  inject(TokenRefreshCoordinator).intercept(request, next);
