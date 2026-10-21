import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { API_ENDPOINT, DEFAULT_HEADERS } from '@core/config/environment.tokens';

export const defaultHeadersInterceptor: HttpInterceptorFn = (request, next) => {
  const endpoint = inject(API_ENDPOINT);
  const defaultHeaders = inject(DEFAULT_HEADERS);

  if (!request.url.includes(endpoint)) {
    return next(request);
  }

  let headers = request.headers;
  for (const [name, value] of Object.entries(defaultHeaders)) {
    if (!request.headers.has(name)) {
      headers = headers.set(name, value);
    }
  }

  return next(request.clone({ headers }));
};
