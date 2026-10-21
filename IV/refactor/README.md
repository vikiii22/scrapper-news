# Tulotero chunk — reconstrucción TypeScript

Reconstrucción tipada del chunk Angular `IV/tulotero-chunk.js` (formateado con Prettier en el mismo directorio).
La lógica se conserva: mismo orden de interceptores, mismas condiciones de refresco de token, mismos endpoints,
mismos efectos sobre `localStorage`, misma secuencia de navegación y mismos diálogos.

## Estructura

```
src/
  app/providers.ts                         provideHttpClient + withInterceptors + APP_INITIALIZER
  core/
    app/
      app-initializer.service.ts           arranque, integridad de versión, analítica, promo, campañas
      version-hooks.service.ts             hooks de versión, migración de storage, versions-web.json
    auth/
      auth.model.ts                        AuthTokens, JwtAuthStrategy, SessionAuthStore, SessionService
      auth.tokens.ts                       tokens DI + cabeceras
      session-auth.interceptor.ts          inyección de Authorization / marca X-Token-Expired
      token-refresh.interceptor.ts         refresco proactivo con Subject compartido
      session-expiry.interceptor.ts        401/403 -> redirectUrl + logout
      fraud-detection.interceptor.ts       FRAUD_DETECTED -> logout + alerta
      auth.interceptors.ts                 orden de registro
    config/environment.tokens.ts           Environment + tokens de configuración
    errors/server-error.handler.ts         ErrorHandler global
    http/
      http.context.ts                      HttpContextToken (skip auth, idioma, mantenimiento)
      default-headers.interceptor.ts       cabeceras por defecto
      cache-buster.interceptor.ts          ngTime
      accept-language.interceptor.ts       Accept-Language
      maintenance.interceptor.ts           503 -> redirección
      legacy-proxy.interceptor.ts          reescritura origen -> proxy
      http.interceptors.ts                 orden de registro
    i18n/                                  LocaleService y tl-translatable-text
    platform/                              contratos de responsive/rutas/logger y token Window
    routing/
      campaign-tracking.service.ts         params de campaña (cid, pid, utm_*)
      campaign-params.guard.ts             preservación de params
      platform-route.guard.ts              coherencia desktop/mobile
      page-controller.service.ts           open/resolve/reject + traza
      meta-router.service.ts               title + meta tags desde route.data
      redirect-url.service.ts              URL de retorno tras expirar sesión
    storage/                               localStorage/sessionStorage/in-memory + migración
    ui/                                    AlertsService y tl-modal-dialog
  features/
    verification/                          interceptor 426 + diálogo de código SMS
    user-events/                           eventos de depósito y DAO
    geolocation/                           estado por IP/CP/accountStateCode
    play/                                  cookie landing_play
    matches/                               adaptación de partidos/quinigol
  shared/
    device/device-info.service.ts          UA parser + high entropy values
    interaction/long-press.plugin.ts       tlpress / tlpressup
    ui/popper.config.ts                    modificador arrow
```

## Correspondencia de símbolos

### Autenticación e interceptores

| Original | Reconstrucción | Fichero |
| --- | --- | --- |
| `Yl` | `sessionAuthInterceptor` | `core/auth/session-auth.interceptor.ts` |
| `$l` | `TokenRefreshCoordinator` / `tokenRefreshInterceptor` | `core/auth/token-refresh.interceptor.ts` |
| `Zl` | `sessionExpiryInterceptor` | `core/auth/session-expiry.interceptor.ts` |
| `Xl` | `fraudDetectionInterceptor` + `FraudDetectedError` | `core/auth/fraud-detection.interceptor.ts` |
| `Jl` | `AUTH_INTERCEPTORS` | `core/auth/auth.interceptors.ts` |
| `Wr` | `TOKEN_EXPIRED_HEADER` | `core/auth/auth.tokens.ts` |
| `Nr` | `SessionAuthStore` | `core/auth/auth.model.ts` |
| `he` | `SessionService` | `core/auth/auth.model.ts` |
| `rc` | `AuthStrategyManager` | `core/auth/auth.model.ts` |
| `ic.JWT` | `AuthStrategyType.JWT` | `core/auth/auth.model.ts` |
| `ec` | `FraudDetectedError` | `core/auth/fraud-detection.interceptor.ts` |
| `tc` | `VerificationRequiredError` | `features/verification/verification.model.ts` |

### HTTP

