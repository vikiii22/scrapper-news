import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { APP_ENVIRONMENT } from '@core/config/environment.tokens';
import { LocaleService } from '@core/i18n/locale.service';
import { WINDOW } from '@core/platform/window.token';
import { SKIP_MAINTENANCE_REDIRECT } from './http.context';

export const maintenanceInterceptor: HttpInterceptorFn = (request, next) => {
  const window = inject(WINDOW);
  const localeService = inject(LocaleService);
  const environment = inject(APP_ENVIRONMENT);

  const isLoggerRequest =
    request.method === 'PUT' && request.url.includes(environment.logger.endpoint);

  return next(request).pipe(
    catchError((error: HttpErrorResponse) => {
      if (
        error instanceof HttpErrorResponse &&
        error.status === 503 &&
        !isLoggerRequest &&
        !request.context.get(SKIP_MAINTENANCE_REDIRECT)
      ) {
        window.location.href = environment.maintenance.redirectUrl(localeService.getLocaleAbbr());
      }

      return throwError(() => error);
    }),
  );
};
