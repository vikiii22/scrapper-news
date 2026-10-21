import { DOCUMENT } from '@angular/common';
import { inject, Injectable } from '@angular/core';
import { ResponsiveService } from '@core/platform/platform.contracts';

type EventHandler = (event: Event) => void;

export type LongPressMode = 'tlpress' | 'tlpressup';

const LONG_PRESS_DELAY_MS = 250;

export abstract class PressInteraction {
  protected readonly startEvent: string;
  protected readonly endEvents: readonly string[];

  private readonly startListener = (event: Event): void => this.startHandler(event);
  private readonly endListener = (event: Event): void => this.endHandler(event);

  constructor(
    protected readonly responsive: ResponsiveService,
    protected readonly element: HTMLElement,
    protected readonly originalHandler: EventHandler,
    protected readonly doc: Document,
  ) {
    if (responsive.isDesktop()) {
      this.startEvent = 'mousedown';
      this.endEvents = ['mouseup'];
      this.endEvents.forEach((eventName) => doc.addEventListener(eventName, this.endListener));
    } else {
      this.startEvent = 'touchstart';
      this.endEvents = ['touchend', 'touchcancel'];
      this.endEvents.forEach((eventName) => element.addEventListener(eventName, this.endListener));
    }

    element.addEventListener(this.startEvent, this.startListener);
  }

  abstract startHandler(event: Event): void;
  abstract endHandler(event: Event): void;

  readonly onDestroy = (): void => {
    this.element.removeEventListener(this.startEvent, this.startListener);

    if (this.responsive.isDesktop()) {
      this.endEvents.forEach((eventName) => this.doc.removeEventListener(eventName, this.endListener));
    } else {
      this.endEvents.forEach((eventName) => this.element.removeEventListener(eventName, this.endListener));
    }
  };
}

export class LongPressInteraction extends PressInteraction {
  private timer?: ReturnType<typeof setTimeout>;

  override startHandler = (event: Event): void => {
    this.timer = setTimeout(() => {
      this.originalHandler(event);
      clearTimeout(this.timer);
    }, LONG_PRESS_DELAY_MS);
  };

  override endHandler = (): void => {
    clearTimeout(this.timer);
  };
}

export class LongPressReleaseInteraction extends PressInteraction {
  private longPress = false;
  private timer?: ReturnType<typeof setTimeout>;

  override startHandler = (): void => {
    this.timer = setTimeout(() => {
      this.longPress = true;
    }, LONG_PRESS_DELAY_MS);
  };

  override endHandler = (event: Event): void => {
    clearTimeout(this.timer);

    if (this.longPress) {
      this.originalHandler(event);
      this.longPress = false;
    }
  };
}

@Injectable({ providedIn: 'root' })
export class LongPressEventPlugin {
  private readonly doc = inject(DOCUMENT);
  private readonly responsive = inject(ResponsiveService);

  supports(eventName: string): boolean {
    return eventName === 'tlpress' || eventName === 'tlpressup';
  }

  addEventListener(element: HTMLElement, eventName: LongPressMode, handler: EventHandler): () => void {
    const interaction =
      eventName === 'tlpress'
        ? new LongPressInteraction(this.responsive, element, handler, this.doc)
        : new LongPressReleaseInteraction(this.responsive, element, handler, this.doc);

    return interaction.onDestroy;
  }

  addGlobalEventListener(target: string, eventName: string, handler: EventHandler): () => void {
    let element: HTMLElement | Document | Window | null = null;

    switch (target) {
      case 'document':
        element = this.doc;
        break;
      case 'window':
        element = this.doc.defaultView;
        break;
      case 'body':
        element = this.doc.body;
        break;
    }

    if (!element) {
      throw new Error(`Unsupported event target ${element} for event ${eventName}`);
    }

    return this.addEventListener(element as HTMLElement, eventName as LongPressMode, handler);
  }
}
