# Local Tulotero mirror

This directory contains a small, dependency-free Node server (Node 20+) that
serves the **published, compiled frontend** from `https://web.tulotero.es` on
localhost and proxies the production API hosts through the same origin.

It is a local interoperability/test harness, not a reimplementation of the
application and not a way to bypass authentication. Use it only with accounts
and data you are allowed to use, and do not redistribute the cached frontend.

## No confundir con la demo reconstruida

- `IV/refactor` (`npm start`, puerto `4200`) es la reconstrucción TypeScript con
  auth simulado: sirve para comparar el comportamiento, no para usar la cuenta real.
- `IV/mirror` (este directorio, puerto `4300`) sirve el front compilado original
  completo y habla con el backend real. Incluye la pantalla y los flujos de
  login, registro, juegos, resultados, etc. No hay auth simulado.

## Run

```sh
cd IV/mirror
npm start
# open http://127.0.0.1:4300/
```

The server has no npm dependencies; `node IV/mirror/server.mjs` works too.

The first request for each asset is fetched from Tulotero and cached under
`IV/mirror/.cache/`. Later runs reuse the cache. Delete the cache after a new
deployment, or start with a clean cache:

```sh
MIRROR_FRESH=1 node IV/mirror/server.mjs
```

On Windows PowerShell:

```powershell
$env:MIRROR_FRESH = "1"
node IV/mirror/server.mjs
```

## Reusing your own real session

The frontend stores its JWT session in `localStorage`, not primarily in cookies.
To reuse a session that is already logged in on `https://web.tulotero.es`:

1. Log in normally on `https://web.tulotero.es`.
2. Open DevTools → Console on that tab and run:

   ```js
   copy(JSON.stringify({
     localStorage: { ...localStorage },
     sessionStorage: { ...sessionStorage }
   }))
   ```

   The app stores the JWT in `localStorage` when "No cerrar sesión" is checked
   and in `sessionStorage` otherwise, so copy both.

3. Open `http://127.0.0.1:4300/__mirror/session`, paste the JSON and press
   **Importar y recargar**.
4. The local app should restore the session and start sending authenticated
   requests through `/backend-proxy-es`.

The page only writes to the local origin's `localStorage` (and optional
non-HttpOnly cookies); it does not send the payload to the server. Do not paste
tokens into chats, issues, screenshots or the repository. Use only your own
account. HttpOnly cookies cannot be copied from JavaScript and are usually not
needed for this frontend.

## Local phone-change tool

`/__mirror/phone` is a local-only helper for changing the phone number of your
own account. It does not modify the original frontend chunks. Instead it reuses
the exact profile payload that the app generates for `PUT /users/me`.

1. Start the mirror and log in normally.
2. Open your profile in the app (`/usuario/perfil`) and press **Guardar** once,
   even if you do not change anything. The mirror keeps the successful
   `PUT /users/me` body as a template.
3. Open `http://127.0.0.1:4300/__mirror/phone`.
4. Enter the country prefix and the new number, preview the `PUT`, and send it.
5. Enter the SMS code on the same page to complete `verifyPhoneNumber`.

The template is kept **in memory only** by the mirror process and is never
written to `.cache/` or logged. It disappears when the server restarts, and the
page has a **Borrar plantilla** button. The page reads the JWT from the local
`0x01` key (`localStorage`, falling back to `sessionStorage`), so a session
stored only in `sessionStorage` must be opened in the **same tab**: `sessionStorage`
is not shared between tabs. Open the app and the page with the **same host**
(`127.0.0.1` everywhere or `localhost` everywhere); `localhost` and `127.0.0.1`
do not share `localStorage`. The page tries both stored tokens if one is stale,
and has a **Releer sesión** button.

The page removes `newPassword` from the captured payload. A profile save starts
with an empty password form and can therefore produce `newPassword:""`; the
app's phone flow clones the loaded user instead, so that field is normally
omitted. Sending it in a phone change can make the backend interpret the request
as a password update.

This tool still uses the real backend and the real SMS verification. It does not
bypass authentication, phone validation or any anti-fraud check. Use it only
with your own account, and do not share the generated profile body or tokens.

The underlying flow is:

```text
PUT  /backend-proxy-es/tuloteroweb/rest/users/me
POST /backend-proxy-es/tuloteroweb/rest/users/inicioVerificarNumero
POST /backend-proxy-es/tuloteroweb/rest/users/verifyPhoneNumber?disableGlobalMessages=false
```

The page reads the device identifiers the original app already generated
(`0x05` for `androidRegistrationId` and `0x13` for `deviceId`) and adds the same
`deviceType`, `deviceDesc`, `osVersion`, `versionCode` and `mode` headers that
the app's interceptor adds to `/rest/users/` calls. It does not invent new
identifiers: if `0x05` or `0x13` is missing, open the app once in the same
origin so its device/fingerprint services populate them.

### Sanitized trace

`GET /__mirror/trace` returns a JSON ring buffer of the last 200 proxied
requests. It is meant for comparing the original app flow with
`/__mirror/phone`:

- method, local path, upstream path, query **keys**, referer **origin**/path and
  duration; use the origin to catch `localhost` vs `127.0.0.1` mix-ups;