| Original | Reconstrucción | Fichero |
| --- | --- | --- |
| `Cl` | `defaultHeadersInterceptor` | `core/http/default-headers.interceptor.ts` |
| `Pl` | `cacheBusterInterceptor` | `core/http/cache-buster.interceptor.ts` |
| `Nl` | `acceptLanguageInterceptor` | `core/http/accept-language.interceptor.ts` |
| `_l` | `HTTP_HEADER_INTERCEPTORS` | `core/http/http.interceptors.ts` |
| `fp` | `legacyProxyInterceptor` | `core/http/legacy-proxy.interceptor.ts` |
| `gp` | `maintenanceInterceptor` | `core/http/maintenance.interceptor.ts` |
| `yr` | `SKIP_AUTH` | `core/http/http.context.ts` |
| `Ca` | `USE_BROWSER_LANGUAGE` | `core/http/http.context.ts` |
| `Pa` | `ACCEPT_ANY_LANGUAGE` | `core/http/http.context.ts` |
| `Na` | `SKIP_MAINTENANCE_REDIRECT` | `core/http/http.context.ts` |
| `Um` | `verificationInterceptor` | `features/verification/verification.interceptor.ts` |
| `Fm` | `VerificationDialogComponent` | `features/verification/verification-dialog.component.ts` |
| `Lm` | `LEGACY_VERIFICATION_DIALOG_COMPONENT` | `features/verification/verification.interceptor.ts` |

### Almacenamiento

| Original | Reconstrucción | Fichero |
| --- | --- | --- |
| `kl` | `BrowserStorageService` (localStorage) | `core/storage/browser-storage.service.ts` |
| `Bl` | `BrowserStorageService` (sessionStorage) | `core/storage/browser-storage.service.ts` |
| `Vr` | `InMemoryStorageService` | `core/storage/browser-storage.service.ts` |
| `Tp` / `_p` | `localStorageFactory` / `sessionStorageFactory` | `core/storage/browser-storage.service.ts` |
| `zl` | `AsyncLocalStorageService` | `core/storage/async-local-storage.service.ts` |
| `Gr` | `StorageMigrationService` | `core/storage/storage-migration.service.ts` |
| `Hl` / `Vl` / `jl` / `bm` | `StorageModule` | `core/storage/storage.module.ts` |

### Routing y aplicación

| Original | Reconstrucción | Fichero |
| --- | --- | --- |
| `Kr` | `CampaignTrackingService` | `core/routing/campaign-tracking.service.ts` |
| `Le` | `CampaignParamsGuard` | `core/routing/campaign-params.guard.ts` |
| `Xe` | `PlatformRouteGuard` | `core/routing/platform-route.guard.ts` |
| `Ol` | `PageControllerService` | `core/routing/page-controller.service.ts` |
| `xl` | `MetaRouterService` | `core/routing/meta-router.service.ts` |
| `Wl` | `ServerErrorHandler` | `core/errors/server-error.handler.ts` |
| `eo` | `AppInitializerService` | `core/app/app-initializer.service.ts` |
| `Xr` | `VersionMismatchService` | `core/app/version-hooks.service.ts` |
| `Sm` | `StorageMigrationHooksService` | `core/app/version-hooks.service.ts` |
| `Em` | `DeleteAllInfoInVersionService` | `core/app/version-hooks.service.ts` |
| `$r` / `ln` | `VersionRangeModel` | `core/app/version-hooks.service.ts` |

### Features y shared

| Original | Reconstrucción | Fichero |
| --- | --- | --- |
| `ql` | `UserEventsService` | `features/user-events/user-events.service.ts` |
| `Gl` | `HttpUserEventsDao` | `features/user-events/user-events.dao.ts` |
| `tn` | `UserEventType` | `features/user-events/user-events.service.ts` |
| `qa` | `DepositMethod` | `features/user-events/user-events.service.ts` |
| `Ai` | `UpdateStateAppListenerService` | `features/geolocation/update-state-app-listener.service.ts` |
| `Tm` | `LandingPlayService` | `features/play/landing-play.service.ts` |
| `Hm` | `MatchesService` | `features/matches/matches.service.ts` |
| `Br` | `DeviceInfoService` | `shared/device/device-info.service.ts` |
| `wl` | `HighEntropyDeviceInfoService` | `shared/device/device-info.service.ts` |
| `ei` | `PressInteraction` | `shared/interaction/long-press.plugin.ts` |
| `zr` | `LongPressInteraction` | `shared/interaction/long-press.plugin.ts` |
| `Hr` | `LongPressReleaseInteraction` | `shared/interaction/long-press.plugin.ts` |
| `Fl` | `LongPressEventPlugin` | `shared/interaction/long-press.plugin.ts` |
| `Pp` / `Np` | `ARROW_PADDING` / `withArrowModifier` | `shared/ui/popper.config.ts` |
| `Dl` | (plugin de teclado, sin cambios funcionales) | — |

## Decisiones de refactor

- Interceptores funcionales (`HttpInterceptorFn`) con `inject()`, registrados en `withInterceptors` en el orden
  `sessionAuth -> tokenRefresh -> sessionExpiry -> headers -> maintenance -> verification`.
- El estado compartido del refresco (`isRefreshing`, `refresh$`) vive en `TokenRefreshCoordinator`, singleton,
  para conservar la semántica de instancia única del interceptor original.
- Los contratos que provenían de otros chunks (`Nr`, `he`, `rc`, `y`, `Z`, ...) se modelan como clases abstractas
  o `InjectionToken`, de forma que la app real solo tenga que enlazarlos con `useExisting`/`useClass`.
