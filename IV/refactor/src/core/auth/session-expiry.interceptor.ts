import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { APP_ENVIRONMENT } from '@core/config/environment.tokens';
import { RedirectUrlService } from '@core/routing/redirect-url.service';
import { AUTHORIZATION_HEADER, SESSION_AUTH_STORE } from './auth.tokens';

const ABSOLUTE_URL = /^(?:[a-z]+:)?\/\//i;

export const sessionExpiryInterceptor: HttpInterceptorFn = (request, next) => {
  const session = inject(SESSION_AUTH_STORE);
  const router = inject(Router);
  const redirectUrl = inject(RedirectUrlService);
  const environment = inject(APP_ENVIRONMENT);

  const onUnauthorized = (): void => {
    redirectUrl.setRedirectUrl(router.url);
    session.logout();
  };

  return next(request).pipe(
    catchError((error: HttpErrorResponse) => {
      const isSessionExpired =
        error instanceof HttpErrorResponse &&
        session.isLoggedIn() &&
        request.headers.has(AUTHORIZATION_HEADER) &&
        (error.status === 401 || error.status === 403);

      if (isSessionExpired) {
        if (ABSOLUTE_URL.test(request.url)) {
          const requestUrl = new URL(request.url);
          const endpointUrl = new URL(environment.endpoint);

          if (requestUrl.hostname === endpointUrl.hostname) {
            onUnauthorized();
          }
        } else if (request.url.indexOf(environment.endpoint) === 0) {
          onUnauthorized();
        }
      }

      return throwError(() => error);
    }),
  );
};
