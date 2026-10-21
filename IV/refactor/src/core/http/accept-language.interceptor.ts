import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { API_ENDPOINT, BROWSER_LANGUAGE } from '@core/config/environment.tokens';
import { LocaleService } from '@core/i18n/locale.service';
import { ACCEPT_ANY_LANGUAGE, USE_BROWSER_LANGUAGE } from './http.context';

export const acceptLanguageInterceptor: HttpInterceptorFn = (request, next) => {
  const endpoint = inject(API_ENDPOINT);
  const localeService = inject(LocaleService);

  if (!request.url.includes(endpoint)) {
    return next(request);
  }

  if (request.context.get(USE_BROWSER_LANGUAGE)) {
    return next(
      request.clone({
        headers: request.headers.set('Accept-Language', inject(BROWSER_LANGUAGE)),
      }),
    );
  }

  const locale = request.context.get(ACCEPT_ANY_LANGUAGE) ? '*' : localeService.getLocale();

  return next(
    request.clone({
      headers: request.headers.set('Accept-Language', locale),
    }),
  );
};