- presence of `Authorization`, cookies, `deviceId` and
  `androidRegistrationId` (never their values); `authorizationHash` is a short
  SHA-256 prefix so app and page requests can be correlated without storing the
  token;
- request field names and types; phone numbers are masked, passwords/tokens are
  reported only as `[set]`/`[redacted]`; JSON sent as `text/plain` is parsed too;
- response status, top-level keys and sanitized error messages.

It never stores request/response bodies, JWTs, cookies or SMS codes. Use
`DELETE /__mirror/trace` to clear it before reproducing a flow. The page footer
links to the same endpoint.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `PORT` | `4300` | Local HTTP port |
| `HOST` | `127.0.0.1` | Bind address; keep it on localhost |
| `MIRROR_ORIGIN` | `https://web.tulotero.es` | Upstream frontend origin |
| `MIRROR_CACHE` | `IV/mirror/.cache` | Asset cache directory |
| `MIRROR_FRESH` | unset | `1` clears the cache and refetches assets |
| `MIRROR_VERBOSE` | unset | `1` logs every proxied request |

## What it does

- Serves `/`, the SPA fallback, all lazy-loaded chunks and static assets from
  the original build, fetching and caching them on demand.
- Forces the app's own `legacyProxyInterceptor` on (production disables it via
  `enableLocalProxy`) and patches the production hosts into its `qn` map in
  `main-*.js`, so the app rewrites:

  | App production URL | Local route | Upstream |
  | --- | --- | --- |
  | `https://web-backend.es.tulotero.net` | `/backend-proxy-es` | same host |
  | `https://static.es.tulotero.net` | `/tulotero-static-proxy-es` | same host |
  | `https://static.tulotero.net` | `/tulotero-static-proxy-global` | same host |
  | `https://auth.es.tulotero.net` | `/auth-proxy-es` | same host |
  | `https://public.auth.es.tulotero.net` | `/public-auth-proxy-es` | same host |
  | `https://fp.web.tulotero.es` | `/fp-proxy` | same host |

- Forwards `Origin: https://web.tulotero.es` and a matching `Referer` when
  calling the API, because the production backend only allows that CORS origin.
  Browser CORS is therefore not involved in the local API calls.
- Disables the production service worker (`serviceWorkerEnabled:!0` becomes
  `!1`) and serves a no-op worker as a fallback, so localhost does not keep an
  old build cached.
- Rewrites upstream `Location` headers and strips `Domain`/`Secure` flags from
  `Set-Cookie` so redirects and cookies work on `http://127.0.0.1`.
- Sends API requests from the Node process; the browser never receives the
  production CORS headers because it is talking to the local origin.

## Quick verification

```sh
curl -sI http://127.0.0.1:4300/
curl -s http://127.0.0.1:4300/ | head

# 15 matches for the public Quiniela query
curl -s "http://127.0.0.1:4300/backend-proxy-es/tuloteroweb/rest/sorteos/11357/partidos?imgSize=20" | head -c 400

# static JSON used by the app
curl -s "http://127.0.0.1:4300/tulotero-static-proxy-es/allinfo_es_ES.json" | head -c 200

# inspect or clear the sanitized request trace
curl -s http://127.0.0.1:4300/__mirror/trace
curl -s -X DELETE http://127.0.0.1:4300/__mirror/trace
```

Check in the browser that the shell paints, public routes open, and the network
panel shows requests going to `127.0.0.1:4300/backend-proxy-es/...` rather than
`web-backend.es.tulotero.net`.

Observed in a clean headless Chrome profile while loading
`/jugar/quiniela/11368`:

- `/tuloteroweb/rest/endpoint` → `200` via `/backend-proxy-es`
- `/tuloteroweb/rest/sorteos/11368/partidos?imgSize=20` → `200`
- `/tuloteroweb/rest/sorteos/finished?firstResult=0` → `200`
- `/tuloteroweb/rest/installation` → `200`
- `/kibana/jugar/quiniela/11368` → `200`
- no remaining direct requests to `https://web-backend.es.tulotero.net`

The public results route `/resultados/11357` also renders the live draw data.

## Authentication and limits

- Public browsing and public lottery/match endpoints work without an account.
- Login still uses Tulotero's real authentication flow. The email/password form
  posts `username`, `password` and `instalacionId` as form data to
  `/tuloteroweb/rest/userLogin`; through this mirror the request is visible as
  `POST /backend-proxy-es/tuloteroweb/rest/userLogin`. Social login uses the
  same backend through `/google/login`, `/facebook/login` or `/apple/login`.
  It may require valid credentials, acceptance of terms, a captcha or a device
  fingerprint. This harness does not bypass any of those checks.
- Start with `MIRROR_VERBOSE=1` to see the login request and its response status
  without logging the credentials themselves (only method, URL and status are
  printed).
- The app can still contact third-party services (Google, Apple, Facebook,
  analytics, fingerprinting) directly. Those calls are outside this proxy.
- Some production APIs may reject traffic that does not look like a real
  browser. The proxy forwards the browser's `User-Agent`, `Authorization`,
  cookies and request body, but cannot guarantee account-specific flows.
- Only bind to localhost. Do not expose this server on a network: it forwards
  whatever credentials the local browser sends and caches third-party assets.
- The frontend and API are third-party property. Keep the cache untracked and
  use this mirror only for local testing/interoperability within Tulotero's
  terms.
