import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { APP_ENVIRONMENT } from '@core/config/environment.tokens';
import { AUTHORIZATION_HEADER, DYNAMIC_ALLOWED_DOMAINS, SESSION_AUTH_STORE, TOKEN_EXPIRED_HEADER } from './auth.tokens';
import { SKIP_AUTH } from '@core/http/http.context';

export const sessionAuthInterceptor: HttpInterceptorFn = (request, next) => {
  const session = inject(SESSION_AUTH_STORE);
  const dynamicDomains = inject(DYNAMIC_ALLOWED_DOMAINS);
  const environment = inject(APP_ENVIRONMENT);

  const isDomainAllowed = (url: string): boolean =>
    url.includes(environment.endpoint) ||
    Boolean(environment.enableAuthDomains?.some((domain) => url.includes(domain))) ||
    dynamicDomains.isAllowed(url);

  if (
    request.context.get(SKIP_AUTH) ||
    !session.isLoggedIn() ||
    !isDomainAllowed(request.url) ||
    request.headers.has(AUTHORIZATION_HEADER)
  ) {
    return next(request);
  }

  if (session.shouldRefreshAccessToken()) {
    return next(
      request.clone({
        headers: request.headers.set(TOKEN_EXPIRED_HEADER, 'true'),
      }),
    );
  }

  const authorization = session.getAuthorizationHeader();
  return next(
    authorization
      ? request.clone({
          headers: request.headers.set(AUTHORIZATION_HEADER, authorization),
        })
      : request,
  );
};
