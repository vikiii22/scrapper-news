import { HttpInterceptorFn } from '@angular/common/http';
import { inject, InjectionToken } from '@angular/core';

/** Origin -> proxy prefix map extracted from the original bundle (`qn`). */
export const LEGACY_URL_REWRITES = new InjectionToken<Readonly<Record<string, string>>>('LEGACY_URL_REWRITES');

export const legacyProxyInterceptor: HttpInterceptorFn = (request, next) => {
  const rewrites = inject(LEGACY_URL_REWRITES);

  const url = Object.entries(rewrites).reduce(
    (currentUrl, [origin, proxyPrefix]) => currentUrl.replace(origin, proxyPrefix),
    request.url,
  );

  return next(url === request.url ? request : request.clone({ url }));
};
