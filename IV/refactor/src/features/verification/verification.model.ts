import { HttpErrorResponse } from '@angular/common/http';
import { Type } from '@angular/core';
import { Observable } from 'rxjs';

export interface ModalOptions {
  readonly centered?: boolean;
  readonly windowClass?: string;
}

export interface OkCancelModalConfig<TParams> {
  readonly modalOptions?: ModalOptions;
  readonly componentParams?: TParams;
}

export interface VerificationDialogParams {
  readonly title: { readonly key: string };
  readonly image: string;
  readonly info?: string;
}

export abstract class ModalHelperService {
  abstract openOkCancelModal<TParams>(
    component: Type<unknown>,
    config: OkCancelModalConfig<TParams>,
  ): Observable<unknown>;

  abstract openSingleActionModal<TParams>(
    component: Type<unknown>,
    config?: OkCancelModalConfig<TParams>,
  ): Observable<unknown>;
}

export class VerificationRequiredError extends HttpErrorResponse {
  constructor(
    status: number,
    readonly code: string,
    readonly translationKey: string,
    readonly silent: boolean,
  ) {
    super({
      status,
      statusText: 'Forbidden',
      error: { code, translationKey, silent },
    });
  }
}
