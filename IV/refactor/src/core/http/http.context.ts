import { HttpContextToken } from '@angular/common/http';

/** Skips every token related interceptor (original `yr`). */
export const SKIP_AUTH = new HttpContextToken<boolean>(() => false);

/** Forces the browser language instead of the application locale (original `Ca`). */
export const USE_BROWSER_LANGUAGE = new HttpContextToken<boolean>(() => false);

/** Sends `Accept-Language: *` (original `Pa`). */
export const ACCEPT_ANY_LANGUAGE = new HttpContextToken<boolean>(() => false);

/** Prevents the maintenance redirect on 503 responses (original `Na`). */
export const SKIP_MAINTENANCE_REDIRECT = new HttpContextToken<boolean>(() => false);
