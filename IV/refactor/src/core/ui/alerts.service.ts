export interface AlertMessage {
  readonly key: string;
  readonly params?: Readonly<Record<string, unknown>>;
}

export abstract class AlertsService {
  abstract notifyError(message: string | AlertMessage): void;
  abstract notifySuccess(message: string | AlertMessage): void;
}
