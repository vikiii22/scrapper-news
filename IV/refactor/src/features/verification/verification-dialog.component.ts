import { NgIf } from '@angular/common';
import { ChangeDetectorRef, Component, inject, Input, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { map, Observable, Subject, take, takeUntil, tap, timer } from 'rxjs';
import { APP_ENVIRONMENT } from '@core/config/environment.tokens';
import { TranslatableTextComponent } from '@core/i18n/translatable-text.component';
import { ResponsiveService } from '@core/platform/platform.contracts';
import { ModalComponent } from '@core/ui/modal.component';
import { MeasuringService, UserService } from '@features/user-events/user-events.service';

export enum VerificationScreen {
  REQUEST_CODE_FAILED = 'requestCodeFailed',
  DEVICE_BLOCKED = 'deviceBlocked',
  INITIAL_SCREEN = 'initialScreen',
  INITIAL_SCREEN_ON_ERROR = 'initialScreenOnError',
  CONFIRM_CODE_SUCCESS = 'confirmCodeSuccess',
  INSERT_VERIFICATION_CODE = 'insertVerificationCode',
}

export interface TranslatableText {
  readonly key: string;
  readonly keyData?: Record<string, string>;
}

export interface VerificationInfo {
  maxAttemptsReached?: boolean;
  minutesForWaitNextSMS?: number;
  secondsToRetry?: number;
  smsSentOnThisRequest?: boolean;
  dateSendLast?: number;
  lastTimeSmsSent?: number;
}

export interface VerificationError {
  readonly status?: string;
  readonly message?: string;
  readonly error?: VerificationInfo;
}

export interface ProcessedError {
  readonly status?: string;
  readonly message?: string;
}

export abstract class VerificationViewService {
  abstract confirmCode(code: string): Observable<unknown>;
  abstract requestCode(): Observable<unknown>;
}

export abstract class ErrorProcessingService {
  abstract processErrorManually(error: unknown): ProcessedError;
}

export interface VerificationDialogRef {
  close(result?: unknown): void;
  dismiss(result?: unknown): void;
}

@Component({
  selector: 'tl-verification-dialog',
  standalone: true,
  imports: [NgIf, ReactiveFormsModule, ModalComponent, TranslatableTextComponent],
  templateUrl: './verification-dialog.component.html',
})
export class VerificationDialogComponent implements OnInit, OnDestroy {
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly errorService = inject(ErrorProcessingService);
  private readonly responsive = inject(ResponsiveService);
  private readonly verificationView = inject(VerificationViewService);
  private readonly userService = inject(UserService);
  private readonly measuring = inject(MeasuringService);
  private readonly router = inject(Router);
  private readonly environment = inject(APP_ENVIRONMENT);

  @ViewChild(ModalComponent, { static: true })
  dialog!: VerificationDialogRef;

  readonly wrongCode = new FormControl('', { nonNullable: true });
  readonly form = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.minLength(4), Validators.maxLength(5)],
  });

  readonly idVerificationInvalidMaxAttemptsReached = 'ID_VERIFICATION_INVALID_MAX_ATTEMPTS_REACHED';

  @Input() info: VerificationInfo = {};

  private readonly destroySubject = new Subject<void>();

  screen: VerificationScreen = VerificationScreen.INITIAL_SCREEN;
  confirmButtonAction = 'confirm';
  isLoading = false;
  submitted = false;
  showInformation = true;
  inputError = false;
  showDescriptionText = true;
  hostClass = true;
  phone = '';
  title?: TranslatableText;
  image?: string;
  descriptionText: TranslatableText = { key: '' };
  sendButtonText: TranslatableText = { key: '' };
  errorTimer?: TranslatableText;
  buttonCallBack: () => boolean = () => true;

  get routeMap() {
    return this.environment.locale.routes;
  }

  get isMobile(): boolean {
    return !this.responsive.isDesktop();
  }

  get showForm(): boolean {
    return this.screen === VerificationScreen.INSERT_VERIFICATION_CODE;
  }

  get enableButton(): boolean {
    return this.screen !== VerificationScreen.REQUEST_CODE_FAILED;
  }

  get isDeviceBlocked(): boolean {
    return this.screen === VerificationScreen.INITIAL_SCREEN_ON_ERROR;
  }

  get hasActiveCode(): boolean {
    return (
      (!this.isLoading && this.screen === VerificationScreen.INITIAL_SCREEN) ||
      this.screen === VerificationScreen.REQUEST_CODE_FAILED
    );
  }

  get disableButton(): boolean {
    return (
      this.screen === VerificationScreen.INSERT_VERIFICATION_CODE &&
      (this.form.invalid || !!this.wrongCode.value)
    );
  }

  ngOnInit(): void {
    this.userService
      .getData()
      .pipe(take(1))
      .subscribe((user) => {
        this.phone = user?.phone ? `${user.phonePrefix ?? ''}${user.phone}` : '';
      });

    this.configureScreen(
      this.shouldShowInitialScreen()
        ? VerificationScreen.INITIAL_SCREEN
        : VerificationScreen.INITIAL_SCREEN_ON_ERROR,
    );
  }

  ngOnDestroy(): void {
    this.destroy();
  }

  confirmCode(): boolean {
    this.submitted = true;
    this.isLoading = true;

    if (this.form.invalid) {
      this.isLoading = false;
      return false;
    }

    this.verificationView.confirmCode(this.form.value).subscribe({
      next: () => {
        this.isLoading = false;
        this.submitted = false;
        this.configureScreen(VerificationScreen.CONFIRM_CODE_SUCCESS);
      },
      error: (error: unknown) => {
        const processed = this.errorService.processErrorManually(error);

        if (processed.status === this.idVerificationInvalidMaxAttemptsReached) {
          this.configureScreen(VerificationScreen.DEVICE_BLOCKED);
          return;
        }

        if (processed.message) {
          this.wrongCode.setValue(processed.message);
          this.inputError = true;
          this.isLoading = false;
          this.submitted = false;
        }
      },
    });

    return true;
  }

  closeDialog(action: string): void {
    if (action === 'cancel') {
      this.dialog.dismiss(action);
    }

    this.dialog.close(action);
  }

  goToContact(): void {
    const contactUrl = this.isMobile ? `/m/${this.routeMap.contactUs}` : `/${this.routeMap.contactUs}`;
    void this.router.navigateByUrl(contactUrl);
    this.closeDialog('cancel');
  }

  displayContactLink(): boolean {
    return this.descriptionText.key.includes('errorContact');
  }

  validateInput(event: KeyboardEvent | ClipboardEvent): boolean {
    if (event instanceof KeyboardEvent) {
      return !!event.key?.match(/[0-9]|Backspace|Delete/);
    }

    if (event.type === 'paste') {
      const text = (event as ClipboardEvent).clipboardData?.getData('text/plain').trim();
      return !!text?.match(/[0-9]/);
    }

    return false;
  }

  pasteNumbers(event: ClipboardEvent): void {
    event.preventDefault();
    const text = event.clipboardData?.getData('text/plain').trim() ?? '';
    const digits = text.replace(/[^0-9]/g, '');

    if (digits) {
      (event.target as HTMLInputElement).value = digits;
    }

    this.form.setValue((event.target as HTMLInputElement).value);
  }

  goInsertCode(): void {
    this.isLoading = false;
    this.configureScreen(VerificationScreen.INSERT_VERIFICATION_CODE);
  }

  goInitialScreen(): void {
    this.configureScreen(VerificationScreen.INITIAL_SCREEN);
  }

  requestNewCode(): void {
    this.isLoading = true;

    this.verificationView.requestCode().subscribe({
      next: () => {
        this.submitted = false;
        this.isLoading = false;
        this.configureScreen(VerificationScreen.INSERT_VERIFICATION_CODE);
      },
      error: (error: VerificationError) => {
        this.submitted = false;
        this.isLoading = false;
        Object.assign(this.info, this.parseError(error.error ?? {}));

        this.configureScreen(
          this.info.minutesForWaitNextSMS
            ? VerificationScreen.REQUEST_CODE_FAILED
            : VerificationScreen.DEVICE_BLOCKED,
        );
      },
    });
  }

  private cleanErrors(): void {
    this.inputError = false;
    this.submitted = false;
    this.wrongCode.setValue('');
    this.cdr.markForCheck();
  }

  private shouldShowInitialScreen(): boolean {
    return !this.info.smsSentOnThisRequest && !this.info.maxAttemptsReached;
  }

  private setErrorInterval(seconds: number, message: TranslatableText, updateTimer = true): void {
    this.cdr.markForCheck();
    this.destroy();

    let finished = false;

    timer(0, 1000)
      .pipe(
        take(seconds),
        map((elapsed) => seconds - elapsed),
        tap((remaining) => (finished = remaining - 1 === 0)),
        takeUntil(this.destroySubject),
      )
      .subscribe({
        next: (remaining) => {
          if (updateTimer) {
            this.errorTimer = this.formatErrorMessage(message, remaining);
            this.cdr.markForCheck();
          }
        },
        complete: () => {
          if (finished) {
            this.configureScreen(VerificationScreen.INITIAL_SCREEN);
          }

          this.cleanErrors();
          this.cdr.markForCheck();
        },
      });
  }

  private destroy(): void {
    this.destroySubject.next();
  }

  private configureScreen(screen: VerificationScreen): void {
    this.screen = screen;
    this.destroy();

    switch (screen) {
      case VerificationScreen.REQUEST_CODE_FAILED:
        this.buildModalRequestCodeFailed();
        break;
      case VerificationScreen.DEVICE_BLOCKED:
        this.buildModalDeviceBlocked();
        break;
      case VerificationScreen.INITIAL_SCREEN:
        this.buildModalInitialScreen();
        break;
      case VerificationScreen.INITIAL_SCREEN_ON_ERROR:
        this.buildModalInitialScreenOnError();
        break;
      case VerificationScreen.CONFIRM_CODE_SUCCESS:
        this.buildModalCodeSuccess();
        break;
      case VerificationScreen.INSERT_VERIFICATION_CODE:
        this.buildModalInsertVerificationCode();
        break;
    }

    this.cdr.markForCheck();
  }

  private buildModalRequestCodeFailed(): void {
    this.title = { key: 'userProfile.verifyPhone.dialogIdentityBrowser' };
    this.info.maxAttemptsReached = true;

    const message: TranslatableText = {
      key: 'userProfile.verifyPhone.errorSubtitle',
      keyData: { time: '' },
    };

    this.setErrorInterval(
      this.calculateWaitSeconds((this.info.minutesForWaitNextSMS ?? 0) * 60 * 1000, this.info.dateSendLast ?? 0),
      message,
      true,
    );

    this.showDescriptionText = true;
    this.descriptionText = { key: 'userProfile.verifyPhone.dialogDescriptionInfoBrowser' };
    this.sendButtonText = { key: 'userProfile.verifyPhone.successButom' };
    this.wrongCode.setValue('userProfile.verifyPhone.verificationCodeError');
    this.showInformation = true;
    this.confirmButtonAction = 'cancel';
    this.buttonCallBack = () => this.buttonRequestCodeFailed();
  }

  private buttonRequestCodeFailed(): boolean {
    this.submitted = false;
    this.isLoading = false;
    this.configureScreen(VerificationScreen.INSERT_VERIFICATION_CODE);
    return true;
  }

  private buildModalDeviceBlocked(): void {
    this.confirmButtonAction = 'cancel';
    this.title = { key: 'userProfile.verifyPhone.errorTitleBrowser' };
    this.image = 'assets/img/seguridad/nav-pass-red.png';
    this.info.maxAttemptsReached = true;

    const message: TranslatableText = {
      key: 'userProfile.verifyPhone.errorSubtitle',
      keyData: { time: '' },
    };

    this.setErrorInterval(this.environment.verification?.maxTimeBlockedUser ?? 0, message);
    this.showDescriptionText = true;
    this.showInformation = false;
    this.isLoading = false;
    this.descriptionText = { key: 'userProfile.verifyPhone.errorContact' };
    this.sendButtonText = { key: 'userProfile.verifyPhone.successButom' };
    this.wrongCode.setValue('userProfile.verifyPhone.verificationCodeError');
    this.buttonCallBack = () => this.buttonCloseModal();
  }

  private buttonCloseModal(): boolean {
    this.closeDialog(this.confirmButtonAction);
    return true;
  }

  private buildModalInitialScreen(): void {
    this.showDescriptionText = true;
    this.descriptionText = { key: 'userProfile.verifyPhone.dialogDescriptionInfoBrowser' };
    this.submitted = false;
    this.sendButtonText = { key: 'userProfile.verifyPhone.sendCode' };
    this.buttonCallBack = () => this.buttonInitialScreen();
  }

  private buttonInitialScreen(): boolean {
    this.requestNewCode();
    return true;
  }

  private buildModalInitialScreenOnError(): void {
    this.confirmButtonAction = 'cancel';
    this.title = { key: 'userProfile.verifyPhone.errorTitleBrowser' };
    this.image = 'assets/img/seguridad/nav-pass-red.png';
    this.showDescriptionText = true;
    this.descriptionText = { key: 'userProfile.verifyPhone.errorContact' };
    this.sendButtonText = { key: 'userProfile.verifyPhone.successButom' };
    this.wrongCode.setValue('userProfile.verifyPhone.verificationCodeError');
    this.buttonCallBack = () => this.buttonCloseModal();

    const message: TranslatableText = {
      key: 'userProfile.verifyPhone.retryExpiredCodeDisabled',
      keyData: { message: '' },
    };

    this.showInformation = false;
    this.setErrorInterval(this.info.secondsToRetry ?? 0, message);
  }

  private buildModalCodeSuccess(): void {
    this.measuring.sendTagManagerEvent('device_verification_complete', {});
    this.confirmButtonAction = 'success';
    this.title = { key: 'userProfile.verifyPhone.successTitleBrowser' };
    this.showDescriptionText = true;
    this.descriptionText = { key: 'userProfile.verifyPhone.successSubtitle' };
    this.sendButtonText = { key: 'userProfile.verifyPhone.successButom' };
    this.image = 'assets/img/seguridad/nav-pass-green.png';
    this.showInformation = false;
    this.buttonCallBack = () => this.buttonCloseModal();
  }

  private buildModalInsertVerificationCode(): void {
    this.measuring.sendTagManagerEvent('device_verification_start', {});
    this.sendButtonText = { key: 'userProfile.verifyPhone.verifyCode' };
    this.showDescriptionText = false;
    this.cleanErrors();
    this.title = { key: 'userProfile.verifyPhone.titleCode' };
    this.form.reset();
    this.buttonCallBack = () => this.confirmCode();
  }

  private parseError(error: VerificationInfo): VerificationInfo {
    return {
      dateSendLast: error.dateSendLast,
      minutesForWaitNextSMS: error.minutesForWaitNextSMS,
      secondsToRetry: error.secondsToRetry,
      smsSentOnThisRequest: error.smsSentOnThisRequest,
      lastTimeSmsSent: error.lastTimeSmsSent,
    };
  }

  private formatErrorMessage(template: TranslatableText, value: number): TranslatableText {
    const keyData = { ...(template.keyData ?? {}) };
    const [firstKey] = Object.keys(keyData);

    if (firstKey) {
      keyData[firstKey] = this.formatSeconds(value);
    }

    return { ...template, keyData };
  }

  private calculateWaitSeconds(durationMs: number, startDate: number): number {
    const elapsed = Date.now() - startDate;
    const remaining = Math.ceil((durationMs - elapsed) / 1000);
    return remaining > 0 ? remaining : 0;
  }

  private formatSeconds(seconds: number): string {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  }
}
