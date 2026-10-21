import '@angular/compiler';
import { HttpClient } from '@angular/common/http';
import { createEnvironmentInjector, EnvironmentInjector, Injector } from '@angular/core';
import { firstValueFrom, from, of } from 'rxjs';
import { APP_ENVIRONMENT, Environment } from '../src/core/config/environment.tokens';
import { TranslationsService } from '../src/core/routing/meta-router.service';
import { MatchesService } from '../src/features/matches/matches.service';

const endpoint = 'https://web-backend.es.tulotero.net/tuloteroweb/rest';
const raffleId = Number(process.argv[2] ?? 11357);

const http = {
  get: (url: string) =>
    from(
      fetch(url).then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status} for ${url}`);
        return response.json();
      }),
    ),
};

const environment = { endpoint } as Environment;
const parent = Injector.NULL as unknown as EnvironmentInjector;

const injector = createEnvironmentInjector(
  [
    MatchesService,
    { provide: HttpClient, useValue: http },
    { provide: APP_ENVIRONMENT, useValue: environment },
    {
      provide: TranslationsService,
      useValue: { getTranslation: () => of('Partido suspendido') },
    },
  ],
  parent,
);

const service = injector.get(MatchesService);
const page = await firstValueFrom(service.getMatches(raffleId));

console.log(
  JSON.stringify(
    {
      endpoint,
      raffleId,
      count: page.matches.length,
      types: [...new Set(page.matches.map((match) => match.typeId))],
      first: page.matches[0],
      extraInfo: page.extraInfo,
    },
    null,
    2,
  ),
);

const teamsOk = page.matches.every(
  (match) =>
    match.id !== undefined &&
    typeof match.local.name === 'string' &&
    typeof match.visitor.name === 'string' &&
    typeof match.local.emblem === 'string' &&
    typeof match.visitor.emblem === 'string' &&
    Number.isFinite(Number(match.date)),
);
const resultsOk = page.matches.every(
  (match) => match.resultValues === undefined || Array.isArray(match.resultValues),
);

console.log('HAS_RESULTS', page.matches.some((match) => match.resultValues !== undefined));
console.log('LIVE_SHAPE_OK', teamsOk && resultsOk && page.matches.length > 0);
