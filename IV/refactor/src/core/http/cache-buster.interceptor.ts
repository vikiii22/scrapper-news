import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { API_ENDPOINT } from '@core/config/environment.tokens';

export const cacheBusterInterceptor: HttpInterceptorFn = (request, next) => {
  const endpoint = inject(API_ENDPOINT);

  if (!request.url.includes(endpoint)) {
    return next(request);
  }

  return next(
    request.clone({
      headers: request.headers.append('ngTime', Date.now().toString()),
    }),
  );
};
