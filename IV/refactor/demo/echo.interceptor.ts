import { HttpErrorResponse, HttpInterceptorFn, HttpResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { of, throwError } from 'rxjs';
import { DemoState } from './demo.state';

export const echoBackendInterceptor: HttpInterceptorFn = (request) => {
  const state = inject(DemoState);

  if (state.mode() === 'unauthorized') {
    return throwError(
      () =>
        new HttpErrorResponse({
          status: 401,
          statusText: 'Unauthorized',
          url: request.url,
        }),
    );
  }

  const headers: Record<string, string> = {};
  request.headers.keys().forEach((key) => {
    headers[key] = request.headers.get(key) ?? '';
  });

  return of(
    new HttpResponse({
      status: 200,
      url: request.url,
      body: {
        method: request.method,
        url: request.url,
        headers,
      },
    }),
  );
};
