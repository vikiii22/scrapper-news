import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject, InjectionToken, Type } from '@angular/core';
import { catchError, retryWhen, switchMap, throwError } from 'rxjs';
import { APP_ENVIRONMENT } from '@core/config/environment.tokens';
import { ResponsiveService } from '@core/platform/platform.contracts';
import { ModalHelperService, VerificationDialogParams, VerificationRequiredError } from './verification.model';

export const VERIFICATION_DIALOG_COMPONENT = new InjectionToken<Type<unknown>>('VERIFICATION_DIALOG_COMPONENT');
export const LEGACY_VERIFICATION_DIALOG_COMPONENT = new InjectionToken<Type<unknown>>(
  'LEGACY_VERIFICATION_DIALOG_COMPONENT',
);

interface VerificationErrorBody {
  readonly info?: string;
}

export const verificationInterceptor: HttpInterceptorFn = (request, next) => {
  const modalHelper = inject(ModalHelperService);
  const responsive = inject(ResponsiveService);
  const environment = inject(APP_ENVIRONMENT);
  const dialog = inject(VERIFICATION_DIALOG_COMPONENT);
  const legacyDialog = inject(LEGACY_VERIFICATION_DIALOG_COMPONENT);

  const launchVerificationModal = (error: HttpErrorResponse) => {
    const modalOptions = {
      centered: true,
      windowClass: responsive.isDesktop() ? 'wide' : '',
    };

    if (!environment.features.verificationDialogNewFlow) {
      return modalHelper.openOkCancelModal(legacyDialog, { modalOptions });
    }

    const body = (error.error ?? {}) as VerificationErrorBody;

    return modalHelper.openOkCancelModal<VerificationDialogParams>(dialog, {
      modalOptions,
      componentParams: {
        title: { key: 'userProfile.verifyPhone.dialogIdentityBrowser' },
        image: 'assets/img/seguridad/nav-pass-blue.png',
        info: body.info,
      },
    });
  };

  return next(request).pipe(
    retryWhen((errors) =>
      errors.pipe(
        switchMap((error) => {
          const httpError = error as HttpErrorResponse;

          return httpError.status === 426
            ? launchVerificationModal(httpError).pipe(
                catchError(() =>
                  throwError(
                    () =>
                      new VerificationRequiredError(
                        403,
                        'no_verificado',
                        'userProfile.verifyPhone.verificationBrowserNeeded',
                        true,
                      ),
                  ),
                ),
              )
            : throwError(() => httpError);
        }),
      ),
    ),
  );
};