- Se mantienen las mutaciones observadas en el original (`delete meta.title`, `info.maxAttemptsReached = true`,
  escritura de la cookie `landing_play`, `localStorage` de `appVersion`).
- `VerificationRequiredError` reproduce el error lanzado tras el 426 (`403`, `no_verificado`,
  `userProfile.verifyPhone.verificationBrowserNeeded`, silencioso).
- El refresco de token conserva el marcador `X-Token-Expired` y la distinción entre refresco bloqueante y
  refresco en segundo plano con `catchError(() => EMPTY)`.

## Verificación contra Tulotero real

### 1. Procedencia del código

El chunk local es el bundle `main-C3X6YJSJ.js` que sirve **`web.tulotero.es`** (la aplicación). Ojo:
`www.tulotero.es` sirve la landing con otro bundle pequeño; no es la app.

`npm run verify:provenance` descarga el `main-*.js` publicado y compara los AST (no los bytes, porque el
local está formateado con Prettier) con `IV/tulotero-chunk.js`:

```text
local : IV/tulotero-chunk.js
live  : https://web.tulotero.es/main-C3X6YJSJ.js
bytes : local=324160 live=220219
AST_EQUAL true
MARKER X-Token-Expired local=true live=true
MARKER no_verificado local=true live=true
MARKER verificationBrowserNeeded local=true live=true
MARKER device_verification_complete local=true live=true
MARKER landing_play local=true live=true
```

Si Tulotero publica otro build, el script imprime `DRIFT` y sale con código 1.

### 2. Configuración real

Valores tomados de `chunk-HQZV36DJ.js` del build de producción:

| Clave | Valor real |
| --- | --- |
| `endpoint` | `https://web-backend.es.tulotero.net/tuloteroweb/rest` |
| `logger.endpoint` | `https://web-backend.es.tulotero.net/kibana` |
| `staticEndpoint` | `https://static.tulotero.net` |
| `defaultHeaders` | `{ AvoidRedirect: "true", Client: "web" }` |
| `appVersion` | `1389` |
| `features.verificationDialogNewFlow` | `true` |
| `noDeleteAllInfoInVersionURL` | `https://static.tulotero.net/versions-web.json` |
| `localStorageKeys.token` | `0x01` |
| `localStorageKeys.refreshToken` | `0x45` |

La demo ya usa estos valores en lugar de placeholders.

### 3. API real

`npm run verify:live` ejecuta el `MatchesService` reconstruido contra el backend de producción:

```text
count: 15
types: ["partidos", "pleno15"]
first: Oporto (m) 0 - 1 Psv (m)
resultValues: ["2"]
LIVE_SHAPE_OK true
```

El contrato `BackendMatchesResponse` (`partidos[].local`, `visitante`, `marcador`, `signo`, `escudo1`,
`suspended`, ...) coincide con la respuesta real de `/sorteos/11357/partidos`. El servicio aplica después
`createFromBackend`, igual que el original: `pictureUrl` -> `emblem` y `resultInfo.values` -> `resultValues`.

También se probó `11369` (Quinigol): devuelve 6 partidos y el servicio toma la rama `adaptQuinigolMatches`
(`typeId: "match"`), sin `resultValues` porque aún no hay resultado.

### 4. Interceptores

La demo ejercita los tres flujos con los valores reales de entorno:

| Botón | Resultado verificado |
| --- | --- |
| Petición normal | `Authorization: Bearer access-token-v1` |
| Token a punto de caducar | `X-Token-Expired` -> refresco -> reintento con `access-token-v2` |
| Respuesta 401 | `redirectUrl` + `logout()` -> sesión cerrada |

### Límites

- La reconstrucción cubre el bundle `main`; los ~389 chunks lazy de la app no se han reconstruido.
- Los contratos de otros chunks (`Nr`, `he`, `rc`, `y`, ...) son stubs en la demo; en producción se enlazan
  con las implementaciones reales.
- No se prueba un login real (requiere credenciales); el refresco se simula respetando el mismo contrato.

`tsc --noEmit` pasa con `strict: true` contra Angular 19 y RxJS 7.

```bash
npm install
npm run typecheck
npm run verify:provenance
npm run verify:live
npm start          # http://localhost:4200
```

## Demo

`demo/` monta un Angular standalone con backend simulado (interceptor `echoBackendInterceptor`) y tres escenarios:

| Botón | Flujo ejercitado |
| --- | --- |
| Petición normal | `sessionAuthInterceptor` añade `Authorization: Bearer access-token-v1` |
| Token a punto de caducar | `sessionAuthInterceptor` marca `X-Token-Expired`; `TokenRefreshCoordinator` refresca y reintenta con `access-token-v2` |
| Respuesta 401 | `sessionExpiryInterceptor` guarda la URL y ejecuta `logout()` |

La demo sustituye las implementaciones reales (`Nr`, `he`, `rc`, `y`, ...) por stubs en `demo/demo.providers.ts`.

