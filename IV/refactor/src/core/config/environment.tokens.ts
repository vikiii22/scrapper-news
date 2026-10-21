import { InjectionToken } from '@angular/core';

export interface EnvironmentFeatures {
  readonly verificationDialogNewFlow: boolean;
}

export interface GoogleMapsConfig {
  readonly apikey: string;
  readonly defaultZoomIn: number;
}

export interface EnvironmentLocaleRoutes {
  readonly promoParam: string;
  readonly contactUs: string;
}

export interface EnvironmentLocale {
  readonly locale: string;
  readonly routes: EnvironmentLocaleRoutes;
}

export interface EnvironmentMaintenance {
  redirectUrl(localeAbbr: string): string;
}

export interface EnvironmentLogger {
  readonly endpoint: string;
}

export interface EnvironmentGeolocation {
  readonly defaultAnonimousStateCode: string;
}

export interface Environment {
  readonly endpoint: string;
  readonly enableAuthDomains?: readonly string[];
  readonly defaultHeaders: Readonly<Record<string, string>>;
  readonly appVersion: string;
  readonly production: boolean;
  readonly globalDomain: string;
  readonly enableLocalStorageMigration?: boolean;
  readonly noDeleteAllInfoInVersionURL: string;
  readonly localStorageKeys: Readonly<Record<string, string>>;
  readonly locale: EnvironmentLocale;
  readonly features: EnvironmentFeatures;
  readonly google: {
    readonly clientId: string;
    readonly maps: GoogleMapsConfig;
  };
  readonly apple: { readonly clientId: string };
  readonly maintenance: EnvironmentMaintenance;
  readonly logger: EnvironmentLogger;
  readonly geolocation: EnvironmentGeolocation;
  readonly verification?: { readonly maxTimeBlockedUser: number };
}

export const APP_ENVIRONMENT = new InjectionToken<Environment>('APP_ENVIRONMENT');
export const API_ENDPOINT = new InjectionToken<string>('API_ENDPOINT');
export const DEFAULT_HEADERS = new InjectionToken<Readonly<Record<string, string>>>('DEFAULT_HEADERS');
export const BROWSER_LANGUAGE = new InjectionToken<string>('BROWSER_LANGUAGE');
