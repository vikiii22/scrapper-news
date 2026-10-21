import { Observable } from 'rxjs';

export abstract class ResponsiveService {
  abstract isDesktop(): boolean;
  abstract getPlatform(): string;
  abstract get breakpointChange(): Observable<unknown>;
}

export abstract class PlatformRoutesService {
  abstract navigateAdyacentTo(url: string): void;
  abstract navigateAdyacentRoute(strategy?: 'merge' | 'replace'): void;
  abstract assertRoutePlatform(): boolean;
}

export interface AppRoutes {
  readonly notFound: string;
}

export abstract class AppLogger {
  abstract debug(message: string, context?: unknown): void;
  abstract warn(message: string, context?: unknown): void;
  abstract error(message: string, stacktrace?: unknown, context?: unknown): void;
}
