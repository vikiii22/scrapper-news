import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable, switchMap } from 'rxjs';
import { APP_ENVIRONMENT } from '@core/config/environment.tokens';
import { TranslationsService } from '@core/routing/meta-router.service';

export interface MatchTeam {
  readonly name: string;
  readonly emblem?: string;
  readonly info?: string;
  readonly score?: number;
}

export type MatchResultValues = readonly string[] | readonly (readonly string[])[];

export interface MatchResultInfo {
  readonly score: string;
  readonly values: MatchResultValues;
}

export interface Match {
  readonly id: string | number;
  readonly date: string;
  readonly typeId: 'partidos' | 'pleno15' | 'match';
  readonly local: MatchTeam;
  readonly visitor: MatchTeam;
  readonly resultValues?: MatchResultValues;
}

export interface MatchesPage {
  readonly matches: readonly Match[];
  readonly extraInfo: readonly string[];
}

export interface BackendMatch {
  readonly id: string | number;
  readonly fecha: string;
  readonly local: string;
  readonly visitante: string;
  readonly escudo1?: string;
  readonly escudo2?: string;
  readonly info1?: string;
  readonly info2?: string;
  readonly marcador?: string;
  readonly signo?: string;
  readonly sorteoId?: number;
  readonly error?: boolean;
  readonly externalId?: string;
  readonly suspended?: boolean;
  readonly resultadoAlDescanso?: boolean;
}

export interface BackendMatchesResponse {
  readonly partidos: readonly BackendMatch[];
  readonly extraInfo?: readonly string[];
}

/** Modelo intermedio: el original lo construye antes de `Ns.createFromBackend`. */
interface AdaptedMatchTeam {
  readonly name: string;
  readonly pictureUrl?: string;
  readonly info?: string;
  readonly score?: number;
}

interface AdaptedMatch {
  readonly id: string | number;
  readonly date: string;
  readonly typeId: Match['typeId'];
  readonly local: AdaptedMatchTeam;
  readonly visitor: AdaptedMatchTeam;
  resultInfo?: MatchResultInfo;
}

const QUINIGOL_MATCH_COUNT = 6;
const PARTIDOS_MATCH_COUNT = 14;

@Injectable()
export class MatchesService {
  private readonly http = inject(HttpClient);
  private readonly translations = inject(TranslationsService);
  private readonly environment = inject(APP_ENVIRONMENT);

  getMatches(raffleId: string | number, imageSize = 20): Observable<MatchesPage> {
    const url = `${this.environment.endpoint}/sorteos/${raffleId}/partidos?imgSize=${imageSize}`;

    return this.http.get<BackendMatchesResponse>(url).pipe(
      switchMap((response) =>
        this.translations
          .getTranslation('results.matchSuspended')
          .pipe(map((suspendedNotice) => ({ response, suspendedNotice }))),
      ),
      map(({ response, suspendedNotice }) => {
        const adapted =
          response.partidos.length === QUINIGOL_MATCH_COUNT
            ? this.adaptQuinigolMatches(response).matches
            : this.adaptMatches(response).matches;

        return {
          matches: adapted.map((match) => this.createFromBackend(match)),
          extraInfo: this.adaptExtraInfo(response, suspendedNotice),
        };
      }),
    );
  }

  private adaptMatches(response: BackendMatchesResponse): { matches: AdaptedMatch[] } {
    return {
      matches: response.partidos.map((match, index) => {
        const typeId: Match['typeId'] = index < PARTIDOS_MATCH_COUNT ? 'partidos' : 'pleno15';
        const adapted: AdaptedMatch = {
          id: match.id,
          date: match.fecha,
          typeId,
          local: {
            name: match.local.concat(match.suspended ? '*' : ''),
            pictureUrl: match.escudo1,
            info: match.info1,
            score: this.parseScore(match.marcador, 0),
          },
          visitor: {
            name: match.visitante.concat(match.suspended ? '*' : ''),
            pictureUrl: match.escudo2,
            info: match.info2,
            score: this.parseScore(match.marcador, 1),
          },
        };

        if (match.marcador) {
          if (!match.signo && match.suspended) {
            adapted.resultInfo = {
              score: match.marcador,
              values: this.defaultResultValues(typeId),
            };
          } else {
            adapted.resultInfo = {
              score: match.marcador,
              values: match.signo
                ? typeId === 'pleno15'
                  ? match.signo.split('-').map((value) => [value])
                  : match.signo.split('-')
                : [],
            };
          }
        } else if (!match.signo && match.suspended) {
          adapted.resultInfo = {
            score: match.marcador as string,
            values: this.defaultResultValues(typeId),
          };
        }

        return adapted;
      }),
    };
  }

  private adaptQuinigolMatches(response: BackendMatchesResponse): { matches: AdaptedMatch[] } {
    return {
      matches: response.partidos.map((match) => ({
        id: match.id,
        date: match.fecha,
        typeId: 'match',
        local: {
          name: match.local.concat(match.suspended ? '*' : ''),
          pictureUrl: match.escudo1,
          info: match.info1,
          score: this.parseScore(match.marcador, 0),
        },
        visitor: {
          name: match.visitante.concat(match.suspended ? '*' : ''),
          pictureUrl: match.escudo2,
          info: match.info2,
          score: this.parseScore(match.marcador, 1),
        },
      })),
    };
  }

  /** Equivale a `Ns.createFromBackend` del chunk original. */
  private createFromBackend(match: AdaptedMatch): Match {
    return {
      id: match.id,
      local: this.createTeam(match.local),
      visitor: this.createTeam(match.visitor),
      date: match.date,
      typeId: match.typeId,
      resultValues: match.resultInfo?.values,
    };
  }

  /** Equivale a `Ma.createFromBackend`: `pictureUrl` pasa a llamarse `emblem`. */
  private createTeam(team: AdaptedMatchTeam): MatchTeam {
    return {
      name: team.name,
      emblem: team.pictureUrl,
      info: team.info,
      score: team.score,
    };
  }

  private defaultResultValues(typeId: Match['typeId']): MatchResultValues {
    return typeId === 'partidos'
      ? ['1', 'X', '2']
      : [
          ['0', '1', '2', 'M'],
          ['0', '1', '2', 'M'],
        ];
  }

  private parseScore(score: string | undefined, index: number): number | undefined {
    if (typeof score !== 'string') {
      return undefined;
    }

    const parsed = parseInt(score.split('-')[index], 10);
    return Number.isNaN(parsed) ? undefined : parsed;
  }

  private adaptExtraInfo(response: BackendMatchesResponse, suspendedNotice: string): string[] {
    const extraInfo: string[] = [...(response.extraInfo ?? [])];

    if (response.partidos.some((match) => match.suspended)) {
      extraInfo.push(suspendedNotice);
    }

    return extraInfo;
  }
}
