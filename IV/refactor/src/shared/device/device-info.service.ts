import { inject, Injectable, InjectionToken, Provider } from '@angular/core';
import { combineLatest, map, Observable, of } from 'rxjs';
import { WINDOW } from '@core/platform/window.token';

export enum DeviceOs {
  ANDROID = 'Android',
  MACOS = 'macOS',
}

export interface UserAgentInfo {
  readonly browser: { readonly name: string | undefined; readonly version: string | undefined };
  readonly os: { readonly name: string; readonly version: string | undefined };
  readonly device: { readonly model: string | undefined; readonly vendor: string | undefined };
}

export interface UserAgentParser {
  readonly browser: UserAgentInfo['browser'];
  readonly os: UserAgentInfo['os'];
  readonly device: UserAgentInfo['device'];
}

export interface BrowserFingerprint {
  generate(): string;
}

export const USER_AGENT_PARSER = new InjectionToken<UserAgentParser>('USER_AGENT_PARSER');
export const BROWSER_FINGERPRINT = new InjectionToken<BrowserFingerprint>('BROWSER_FINGERPRINT');

const SAMSUNG_DEVICE_PATTERNS: readonly RegExp[] = [
  /\b(sch-i[89]0\d|shw-m380s|sm-[ptx]\w{2,4}|gt-[pn]\d{2,4}|sgh-t8[56]9|nexus 10)/i,
  /\b((?:s[cgp]h|gt|sm)-\w+|sc[g-]?[\d]+a?|galaxy nexus)/i,
  /samsung[- ]([-\w]+)/i,
  /sec-(sgh\w+)/i,
];

interface NavigatorUserAgentData {
  getHighEntropyValues(hints: readonly string[]): Promise<{
    readonly model?: string;
    readonly platform?: string;
    readonly platformVersion?: string;
  }>;
}

interface ExtendedNavigator extends Navigator {
  readonly userAgentData?: NavigatorUserAgentData;
}

@Injectable()
export class DeviceInfoService {
  protected readonly fingerprint = inject(BROWSER_FINGERPRINT);
  protected readonly parser = inject(USER_AGENT_PARSER);
  protected readonly window = inject(WINDOW);

  get isSafari(): boolean {
    return this.getBrowser()?.includes('Safari') ?? false;
  }

  get isChrome(): boolean {
    const browser = this.getBrowser();
    return typeof browser === 'string' && browser.includes('Chrome') && !browser.includes('WebView');
  }

  get isFirefox(): boolean {
    return this.getBrowser()?.includes('Firefox') ?? false;
  }

  getBrowser(): string | undefined {
    return this.parser.browser.name;
  }

  getBrowserVersion(): string | undefined {
    return this.parser.browser.version;
  }

  getOS(): string {
    return this.parser.os.name;
  }

  getOSVersion(): string | undefined {
    return this.parser.os.version;
  }

  getBrowserFingerprint(): string {
    return this.fingerprint.generate();
  }

  getPixelRatio(): number {
    return this.window.devicePixelRatio;
  }

  getModel(): Observable<string | undefined> {
    return of(this.parser.device.model);
  }

  isSamsungDevice(): Observable<boolean> {
    return of(this.parser.device.vendor?.toLowerCase() === 'samsung');
  }

  isAndroidVersion7OrLower(): Observable<boolean> {
    const os = this.getOS();
    const version = this.getOSVersion();
    return of(os.includes('Android') && !!version && parseInt(version, 10) <= 7);
  }

  toString(): string {
    return `${this.getBrowser()} (${this.getBrowserVersion()}) running over ${this.getOS()} (${this.getOSVersion()})`;
  }
}

@Injectable()
export class HighEntropyDeviceInfoService extends DeviceInfoService {
  private osCached: string | undefined;
  private osVersionCached: string | undefined;

  constructor() {
    super();
    this.setOS();
    this.setOSVersion();
  }

  override getModel(): Observable<string | undefined> {
    return this.getHighEntropyValue('model').pipe(map((values) => values.model ?? undefined));
  }

  override isSamsungDevice(): Observable<boolean> {
    return this.getModel().pipe(map((model) => SAMSUNG_DEVICE_PATTERNS.some((pattern) => pattern.test(model ?? ''))));
  }

  override getOS(): string {
    return this.osCached ?? super.getOS();
  }

  override getOSVersion(): string | undefined {
    return this.osVersionCached ?? super.getOSVersion();
  }

  override isAndroidVersion7OrLower(): Observable<boolean> {
    return combineLatest([this.getOs$(), this.getOsVersion$()]).pipe(
      map(([os, version]) => os === DeviceOs.ANDROID && !!version && parseInt(version, 10) <= 7),
    );
  }

  getOs$(): Observable<string> {
    return this.getHighEntropyValue('platform').pipe(
      map((values) => (values.platform === DeviceOs.MACOS ? DeviceOs.MACOS : (values.platform ?? ''))),
    );
  }

  getOsVersion$(): Observable<string> {
    return this.getHighEntropyValue('platformVersion').pipe(map((values) => values.platformVersion ?? ''));
  }

  private setOS(): void {
    this.getOs$().subscribe((os) => (this.osCached = os));
  }

  private setOSVersion(): void {
    this.getOsVersion$().subscribe((version) => (this.osVersionCached = version));
  }

  private getHighEntropyValue(
    hint: string,
  ): Observable<{ model?: string; platform?: string; platformVersion?: string }> {
    const navigator = this.window.navigator as ExtendedNavigator;

    if (!navigator.userAgentData) {
      return of({});
    }

    return new Observable((subscriber) => {
      navigator.userAgentData!.getHighEntropyValues([hint]).then(
        (values) => {
          subscriber.next(values);
          subscriber.complete();
        },
        (error: unknown) => subscriber.error(error),
      );
    });
  }
}

export function provideDeviceInfoService(): Provider {
  return {
    provide: DeviceInfoService,
    useFactory: () => {
      const navigator = inject(WINDOW).navigator as ExtendedNavigator;

      return navigator.userAgentData ? new HighEntropyDeviceInfoService() : new DeviceInfoService();
    },
  };
}
