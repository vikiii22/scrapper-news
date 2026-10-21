import { HttpInterceptorFn } from '@angular/common/http';
import { sessionAuthInterceptor } from './session-auth.interceptor';
import { tokenRefreshInterceptor } from './token-refresh.interceptor';
import { sessionExpiryInterceptor } from './session-expiry.interceptor';

/**
 * Registration order is significant: the session interceptor marks the request
 * with `X-Token-Expired` and the refresh interceptor consumes that marker.
 */
export const AUTH_INTERCEPTORS: readonly HttpInterceptorFn[] = [
  sessionAuthInterceptor,
  tokenRefreshInterceptor,
  sessionExpiryInterceptor,
];
