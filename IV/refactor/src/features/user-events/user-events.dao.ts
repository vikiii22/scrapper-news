import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { APP_ENVIRONMENT } from '@core/config/environment.tokens';
import { UserEventsDao, UserEventsResponse } from './user-events.service';

@Injectable({ providedIn: 'root' })
export class HttpUserEventsDao implements UserEventsDao {
  private readonly http = inject(HttpClient);
  private readonly environment = inject(APP_ENVIRONMENT);

  getUserEventsAndDelete(): Observable<UserEventsResponse> {
    return this.http.delete<UserEventsResponse>(
      `${this.environment.endpoint}/users/events/fetching`,
    );
  }
}
