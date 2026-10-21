import { HttpErrorResponse } from '@angular/common/http';
import { ErrorHandler, inject, Injectable, InjectionToken } from '@angular/core';
import { APP_ENVIRONMENT } from '@core/config/environment.tokens';
import { AppLogger } from '@core/platform/platform.contracts';
import { WINDOW } from '@core/platform/window.token';

export interface ErrorLoggerConfig {
  readonly ignoredEndpointsPatterns400: readonly RegExp[];
}

export const ERROR_LOGGER_CONFIG = new InjectionToken<ErrorLoggerConfig>('ERROR_LOGGER_CONFIG');

interface NormalizedError {
  readonly message: string;
  readonly stacktrace?: string;
  readonly context?: { readonly error?: HttpErrorResponse };
  readonly original: unknown;
}

@Injectable({ providedIn: 'root' })
export class ServerErrorHandler implements ErrorHandler {
  private readonly logger = inject(AppLogger);
  private readonly environment = inject(APP_ENVIRONMENT);
  private readonly config = inject(ERROR_LOGGER_CONFIG);
  private readonly window = inject(WINDOW);

  handleError(error: unknown): void {
    if (!this.environment.production) {
      throw error;
    }

    const normalized = this.normalize(error);

    if (this.isIgnorable(error)) {
      this.logger.warn(normalized.message, normalized.context);
      return;
    }

    if (this.shouldIgnoreError(normalized)) {
      return;
    }

    const status = normalized.context?.error?.status;

    if (status === 401 || status === 504) {
      this.logger.debug(normalized.message, normalized.context);
    } else {
      this.logger.error(normalized.message, normalized.stacktrace, normalized.context);
    }

    if (normalized.message.includes('Error: Loading chunk')) {
      this.window.location.reload();
    }
  }

  private shouldIgnoreError(error: NormalizedError): boolean {
    const httpError = error.context?.error;

    if (httpError?.status !== 400 || !httpError.url) {
      return false;
    }

    return this.config.ignoredEndpointsPatterns400.some((pattern) => pattern.test(httpError.url as string));
  }

  private isIgnorable(error: unknown): boolean {
    return error instanceof HttpErrorResponse && error.status === 0;
  }

  private normalize(error: unknown): NormalizedError {
    if (error instanceof HttpErrorResponse) {
      return {
        message: `HttpErrorResponse: ${error.status} ${error.statusText}`,
        stacktrace: undefined,
        context: { error },
        original: error,
      };
    }

    if (error instanceof Error) {
      return {
        message: error.message,
        stacktrace: error.stack,
        original: error,
      };
    }

    return {
      message: String(error),
      original: error,
    };
  }
}
