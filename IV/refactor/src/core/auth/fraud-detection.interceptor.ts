import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { SESSION_SERVICE } from './auth.tokens';
import { AlertsService } from '@core/ui/alerts.service';

export class FraudDetectedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'FraudDetectedError';
  }
}

interface FraudErrorBody {
  readonly status?: string;
  readonly message?: string;
}

export const fraudDetectionInterceptor: HttpInterceptorFn = (request, next) => {
  const session = inject(SESSION_SERVICE);
  const alerts = inject(AlertsService);

  return next(request).pipe(
    catchError((error: HttpErrorResponse) => {
      const body = error.error as FraudErrorBody | null;

      if (body?.status === 'FRAUD_DETECTED') {
        session.logoutNoUnregister();
        alerts.notifyError(body.message ?? '');
        return throwError(() => new FraudDetectedError(body.message ?? ''));
      }

      return throwError(() => error);
    }),
  );
};
