import { HttpInterceptorFn } from '@angular/common/http';
import { acceptLanguageInterceptor } from './accept-language.interceptor';
import { cacheBusterInterceptor } from './cache-buster.interceptor';
import { defaultHeadersInterceptor } from './default-headers.interceptor';

/** Original `HTTP_HEADERS_INTERCEPTORS` module order. */
export const HTTP_HEADER_INTERCEPTORS: readonly HttpInterceptorFn[] = [
  defaultHeadersInterceptor,
  cacheBusterInterceptor,
  acceptLanguageInterceptor,
];
