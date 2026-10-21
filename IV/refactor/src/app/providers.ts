import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { EnvironmentProviders, makeEnvironmentProviders, provideAppInitializer, inject } from '@angular/core';
import { AUTH_INTERCEPTORS } from '@core/auth/auth.interceptors';
import { AppInitializerService } from '@core/app/app-initializer.service';
import { HTTP_HEADER_INTERCEPTORS } from '@core/http/http.interceptors';
import { maintenanceInterceptor } from '@core/http/maintenance.interceptor';
import { verificationInterceptor } from '@features/verification/verification.interceptor';

export function provideApi(): EnvironmentProviders {
  return makeEnvironmentProviders([
    provideHttpClient(
      withInterceptors([
        ...AUTH_INTERCEPTORS,
        ...HTTP_HEADER_INTERCEPTORS,
        maintenanceInterceptor,
        verificationInterceptor,
      ]),
    ),
    provideAppInitializer(() => {
      const initializer = inject(AppInitializerService);
      initializer.initialize();
      return initializer.checkDataIntegrity();
    }),
  ]);
}
