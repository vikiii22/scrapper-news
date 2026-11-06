/**
 * Genera `openapi.json` para la API web de Tulotero.
 *
 * Uso: node IV/api-spec/build-openapi.mjs
 *
 * El contrato se reconstruyó desde el bundle público de web.tulotero.es y el
 * mirror local de IV/. No es una especificación oficial de Tulotero.
 */
import { writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const OUT = join(dirname(fileURLToPath(import.meta.url)), 'openapi.json');

/* -------------------------------------------------------------------------- */
/* Helpers                                                                     */
/* -------------------------------------------------------------------------- */

const ref = (name) => ({ $ref: `#/components/schemas/${name}` });

const json = (schema, description = 'Respuesta correcta') => ({
  description,
  content: { 'application/json': { schema } },
});

const ok = (name, description) => json(ref(name), description);
const free = (description = 'Respuesta correcta') =>
  json({ type: 'object', additionalProperties: true }, description);
const noContent = { description: 'Operación completada sin cuerpo' };
const text = (description = 'Respuesta en texto plano') => ({
  description,
  content: { 'text/plain': { schema: { type: 'string' } } },
});
const binary = (description = 'Documento binario') => ({
  description,
  content: {
    'application/pdf': { schema: { type: 'string', format: 'binary' } },
    'application/octet-stream': { schema: { type: 'string', format: 'binary' } },
  },
});

const errors = {
  400: { $ref: '#/components/responses/BadRequest' },
  401: { $ref: '#/components/responses/Unauthorized' },
  403: { $ref: '#/components/responses/Forbidden' },
  404: { $ref: '#/components/responses/NotFound' },
  426: { $ref: '#/components/responses/VerificationRequired' },
  500: { $ref: '#/components/responses/ServerError' },
};

const pathParam = (name, description, example) => ({
  name,
  in: 'path',
  required: true,
  description,
  schema: { type: 'string' },
  ...(example !== undefined ? { example } : {}),
});

const queryParam = (name, description, schema = { type: 'string' }, required = false) => ({
  name,
  in: 'query',
  required,
  description,
  schema,
});

const body = (schema, contentType = 'application/json', description = 'Cuerpo de la petición') => ({
  required: true,
  description,
  content: { [contentType]: { schema } },
});

const formBody = (schema, description) =>
  body(schema, 'application/x-www-form-urlencoded', description);

const multipartBody = (schema, description) =>
  body(schema, 'multipart/form-data', description);

const headerRef = (name) => ({ $ref: `#/components/parameters/${name}` });

const commonQuery = [
  queryParam('region', 'Región para contenidos localizados (noticias).'),
];

let operationCounter = 0;
const paths = {};
const usedOperationIds = new Set();

/**
 * Registra una operación.
 * @param {string} method
 * @param {string} path
 * @param {string} tag
 * @param {string} summary
 * @param {object} o
 */
function endpoint(method, path, tag, summary, o = {}) {
  const operationId =
    o.id ??
    `${method}${path}`
      .replace(/[^a-zA-Z0-9]+(.)?/g, (_, c) => (c ? c.toUpperCase() : ''))
      .replace(/^./, (c) => c.toLowerCase());
  if (usedOperationIds.has(operationId)) {
    throw new Error(`operationId duplicado: ${operationId}`);
  }
  usedOperationIds.add(operationId);
  operationCounter += 1;

  const parameters = [...(o.params ?? [])];
  if (o.query?.length) parameters.push(...o.query);
  if (o.commonQuery) parameters.push(...commonQuery);

  const op = {
    tags: [tag],
    summary,
    operationId,
    ...(o.desc ? { description: o.desc } : {}),
    ...(parameters.length ? { parameters } : {}),
    ...(o.body ? { requestBody: o.body } : {}),
    responses: {
      ...(o.responses ?? { 200: o.response ?? free() }),
      ...(o.errors === false ? {} : errors),
    },
    security: o.public ? [] : [{ bearerAuth: [] }],
    ...(o.deprecated ? { deprecated: true } : {}),
  };

  paths[path] ??= {};
  if (paths[path][method]) {
    throw new Error(`Operación duplicada: ${method.toUpperCase()} ${path}`);
  }
  paths[path][method] = op;
}

const get = (path, tag, summary, o) => endpoint('get', path, tag, summary, o);
const post = (path, tag, summary, o) => endpoint('post', path, tag, summary, o);
const put = (path, tag, summary, o) => endpoint('put', path, tag, summary, o);
const del = (path, tag, summary, o) => endpoint('delete', path, tag, summary, o);

/* -------------------------------------------------------------------------- */
/* Esquemas                                                                    */
/* -------------------------------------------------------------------------- */

const S = {};

S.ApiError = {
  type: 'object',
  description: 'Cuerpo de error del backend.',
  properties: {
    status: { type: 'string', example: 'MAIL_EXISTS' },
    message: { type: 'string' },
    code: { type: 'string' },
    info: { type: 'string' },
    object: {},
  },
  additionalProperties: true,
};

S.MessageResponse = {
  type: 'object',
  properties: {
    status: { type: 'string', example: 'OK' },
    message: { type: 'string' },
    object: {},
  },
  additionalProperties: true,
};

S.ResultAvailability = {
  type: 'object',
  properties: { result: { type: 'boolean' } },
};

S.LoginResponse = {
  type: 'object',
  required: ['token', 'refreshToken', 'refreshTokenUrl'],
  properties: {
    token: { type: 'string', description: 'JWT de acceso; caduca según `exp`.' },
    refreshToken: { type: 'string' },
    refreshTokenUrl: {
      type: 'string',
      format: 'uri',
      description: 'URL absoluta usada para refrescar; puede variar por país o entorno.',
    },
    refreshTokenExpirationDate: { type: 'integer', format: 'int64' },
    registered: { type: 'string', description: '“true” si el alta social acaba de registrarse.' },
    jwtLogin: { type: 'boolean' },
  },
  additionalProperties: true,
};

S.LoginRequest = {
  type: 'object',
  required: ['username', 'password', 'instalacionId'],
  properties: {
    username: { type: 'string', description: 'Email del usuario.' },
    password: { type: 'string', format: 'password' },
    instalacionId: { type: 'integer', format: 'int64' },
  },
};

S.RefreshTokenRequest = {
  type: 'object',
  required: ['refreshToken', 'clientTimestamp'],
  properties: {
    refreshToken: { type: 'string' },
    clientTimestamp: { type: 'string', description: 'Millis del cliente como texto.' },
  },
};

S.RefreshTokenResponse = {
  type: 'object',
  required: ['refreshToken'],
  properties: {
    token: { type: 'string' },
    accessToken: {
      oneOf: [{ type: 'string' }, { type: 'object', properties: { token: { type: 'string' } } }],
    },
    refreshToken: { type: 'string' },
    refreshTokenExpirationDate: { type: 'integer', format: 'int64' },
  },
  additionalProperties: true,
};

S.SocialLoginRequest = {
  type: 'object',
  required: ['token', 'deviceType', 'registerDeviceId', 'instalacionId'],
  properties: {
    token: { type: 'string', description: 'Token del proveedor social.' },
    deviceType: { type: 'string', enum: ['WEB'] },
    registerDeviceId: { type: 'string' },
    instalacionId: { type: 'integer', format: 'int64' },
    grantedPermissions: { type: 'string', example: 'email,public_profile' },
    userName: { type: 'string', description: 'Solo Apple.' },
  },
};

S.RegisterRequest = {
  type: 'object',
  required: ['name', 'mail', 'password', 'deviceType', 'registerDeviceId', 'instalationId'],
  properties: {
    name: { type: 'string', maxLength: 255 },
    mail: { type: 'string', format: 'email' },
    password: { type: 'string', format: 'password' },
    promoCode: { type: 'string' },
    deviceType: { type: 'string', enum: ['WEB'] },
    registerDeviceId: { type: 'string' },
    instalationId: {
      type: 'integer',
      format: 'int64',
      description: 'El frontend usa la grafía `instalationId` (una sola “l”).',
    },
  },
};

S.InstallationRequest = {
  type: 'object',
  required: ['jsonInfo', 'tipo'],
  properties: {
    jsonInfo: {
      type: 'string',
      description: 'JSON serializado con `af_status`, `media_source` y `campaign`.',
      example: '{"af_status":"Organic","media_source":"","campaign":""}',
    },
    tipo: { type: 'string', enum: ['WEB'] },
  },
};

S.InstallationResponse = {
  type: 'object',
  properties: { id: { type: 'integer', format: 'int64' } },
  additionalProperties: true,
};

S.UserExtra = {
  type: 'object',
  properties: {
    residente: { type: 'boolean' },
    comunitario: { type: 'boolean' },
    pasaporte: { type: 'boolean' },
    middleName: { type: 'string' },
    suffixName: { type: 'string' },
    userStateCode: { type: 'string' },
    locale: { type: 'string' },
    documentType: { type: 'string' },
    documentNumber: { type: 'string' },
    documentExpirationDate: { type: 'string' },
    documentIssuingEntity: { type: 'string' },
    cifType: { type: 'string' },
    enableTicketBulkActions: { type: 'boolean' },
    insuranceAvailable: { type: 'boolean' },
    jwtLogin: { type: 'boolean' },
  },
  additionalProperties: true,
};

S.UpdateProfileRequest = {
  type: 'object',
  description: 'Nombres de campo exactos del backend.',
  properties: {
    id: { type: 'integer', format: 'int64' },
    codigo: { type: 'string' },
    nombre: { type: 'string' },
    apellidos: { type: 'string' },
    iniciales: { type: 'string' },
    fechaNacimientoString: { type: 'string' },
    newPassword: { type: 'string', format: 'password' },
    direccion: { type: 'string' },
    cp: { type: 'string' },
    poblacion: { type: 'string' },
    provincia: { type: 'string' },
    pais: { type: 'string' },
    telefono: { type: 'string' },
    cif: { type: 'string' },
    saldo: { type: 'number' },
    pictureUrl: { type: 'string' },
    cuentaBancaria: { type: 'string' },
    administracion: { type: 'string' },
    emailVerificado: { type: 'boolean' },
    telefonoVerificado: { type: 'boolean' },
    creditCardAlias: { type: 'string' },
    creditCardExpiryDate: { type: 'string' },
    autoCreditMultiple: { type: 'integer' },
    tokenSponsor: { type: 'string' },
    tokenSponsorUrl: { type: 'string' },
    extra: ref('UserExtra'),
    shouldValidateMandatoryFields: { type: 'boolean' },
  },
  additionalProperties: true,
};

S.UserProfile = {
  allOf: [
    ref('UpdateProfileRequest'),
    {
      type: 'object',
      required: ['id', 'codigo'],
      properties: {
        id: { type: 'integer', format: 'int64' },
        codigo: { type: 'string', description: 'Email del usuario.' },
        saldo: { type: 'number' },
        mailVerificado: { type: 'boolean' },
        telefonoVerificado: { type: 'boolean' },
        fechaRegistro: { type: 'integer', format: 'int64' },
        locale: { type: 'string' },
        kyc: ref('KycStatus'),
        shouldCallFetchingEvents: { type: 'boolean' },
      },
    },
  ],
};

S.KycStatus = {
  type: 'object',
  properties: {
    status: { type: 'string' },
    comment: { type: 'string' },
    barcodeUsed: { type: 'string' },
    submitted: { type: 'boolean' },
  },
  additionalProperties: true,
};

S.LocaleResponse = { type: 'object', properties: { locale: { type: 'string', example: 'es-ES' } } };

S.Preference = {
  type: 'object',
  required: ['key', 'value'],
  properties: {
    key: { type: 'string' },
    value: { type: 'string' },
    enabled: { type: 'boolean' },
  },
  additionalProperties: true,
};

S.PreferencesResponse = {
  type: 'object',
  properties: { preferences: { type: 'array', items: ref('Preference') } },
};

S.SavePreferencesRequest = {
  type: 'object',
  required: ['preferences'],
  properties: { preferences: { type: 'array', items: ref('Preference') } },
};

S.UserLimits = {
  type: 'object',
  properties: {
    dailyLimit: { type: 'number' },
    weeklyLimit: { type: 'number' },
    monthlyLimit: { type: 'number' },
    maxLoad: { type: 'number' },
    maxBalance: { type: 'number' },
  },
  additionalProperties: true,
};

S.SelfExclusionConfirmRequest = {
  type: 'object',
  required: ['token'],
  properties: {
    token: { type: 'string' },
    selfExclusionTypeCode: { type: 'string' },
    durationInMonths: { type: 'integer' },
    automaticReactivation: { type: 'boolean' },
  },
  additionalProperties: true,
};

S.AutoControlQuestion = {
  type: 'object',
  required: ['id'],
  properties: {
    id: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
    question: { type: 'string' },
    answers: { type: 'array', items: {} },
  },
  additionalProperties: true,
};

S.AutoControlAnswer = {
  type: 'object',
  required: ['id', 'value'],
  properties: {
    id: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
    value: {},
  },
  additionalProperties: true,
};

S.AgendaContact = {
  type: 'object',
  properties: { name: { type: 'string' }, phoneNumber: { type: 'string' } },
  additionalProperties: true,
};

S.SaveAgendaRequest = {
  type: 'object',
  required: ['contactos', 'deviceId'],
  properties: {
    contactos: { type: 'array', items: { oneOf: [{ type: 'string' }, ref('AgendaContact')] } },
    deviceId: { type: 'string' },
  },
};

S.SponsorInfo = {
  type: 'object',
  properties: {
    token: { type: 'string' },
    url: { type: 'string' },
    amount: { type: 'number' },
    sponsorCode: { type: 'string' },
    sponsorUrl: { type: 'string' },
  },
  additionalProperties: true,
};

S.SendSponsorSmsRequest = {
  type: 'object',
  required: ['contactos', 'deviceId'],
  properties: {
    contactos: { type: 'array', items: { type: 'string' } },
    deviceId: { type: 'string' },
    text: { type: 'string' },
  },
};

S.IdentityVerificationStatus = {
  type: 'object',
  properties: {
    status: { type: 'string' },
    comment: { type: 'string' },
    barcodeUsed: { type: 'string' },
  },
  additionalProperties: true,
};

S.ConfirmIdentityVerificationRequest = {
  type: 'object',
  required: ['code'],
  properties: { code: { type: 'string' } },
  additionalProperties: true,
};

S.ShipmentRequest = {
  type: 'object',
  properties: {
    name: { type: 'string' },
    addressLine: { type: 'string' },
    city: { type: 'string' },
    zipCode: { type: 'string' },
    state: { type: 'string' },
    phone: { type: 'string' },
  },
  additionalProperties: true,
};

S.SuggestionRequest = {
  type: 'object',
  required: ['message', 'versionCode', 'deviceType'],
  properties: {
    message: { type: 'string' },
    versionCode: { oneOf: [{ type: 'integer' }, { type: 'string' }] },
    deviceType: { type: 'string', example: 'WEB' },
    suggestionType: { type: 'string' },
    email: { type: 'string', format: 'email' },
  },
};

/* Sorteos ------------------------------------------------------------------ */

S.CombinationNumber = {
  type: 'object',
  required: ['numero', 'numero2Digits', 'highlighted'],
  properties: {
    numero: { type: 'string' },
    numero2Digits: { type: 'string' },
    highlighted: { type: 'boolean' },
  },
};

S.DrawCombination = {
  type: 'object',
  properties: {
    linea: { type: 'string' },
    juego: { type: 'string' },
    numerosCombinacion: { type: 'array', items: ref('CombinationNumber') },
    estrellas: { type: 'array', items: ref('CombinationNumber') },
    plenoAl15: ref('CombinationNumber'),
  },
  additionalProperties: true,
};

S.DrawPrize = {
  type: 'object',
  properties: {
    category: { type: 'string' },
    amount: { type: 'number' },
    winners: { type: 'integer' },
  },
  additionalProperties: true,
};

S.Draw = {
  type: 'object',
  required: ['id', 'juego', 'fecha'],
  properties: {
    id: { type: 'integer', format: 'int64' },
    externalId: { type: 'string' },
    juego: { type: 'string' },
    juegoVersion: { type: 'integer' },
    fecha: { type: 'integer', format: 'int64' },
    fechaCierre: { type: 'integer', format: 'int64' },
    fechaCierreTope: { type: 'integer', format: 'int64' },
    premios: { type: 'array', items: ref('DrawPrize') },
    precio: { type: 'number' },
    nombre: { type: 'string' },
    numSorteo: { type: 'string' },
    numJornada: { type: 'string' },
    combinacion: { type: 'string' },
    activityStartDate: { type: 'integer', format: 'int64' },
    activityEndDate: { type: 'integer', format: 'int64' },
    locked: { type: 'boolean' },
    lockedAbonos: { type: 'boolean' },
    apuestasCierre: { type: 'integer' },
    allowFijos: { type: 'boolean' },
    solicitudAdelantar: { type: 'boolean' },
    combinacionObject: ref('DrawCombination'),
    resultInfoLines: { type: 'array', items: {} },
    prizeInfos: { type: 'array', items: {} },
    premiosCalculados: { type: 'boolean' },
  },
  additionalProperties: true,
};

S.FinishedDrawsResponse = {
  type: 'object',
  required: ['resultados'],
  properties: {
    resultados: { type: 'array', items: ref('Draw') },
    total: { type: 'integer' },
  },
};

S.Match = {
  type: 'object',
  required: ['id', 'local', 'visitante', 'sorteoId'],
  properties: {
    id: { type: 'integer', format: 'int64' },
    local: { type: 'string' },
    visitante: { type: 'string' },
    fecha: { type: 'integer', format: 'int64' },
    signo: { type: 'string' },
    marcador: { type: 'string' },
    sorteoId: { type: 'integer', format: 'int64' },
    escudo1: { type: 'string' },
    escudo2: { type: 'string' },
    info1: { type: 'string' },
    info2: { type: 'string' },
    error: { type: 'boolean' },
    externalId: { type: 'string' },
    suspended: { type: 'boolean' },
    resultadoAlDescanso: { type: 'boolean' },
  },
};

S.MatchesResponse = {
  type: 'object',
  required: ['partidos'],
  properties: {
    partidos: { type: 'array', items: ref('Match') },
    extraInfo: { type: 'array', items: { type: 'string' } },
  },
};

/* Juego -------------------------------------------------------------------- */

S.PlayTypeValue = {
  type: 'object',
  required: ['type', 'typeId', 'value'],
  properties: {
    type: { type: 'string' },
    typeId: { type: 'string' },
    value: { type: 'array', items: {} },
  },
};

S.PlayBet = {
  type: 'object',
  required: ['amountBet', 'betId', 'types'],
  properties: {
    amountBet: { type: 'number' },
    betId: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
    searchAdminId: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
    subscriptionId: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
    subscriptionDraws: { type: 'array', items: { type: 'object', additionalProperties: true } },
    types: { type: 'array', items: ref('PlayTypeValue') },
    boardId: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
  },
};

S.PlayCombination = {
  type: 'object',
  required: ['aleatoria', 'juego', 'bets'],
  properties: {
    aleatoria: { type: 'boolean' },
    juego: { type: 'string' },
    bets: { type: 'array', items: ref('PlayBet') },
    reintegro: { type: 'object', properties: { numero: { type: 'string' } } },
    complementario: { type: 'object', properties: { numero: { type: 'string' } } },
    apuestas: {
      type: 'array',
      items: {
        type: 'object',
        properties: { numeros: { type: 'array', items: { type: 'object', properties: { numero: { type: 'string' } } } } },
      },
    },
  },
};

S.AbonoDay = {
  type: 'object',
  properties: {
    day: { type: 'string' },
    hour: { type: 'string' },
    alias: { type: 'string', nullable: true },
    aliasToShow: { type: 'string', nullable: true },
  },
};

S.PlayRequest = {
  type: 'object',
  required: ['almanaque', 'abonarse', 'aleatorio', 'juego', 'sorteoIds', 'numApuestas', 'totalApuesta', 'combinacionJugada'],
  properties: {
    almanaque: { type: 'boolean' },
    confirmacion: { type: 'boolean' },
    abonarse: { type: 'boolean' },
    abonoDays: { type: 'array', nullable: true, items: ref('AbonoDay') },
    abonoMinJackpotAmount: { type: 'number' },
    aleatorio: { type: 'boolean' },
    groupIdToSpoof: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
    juego: { type: 'string' },
    quickPlay: { type: 'boolean' },
    sorteoIds: { type: 'array', items: { type: 'integer' } },
    numApuestas: { type: 'integer' },
    totalApuesta: { type: 'number' },
    comparticion: { type: 'object', additionalProperties: true },
    extraInfo: { type: 'object', additionalProperties: true },
    combinacionJugada: ref('PlayCombination'),
    insurance: { type: 'boolean' },
    boothId: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
    envioCasaRequest: ref('ShipmentRequest'),
    recogida: { type: 'boolean' },
  },
};

S.LotteryDecimo = {
  type: 'object',
  required: ['numero', 'cantidad'],
  properties: {
    numero: { type: 'string' },
    adminId: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
    cantidad: { type: 'integer' },
    almanaquePrecio: { type: 'number' },
    reservation: { type: 'boolean' },
    fijoLoteriaId: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
  },
};

S.LotteryPlayRequest = {
  type: 'object',
  required: ['almanaque', 'aleatorio', 'abonarse', 'sorteoId', 'decimos'],
  properties: {
    almanaque: { type: 'boolean' },
    aleatorio: { type: 'boolean' },
    quickPlay: { type: 'boolean' },
    abonarse: { type: 'boolean' },
    abonoDays: { type: 'array', items: ref('AbonoDay') },
    abonoMinJackpotAmount: { type: 'number' },
    groupIdToSpoof: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
    insurance: { type: 'boolean' },
    comparticion: { type: 'object', additionalProperties: true },
    sorteoId: { type: 'integer' },
    decimos: { type: 'array', items: ref('LotteryDecimo') },
    randomLoteria: {
      type: 'object',
      properties: { stock: { type: 'integer' }, adminId: { oneOf: [{ type: 'string' }, { type: 'integer' }] } },
    },
    envioCasaRequest: ref('ShipmentRequest'),
    recogida: { type: 'boolean' },
  },
};

S.PlayResult = {
  type: 'object',
  properties: {
    status: { type: 'string' },
    message: { type: 'string' },
    object: {},
    boleto: {},
    ticket: {},
  },
  additionalProperties: true,
};

S.ScannerCodeRequest = { type: 'object', required: ['code'], properties: { code: { type: 'string' } } };

S.LotterySearchType = {
  type: 'object',
  required: ['typeId', 'value'],
  properties: {
    typeId: { type: 'string' },
    value: { type: 'array', items: { type: 'string' } },
  },
};

S.LotterySearchRequest = {
  type: 'object',
  required: ['sorteoId', 'types'],
  properties: {
    sorteoId: { type: 'integer' },
    types: { type: 'array', items: ref('LotterySearchType') },
    firstResult: { type: 'integer' },
    minAmount: { type: 'integer' },
    maxResults: { type: 'integer' },
    avoidDuplicatedNumbers: { type: 'boolean' },
  },
};

S.LotteryTicket = {
  type: 'object',
  properties: {
    numero: { type: 'string' },
    numero2Digits: { type: 'string' },
    highlighted: { type: 'boolean' },
    adminId: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
    precio: { type: 'number' },
  },
  additionalProperties: true,
};

S.LotterySearchResponse = {
  type: 'object',
  properties: {
    totalDecimosEnSorteo: { type: 'integer' },
    totalNumbers: { type: 'integer' },
    totalStockEnSorteo: { type: 'integer' },
    numbers: { type: 'array', items: ref('LotteryTicket') },
    decimos: { type: 'array', items: ref('LotteryTicket') },
    firstResult: { type: 'integer' },
  },
};

S.LotterySubscriptionInfo = {
  type: 'object',
  properties: {
    abonoDay: ref('AbonoDay'),
    amountManual: { type: 'integer' },
    manual: { type: 'boolean' },
    precio: { type: 'number' },
    sorteos: { type: 'array', items: { type: 'integer' } },
  },
};

/* Boletos ------------------------------------------------------------------ */

S.Ticket = {
  type: 'object',
  required: ['id'],
  properties: {
    id: { type: 'integer', format: 'int64' },
    descNombre: { type: 'string' },
    customName: { type: 'string' },
    hash: { type: 'string' },
    fechaSorteo: { type: 'integer', format: 'int64' },
    fechaPedido: { type: 'integer', format: 'int64' },
    apuestaId: { type: 'integer' },
    fechasSorteo: { type: 'array', items: { type: 'integer', format: 'int64' } },
    fechaArchivado: { type: 'integer', format: 'int64' },
    descPrecio: { type: 'string' },
    precio: { type: 'number' },
    precioOriginal: { type: 'number' },
    precioPagado: { type: 'number' },
    premioProvisional: { type: 'number' },
    premio: { type: 'number' },
    prizeFormatted: { type: 'string' },
    prizeFormattedLong: { type: 'string' },
    imagenMini: { type: 'string' },
    imagenMiniSVG: { type: 'string' },
    imagenType: { type: 'string' },
    imagenTypeSVG: { type: 'string' },
    useDescriptorUI: { type: 'boolean' },
    boletoHtml: { type: 'string' },
    sorteo: ref('Draw'),
    config: { type: 'object', additionalProperties: true },
    proof: { type: 'boolean' },
    groupId: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
    status: { type: 'string' },
    numParticipaciones: { type: 'integer' },
    numParticipantes: { type: 'integer' },
    invalidateWhenSorteoFinished: { type: 'boolean' },
    compartidoPor: { type: 'object', additionalProperties: true },
    comparticiones: { type: 'array', items: { type: 'object', additionalProperties: true } },
    abono: { type: 'object', additionalProperties: true },
    penya: ref('Penya'),
    imagenes: { type: 'array', items: { type: 'string' } },
    apuesta: { type: 'object', additionalProperties: true },
    betInfo: {},
    pendingPrizeAppInfo: { type: 'object', additionalProperties: true },
  },
  additionalProperties: true,
};

S.TicketsPage = {
  type: 'object',
  required: ['boletos'],
  properties: {
    boletos: { type: 'array', items: ref('Ticket') },
    total: { type: 'integer' },
  },
};

S.TicketFiltersResponse = {
  type: 'object',
  properties: {
    filters: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id'],
        properties: { id: { type: 'string' }, label: { type: 'string' } },
        additionalProperties: true,
      },
    },
  },
};

S.EditTicketRequest = {
  type: 'object',
  required: ['idBoleto', 'name'],
  properties: {
    idBoleto: { type: 'integer' },
    name: { type: 'string' },
    almanaquePrecio: { type: 'number' },
  },
};

S.ShareTicketRequest = {
  type: 'object',
  required: ['idBoleto'],
  properties: { idBoleto: { type: 'integer' } },
  additionalProperties: true,
};

S.SubscribeTicketRequest = {
  type: 'object',
  required: ['aleatorio', 'recompartir'],
  properties: {
    aleatorio: { type: 'boolean' },
    recompartir: { type: 'boolean' },
    abonoDays: { type: 'array', items: ref('AbonoDay') },
    abonoMinJackpotAmount: { type: 'number' },
    cantidad: { type: 'integer' },
  },
};

S.RepeatTicketRequest = {
  type: 'object',
  required: ['idBoleto', 'sorteoIds'],
  properties: {
    idBoleto: { type: 'integer' },
    sorteoIds: { type: 'array', items: { type: 'integer' } },
    aleatoria: { type: 'boolean' },
    recompartir: { type: 'boolean' },
  },
};

S.ShipmentPrice = {
  type: 'object',
  properties: { price: { type: 'number' } },
  additionalProperties: true,
};

S.PrizeStatus = {
  type: 'object',
  properties: { status: { type: 'string' } },
  additionalProperties: true,
};

/* Cartera ------------------------------------------------------------------ */

S.MoneyMovement = {
  type: 'object',
  properties: {
    id: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
    type: { type: 'string' },
    amount: { type: 'number' },
    date: { type: 'integer', format: 'int64' },
    description: { type: 'string' },
    status: { type: 'string' },
    balance: { type: 'number' },
  },
  additionalProperties: true,
};

S.MoneyMovementsResponse = {
  type: 'object',
  required: ['movimientos'],
  properties: {
    movimientos: { type: 'array', items: ref('MoneyMovement') },
    total: { type: 'integer' },
  },
};

S.WithdrawRequest = {
  type: 'object',
  required: ['cuenta', 'cantidad', 'persist'],
  properties: {
    cuenta: { type: 'string' },
    cantidad: { type: 'number' },
    persist: { type: 'boolean' },
    useOtp: { type: 'boolean' },
  },
  additionalProperties: true,
};

S.WithdrawV2Request = {
  type: 'object',
  properties: {
    amount: { type: 'number' },
    account: { type: 'string' },
    iban: { type: 'string' },
    saveAccount: { type: 'boolean' },
    useOtp: { type: 'boolean' },
  },
  additionalProperties: true,
};

S.CreditCardRequest = {
  type: 'object',
  required: ['amount'],
  properties: {
    amount: { type: 'number' },
    saveCardAlias: { type: 'string' },
    paymentMethodId: { type: 'string' },
    token: { type: 'string' },
    security: { type: 'string' },
    favorite: { type: 'boolean' },
  },
};

S.ExternalCreditRequest = {
  type: 'object',
  required: ['paymentMethod', 'amount'],
  properties: {
    paymentMethod: { type: 'string', example: 'BANK_TRANSFER_REDIRECT' },
    amount: { type: 'number' },
    redirectUrlAfter: { type: 'string', format: 'uri' },
    phoneNumber: { type: 'string' },
    extraData: {
      type: 'object',
      properties: {
        bankCode: { type: 'string' },
        documentType: { type: 'string' },
        documentNumber: { type: 'string' },
      },
      additionalProperties: true,
    },
  },
};

S.AutoCreditRequest = {
  type: 'object',
  required: ['autoCreditMultiple'],
  properties: { autoCreditMultiple: { type: 'integer' } },
};

S.PaymentMethod = {
  type: 'object',
  required: ['id'],
  properties: {
    id: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
    type: { type: 'string' },
    alias: { type: 'string' },
    favorite: { type: 'boolean' },
  },
  additionalProperties: true,
};

S.PaymentMethodLoadRequest = { type: 'object', additionalProperties: true };

/* Grupos ------------------------------------------------------------------- */

S.GroupMember = {
  type: 'object',
  properties: {
    id: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
    name: { type: 'string' },
    picture: { type: 'string' },
    role: { type: 'string' },
  },
  additionalProperties: true,
};

S.Group = {
  type: 'object',
  required: ['id'],
  properties: {
    id: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
    name: { type: 'string' },
    code: { type: 'string' },
    picture: { type: 'string' },
    balance: { type: 'number' },
    role: { type: 'string' },
    members: { type: 'array', items: ref('GroupMember') },
  },
  additionalProperties: true,
};

S.GroupCreateRequest = {
  type: 'object',
  required: ['name'],
  properties: { name: { type: 'string' } },
  additionalProperties: true,
};

S.GroupUpdateRequest = { type: 'object', additionalProperties: true };

S.GroupMoneyRequest = {
  type: 'object',
  required: ['amount'],
  properties: {
    amount: { type: 'number' },
    userIds: { type: 'array', items: { oneOf: [{ type: 'string' }, { type: 'integer' }] } },
  },
};

S.GroupMemberInvite = {
  type: 'object',
  properties: {
    userIds: { type: 'array', items: { oneOf: [{ type: 'string' }, { type: 'integer' }] } },
  },
  additionalProperties: true,
};

S.GroupMessageRequest = {
  type: 'object',
  required: ['message'],
  properties: { message: { type: 'string' } },
  additionalProperties: true,
};

S.GroupMoneyActivity = {
  type: 'object',
  properties: {
    id: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
    type: { type: 'string' },
    amount: { type: 'number' },
    date: { type: 'integer', format: 'int64' },
  },
  additionalProperties: true,
};

/* Clubes / peñas ------------------------------------------------------------ */

S.Penya = {
  type: 'object',
  required: ['id'],
  properties: {
    id: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
    name: { type: 'string' },
    code: { type: 'string' },
    image: { type: 'string' },
    raffleId: { type: 'integer' },
    gameId: { type: 'string' },
    entryMin: { type: 'integer' },
    entryPrice: { type: 'number' },
    type: { type: 'string' },
  },
  additionalProperties: true,
};

S.PenyaList = {
  type: 'object',
  required: ['penyas'],
  properties: { penyas: { type: 'array', items: ref('Penya') } },
};

S.ClubPlayRequest = {
  type: 'object',
  required: ['participaciones'],
  properties: {
    participaciones: {
      type: 'array',
      items: {
        type: 'object',
        required: ['juego', 'abonarse', 'penyaId'],
        properties: {
          juego: { type: 'string' },
          abonarse: { type: 'boolean' },
          penyaId: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
          groupIdToSpoof: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
          numParticipaciones: { type: 'integer' },
        },
      },
    },
  },
};

S.JoinPrivateClubRequest = {
  type: 'object',
  required: ['promo'],
  properties: { promo: { type: 'string' } },
};

S.CompanyClubRequest = { type: 'object', additionalProperties: true };

/* Plataforma / noticias ----------------------------------------------------- */

S.EndpointConfig = {
  type: 'object',
  required: ['id'],
  properties: {
    id: { type: 'string' },
    name: { type: 'string' },
    minHourWithdrawal: { type: 'string' },
    maxHourWithdrawal: { type: 'string' },
    serverLocale: { type: 'string' },
    supportedLocales: { type: 'array', items: { type: 'string' } },
    serverTimeZone: { type: 'string' },
    currencySymbol: { type: 'string' },
    metricUnit: { type: 'string' },
    twitter: { type: 'string' },
    facebook: { type: 'string' },
    instagram: { type: 'string' },
    landingUrl: { type: 'string' },
    terms: { type: 'string' },
    responsibleGame: { type: 'string' },
    selfExclusionUrlInfo: { type: 'string' },
    penyas: { type: 'boolean' },
    groups: { type: 'boolean' },
    administrations: { type: 'boolean' },
    nif: { type: 'boolean' },
    transferOptions: { type: 'object', additionalProperties: true },
    adminsUrl: { type: 'string' },
  },
  additionalProperties: true,
};

S.AllInfoResponse = {
  type: 'object',
  required: ['endpoint'],
  properties: {
    endpoint: ref('EndpointConfig'),
    administraciones: { type: 'array', items: { type: 'object', additionalProperties: true } },
    states: { type: 'array', items: { type: 'object', additionalProperties: true } },
    booths: { type: 'array', items: { type: 'object', additionalProperties: true } },
  },
  additionalProperties: true,
};

S.FacebookLoginInfo = {
  type: 'object',
  properties: {
    appId: { type: 'string' },
    permissions: { type: 'string' },
    disabledMessage: { type: 'string' },
  },
};

S.NewsBackend = {
  type: 'object',
  required: ['id', 'title'],
  properties: {
    id: { oneOf: [{ type: 'string' }, { type: 'integer' }] },
    title: { type: 'string' },
    content: { type: 'string' },
    comments: { type: 'integer' },
    views: { type: 'integer' },
    date: { type: 'integer', format: 'int64' },
    mainImg: { type: 'string' },
    img: { type: 'string' },
    urlVideo: { type: 'string' },
    url: { type: 'string' },
    layout: { type: 'string' },
    category: { type: 'string' },
    videoVertical: { type: 'boolean' },
  },
  additionalProperties: true,
};

S.NewsResponse = {
  type: 'object',
  required: ['news'],
  properties: {
    news: { type: 'array', items: ref('NewsBackend') },
    total: { type: 'integer' },
    totalUnread: { type: 'integer' },
  },
};

S.KycScannerParseRequest = { type: 'object', additionalProperties: true };
S.KycScannerParseResponse = {
  type: 'object',
  properties: { message: { type: 'string' }, object: {} },
  additionalProperties: true,
};

/* -------------------------------------------------------------------------- */
/* Operaciones                                                                 */
/* -------------------------------------------------------------------------- */

const deviceHeaders = () => [
  headerRef('AcceptLanguage'),
  headerRef('NgTime'),
  headerRef('AvoidRedirect'),
  headerRef('Client'),
  headerRef('DeviceId'),
  headerRef('DeviceType'),
  headerRef('DeviceDesc'),
  headerRef('OsVersion'),
  headerRef('VersionCode'),
  headerRef('Mode'),
  headerRef('AndroidRegistrationId'),
];

/* Autenticación y sesión */
post('/userLogin', 'Authentication', 'Iniciar sesión con email y contraseña', {
  public: true,
  desc: 'Formulario `application/x-www-form-urlencoded`. Devuelve JWT, refresh token y la URL de refresco.',
  params: deviceHeaders(),
  body: formBody(ref('LoginRequest'), 'Credenciales y `instalacionId`.'),
  response: ok('LoginResponse'),
  responses: {
    200: ok('LoginResponse'),
    400: { $ref: '#/components/responses/BadRequest' },
    401: { $ref: '#/components/responses/Unauthorized' },
    403: { $ref: '#/components/responses/Forbidden' },
  },
});

post('/facebook/login', 'Authentication', 'Login con Facebook', {
  public: true,
  desc: 'Enviado como formulario. El backend aplica las mismas cabeceras de dispositivo que `/userLogin`.',
  params: deviceHeaders(),
  body: formBody(ref('SocialLoginRequest'), 'Token social y datos del dispositivo.'),
  responses: { 200: ok('LoginResponse') },
});

post('/google/login', 'Authentication', 'Login con Google', {
  public: true,
  params: deviceHeaders(),
  body: formBody(ref('SocialLoginRequest'), 'Token social y datos del dispositivo.'),
  responses: { 200: ok('LoginResponse') },
});

post('/apple/login', 'Authentication', 'Login con Apple', {
  public: true,
  desc: 'Incluye `userName` opcional. `grantedPermissions` por defecto: `full_name, email`.',
  params: deviceHeaders(),
  body: formBody(ref('SocialLoginRequest'), 'Token social y datos del dispositivo.'),
  responses: { 200: ok('LoginResponse') },
});

post('/registration', 'Authentication', 'Registrar una cuenta nueva', {
  public: true,
  desc: 'El frontend envía `registration?disableGlobalMessages=false`. Tras el alta se hace login automático.',
  params: [...deviceHeaders(), queryParam('disableGlobalMessages', 'Suprime mensajes globales durante el alta.', { type: 'boolean' }, false)],
  body: body(ref('RegisterRequest'), 'application/json', 'Datos del alta.'),
  response: ok('MessageResponse'),
  responses: {
    200: ok('MessageResponse'),
    400: { $ref: '#/components/responses/BadRequest' },
  },
});

get('/beginForgotPassword/', 'Authentication', 'Iniciar recuperación de contraseña', {
  public: true,
  query: [queryParam('mail', 'Email de la cuenta.', { type: 'string', format: 'email' }, true)],
  response: ok('MessageResponse'),
  responses: {
    200: ok('MessageResponse'),
    404: { $ref: '#/components/responses/NotFound' },
  },
});

post('/refreshToken', 'Authentication', 'Refrescar el access token', {
  public: true,
  desc: 'La URL real llega en `refreshTokenUrl` al hacer login y puede apuntar a otro host o ruta. Aquí se documenta la forma habitual y el cuerpo exacto.',
  body: formBody(ref('RefreshTokenRequest'), '`refreshToken` y `clientTimestamp`.'),
  response: ok('RefreshTokenResponse'),
  responses: {
    200: ok('RefreshTokenResponse'),
    401: { $ref: '#/components/responses/Unauthorized' },
    403: { $ref: '#/components/responses/Forbidden' },
  },
});

post('/installation', 'Authentication', 'Registrar la instalación web', {
  public: true,
  desc: 'Devuelve el `instalacionId` que se usa en login, alta y login social.',
  body: body(ref('InstallationRequest'), 'application/json', 'Metadatos de atribución.'),
  response: ok('InstallationResponse'),
  responses: { 200: ok('InstallationResponse') },
});

put('/device/{registrationId}/locale', 'Authentication', 'Actualizar el idioma del dispositivo', {
  params: [pathParam('registrationId', 'Identificador de registro del dispositivo.')],
  body: body({ type: 'object', required: ['locale'], properties: { locale: { type: 'string' } } }),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

post('/users/unregister', 'Authentication', 'Desregistrar el dispositivo', {
  body: formBody(
    { type: 'object', required: ['registrationId'], properties: { registrationId: { type: 'string' } } },
    'Identificador de registro a eliminar.',
  ),
  response: text(),
  responses: { 200: text() },
});

/* Usuario */
get('/users/me', 'Users', 'Obtener el perfil del usuario autenticado', {
  response: ok('UserProfile'),
  responses: { 200: ok('UserProfile') },
});

put('/users/me', 'Users', 'Actualizar el perfil', {
  body: body(ref('UpdateProfileRequest')),
  response: ok('UserProfile'),
  responses: { 200: ok('UserProfile'), 400: { $ref: '#/components/responses/BadRequest' } },
});

del('/users/me', 'Users', 'Eliminar la cuenta', {
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

get('/users/verificarMail', 'Users', 'Reenviar el email de verificación', {
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

put('/users/mail', 'Users', 'Cambiar el email', {
  body: body({
    type: 'object',
    required: ['mail'],
    properties: { mail: { type: 'string', format: 'email' } },
  }),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

get('/users/locale', 'Users', 'Obtener el idioma del usuario', {
  response: ok('LocaleResponse'),
  responses: { 200: ok('LocaleResponse') },
});

put('/users/locale', 'Users', 'Cambiar el idioma del usuario', {
  body: body({
    type: 'object',
    required: ['locale'],
    properties: { locale: { type: 'string', example: 'es-ES' } },
  }),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

post('/users/inicioVerificarNumero', 'Users', 'Iniciar la verificación de teléfono', {
  desc: 'Formulario con el número de teléfono.',
  body: formBody(
    { type: 'object', required: ['numero'], properties: { numero: { type: 'string' } } },
    'Número a verificar.',
  ),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

post('/users/verifyPhoneNumber', 'Users', 'Confirmar el código de teléfono', {
  query: [queryParam('disableGlobalMessages', 'Suprime mensajes globales.', { type: 'boolean' })],
  body: formBody(
    {
      type: 'object',
      required: ['numero', 'token'],
      properties: { numero: { type: 'string' }, token: { type: 'string' } },
    },
    'Número y código recibido.',
  ),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

get('/shouldShowPrivacyModalOnRegister/{email}', 'Users', 'Comprobar si el email ya está registrado', {
  public: true,
  desc: 'Devuelve `result: false` cuando el email ya existe (el frontend lo interpreta como “registrado”).',
  params: [pathParam('email', 'Email a comprobar.', 'user@example.com')],
  response: ok('ResultAvailability'),
  responses: { 200: ok('ResultAvailability') },
});

put('/users/extras/add', 'Users', 'Añadir un campo extra al perfil', {
  body: body({
    type: 'object',
    required: ['name', 'value'],
    properties: { name: { type: 'string' }, value: { type: 'string' } },
  }),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

put('/users/extras/replace', 'Users', 'Reemplazar los campos extra del perfil', {
  body: body({
    type: 'object',
    required: ['extras'],
    properties: { extras: { type: 'object', additionalProperties: { type: 'string' } } },
  }),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

get('/users/preferences', 'Users', 'Obtener las preferencias', {
  response: ok('PreferencesResponse'),
  responses: { 200: ok('PreferencesResponse') },
});

put('/users/preferences', 'Users', 'Guardar las preferencias', {
  body: body(ref('SavePreferencesRequest')),
  response: ok('PreferencesResponse'),
  responses: { 200: ok('PreferencesResponse') },
});

get('/users/limits', 'Users', 'Obtener los límites de juego', {
  response: ok('UserLimits'),
  responses: { 200: ok('UserLimits') },
});

put('/users/limits', 'Users', 'Guardar los límites de juego', {
  body: body(ref('UserLimits')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

post('/users/selfexclusion/generatetoken', 'Users', 'Solicitar token de autoexclusión', {
  query: [queryParam('selfexclusiontypecode', 'Tipo de autoexclusión.', { type: 'string' }, true)],
  body: body({ type: 'object', additionalProperties: true }),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

put('/users/selfexclusion/confirm', 'Users', 'Confirmar la autoexclusión', {
  body: body(ref('SelfExclusionConfirmRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

get('/users/autocontroltest/questions', 'Users', 'Obtener el test de autocontrol', {
  response: json({
    type: 'object',
    properties: { object: { type: 'array', items: ref('AutoControlQuestion') } },
  }),
  responses: { 200: json({ type: 'object', properties: { object: { type: 'array', items: ref('AutoControlQuestion') } } }) },
});

post('/users/autocontroltest/testResult', 'Users', 'Enviar el resultado del test de autocontrol', {
  body: body({ type: 'array', items: ref('AutoControlAnswer') }),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

get('/users/autocontroltest/nextAttemptTimestamp', 'Users', 'Obtener la fecha del próximo test', {
  response: json({ type: 'object', properties: { object: { type: 'integer', format: 'int64' } } }),
  responses: { 200: json({ type: 'object', properties: { object: { type: 'integer', format: 'int64' } } }) },
});

get('/users/agenda', 'Users', 'Obtener la agenda de contactos', {
  response: json({
    type: 'object',
    properties: {
      agenda: { type: 'array', items: ref('AgendaContact') },
      relations: { type: 'array', items: ref('AgendaContact') },
    },
  }),
  responses: {
    200: json({
      type: 'object',
      properties: {
        agenda: { type: 'array', items: ref('AgendaContact') },
        relations: { type: 'array', items: ref('AgendaContact') },
      },
    }),
  },
});

post('/users/agenda', 'Users', 'Guardar la agenda de contactos', {
  body: body(ref('SaveAgendaRequest')),
  response: free(),
  responses: { 200: free() },
});

get('/users/sponsor', 'Users', 'Obtener la información de patrocinio', {
  response: ok('SponsorInfo'),
  responses: { 200: ok('SponsorInfo') },
});

post('/users/sponsor/sms', 'Users', 'Enviar invitaciones de patrocinio por SMS', {
  body: body(ref('SendSponsorSmsRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

get('/users/identity-verification', 'Users', 'Consultar el estado de verificación de identidad', {
  response: ok('IdentityVerificationStatus'),
  responses: { 200: ok('IdentityVerificationStatus') },
});

post('/users/identity-verification', 'Users', 'Confirmar el código de verificación de identidad', {
  body: body(ref('ConfirmIdentityVerificationRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

get('/users/identity-verification/resend-sms', 'Users', 'Reenviar el SMS de verificación de identidad', {
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

get('/users/lastEnvioAddress', 'Users', 'Obtener la última dirección de envío', {
  response: ok('ShipmentRequest'),
  responses: { 200: ok('ShipmentRequest') },
});

post('/users/lastEnvioAddress', 'Users', 'Guardar la última dirección de envío', {
  body: body(ref('ShipmentRequest')),
  response: ok('ShipmentRequest'),
  responses: { 200: ok('ShipmentRequest') },
});

post('/users/photo', 'Users', 'Subir la foto de perfil', {
  body: multipartBody(
    {
      type: 'object',
      required: ['img'],
      properties: { img: { type: 'string', format: 'binary' } },
    },
    'Imagen de perfil.',
  ),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

del('/users/photo', 'Users', 'Eliminar la foto de perfil', {
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

get('/users/administracion', 'Users', 'Obtener la administración asignada', {
  response: free(),
  responses: { 200: free() },
});

/* Sorteos */
get('/sorteos/{raffleId}', 'Draws', 'Obtener un sorteo', {
  desc: 'Público. Incluye combinación, premios y fechas de cierre.',
  public: true,
  params: [pathParam('raffleId', 'Identificador del sorteo.', '11357')],
  response: ok('Draw'),
  responses: { 200: ok('Draw'), 404: { $ref: '#/components/responses/NotFound' } },
});

get('/sorteos/{raffleId}/partidos', 'Draws', 'Obtener los partidos de un sorteo', {
  public: true,
  params: [pathParam('raffleId', 'Identificador del sorteo.', '11357')],
  query: [queryParam('imgSize', 'Tamaño de los escudos en píxeles.', { type: 'integer', default: 20 })],
  response: ok('MatchesResponse'),
  responses: { 200: ok('MatchesResponse') },
});

get('/sorteos/finished', 'Draws', 'Listar sorteos finalizados', {
  public: true,
  query: [
    queryParam('firstResult', 'Offset de paginación.', { type: 'integer', default: 0 }),
    queryParam('maxResults', 'Tamaño de página.', { type: 'integer' }),
    queryParam('filters', 'Filtro de estado, p. ej. `state:ES`.', { type: 'string' }),
  ],
  response: ok('FinishedDrawsResponse'),
  responses: { 200: ok('FinishedDrawsResponse') },
});

get('/sorteos/finished/{gameTypes}', 'Draws', 'Listar sorteos finalizados por tipo de juego', {
  public: true,
  desc: 'Tipos de juego separados por `+` en minúsculas, p. ej. `quiniela+loteria`.',
  params: [pathParam('gameTypes', 'Tipos de juego separados por `+`.', 'quiniela')],
  query: [
    queryParam('firstResult', 'Offset de paginación.', { type: 'integer', default: 0 }),
    queryParam('filters', 'Filtro de estado, p. ej. `state:ES`.', { type: 'string' }),
  ],
  response: ok('FinishedDrawsResponse'),
  responses: { 200: ok('FinishedDrawsResponse') },
});

get('/matches/sorteos/{raffleId}', 'Draws', 'Obtener partidos (ruta legacy)', {
  public: true,
  params: [pathParam('raffleId', 'Identificador del sorteo.')],
  query: [queryParam('imgSize', 'Tamaño de los escudos.', { type: 'integer' })],
  response: ok('MatchesResponse'),
  responses: { 200: ok('MatchesResponse') },
});

get('/game/{gameId}/media', 'Draws', 'Obtener recursos multimedia del juego', {
  public: true,
  params: [pathParam('gameId', 'Identificador del juego.')],
  response: free(),
  responses: { 200: free() },
});

/* Juego */
post('/users/play', 'Play', 'Jugar una combinación', {
  desc: 'Requiere geolocalización (`x-geolocation`, `x-geolocation-timestamp`) en los flujos que la plataforma marque como obligatoria.',
  params: [headerRef('Geolocation'), headerRef('GeolocationTimestamp')],
  body: body(ref('PlayRequest')),
  response: ok('PlayResult'),
  responses: { 200: ok('PlayResult'), 400: { $ref: '#/components/responses/BadRequest' } },
});

post('/users/play/loteria', 'Play', 'Jugar décimos de lotería', {
  body: body(ref('LotteryPlayRequest')),
  response: ok('PlayResult'),
  responses: { 200: ok('PlayResult') },
});

post('/users/play/descriptor', 'Play', 'Jugar con descriptor de juego', {
  body: body(ref('PlayRequest')),
  response: ok('PlayResult'),
  responses: { 200: ok('PlayResult') },
});

post('/users/play/descriptor/validate', 'Play', 'Validar una jugada sin confirmarla', {
  body: body(ref('PlayRequest')),
  response: json({ type: 'object', properties: { status: { type: 'string' } } }),
  responses: { 200: json({ type: 'object', properties: { status: { type: 'string' } } }) },
});

post('/users/play/scannercode', 'Play', 'Jugar un código escaneado', {
  body: body(ref('ScannerCodeRequest')),
  response: ok('PlayResult'),
  responses: { 200: ok('PlayResult') },
});

post('/users/unfinish/play', 'Play', 'Guardar una jugada sin finalizar', {
  body: body(ref('PlayRequest')),
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

post('/users/unfinish/play/descriptor', 'Play', 'Guardar una jugada con descriptor sin finalizar', {
  body: body(ref('PlayRequest')),
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

post('/users/unfinish/jugar/loteria', 'Play', 'Guardar una jugada de lotería sin finalizar', {
  body: body(ref('LotteryPlayRequest')),
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

post('/users/prereserves/play', 'Play', 'Pre-reservar una jugada', {
  body: body(ref('PlayRequest')),
  response: ok('PlayResult'),
  responses: { 200: ok('PlayResult') },
});

post('/users/prereserves/play/descriptor', 'Play', 'Pre-reservar una jugada con descriptor', {
  body: body(ref('PlayRequest')),
  response: ok('PlayResult'),
  responses: { 200: ok('PlayResult') },
});

post('/users/lottery/search', 'Lottery', 'Buscar décimos (usuario autenticado)', {
  body: body(ref('LotterySearchRequest')),
  response: ok('LotterySearchResponse'),
  responses: { 200: ok('LotterySearchResponse') },
});

post('/lottery/search', 'Lottery', 'Buscar décimos (público)', {
  public: true,
  body: body(ref('LotterySearchRequest')),
  response: ok('LotterySearchResponse'),
  responses: { 200: ok('LotterySearchResponse') },
});

post('/users/lottery/free/search', 'Lottery', 'Buscar décimos gratuitos (usuario)', {
  body: body(ref('LotterySearchRequest')),
  response: ok('LotterySearchResponse'),
  responses: { 200: ok('LotterySearchResponse') },
});

post('/lottery/free/search', 'Lottery', 'Buscar décimos gratuitos (público)', {
  public: true,
  body: body(ref('LotterySearchRequest')),
  response: ok('LotterySearchResponse'),
  responses: { 200: ok('LotterySearchResponse') },
});

get('/lottery/info/{raffleId}', 'Lottery', 'Obtener stock e información de lotería', {
  public: true,
  params: [pathParam('raffleId', 'Identificador del sorteo.')],
  response: free('Información del sorteo de lotería'),
  responses: { 200: free('Información del sorteo de lotería') },
});

get('/users/lottery/info/{raffleId}', 'Lottery', 'Obtener stock de lotería (usuario)', {
  params: [pathParam('raffleId', 'Identificador del sorteo.')],
  response: free('Stock del sorteo'),
  responses: { 200: free('Stock del sorteo') },
});

get('/users/lottery/decimos/{raffleId}', 'Lottery', 'Listar décimos disponibles (usuario)', {
  params: [pathParam('raffleId', 'Identificador del sorteo.')],
  response: ok('LotterySearchResponse'),
  responses: { 200: ok('LotterySearchResponse') },
});

get('/lottery/decimos/{raffleId}', 'Lottery', 'Listar décimos disponibles (público)', {
  public: true,
  params: [pathParam('raffleId', 'Identificador del sorteo.')],
  response: ok('LotterySearchResponse'),
  responses: { 200: ok('LotterySearchResponse') },
});

get('/lottery/infoSubscribe', 'Lottery', 'Obtener información de suscripción a lotería', {
  public: true,
  response: json({ type: 'array', items: ref('LotterySubscriptionInfo') }),
  responses: { 200: json({ type: 'array', items: ref('LotterySubscriptionInfo') }) },
});

post('/users/papeletas', 'Lottery', 'Canjear papeletas', {
  body: body({ type: 'object', additionalProperties: true }),
  response: ok('PlayResult'),
  responses: { 200: ok('PlayResult') },
});

/* Boletos */
get('/users/boletos/me', 'Tickets', 'Listar mis boletos', {
  query: [queryParam('firstResult', 'Offset de paginación.', { type: 'integer', default: 0 })],
  response: ok('TicketsPage'),
  responses: { 200: ok('TicketsPage') },
});

get('/users/boletos/me/{gameIds}', 'Tickets', 'Listar mis boletos filtrados por juego', {
  desc: 'Los identificadores de juego se separan con `+` en minúsculas, p. ej. `quiniela+loteria`.',
  params: [pathParam('gameIds', 'Ids de juego separados por `+`.', 'quiniela')],
  query: [queryParam('firstResult', 'Offset de paginación.', { type: 'integer', default: 0 })],
  response: ok('TicketsPage'),
  responses: { 200: ok('TicketsPage') },
});

get('/users/boletos/me/filters', 'Tickets', 'Obtener filtros de boletos', {
  response: ok('TicketFiltersResponse'),
  responses: { 200: ok('TicketFiltersResponse') },
});

get('/users/boletos/{ticketId}', 'Tickets', 'Obtener un boleto', {
  params: [pathParam('ticketId', 'Identificador del boleto.', '123456')],
  response: ok('Ticket'),
  responses: { 200: ok('Ticket'), 404: { $ref: '#/components/responses/NotFound' } },
});

get('/users/boletos/html/{ticketId}', 'Tickets', 'Obtener el HTML del boleto', {
  params: [pathParam('ticketId', 'Identificador del boleto.')],
  response: text('HTML del boleto'),
  responses: { 200: text('HTML del boleto') },
});

put('/users/boletos/', 'Tickets', 'Editar el nombre de un boleto', {
  body: body(ref('EditTicketRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

put('/users/boletos/{ticketId}/archive', 'Tickets', 'Archivar un boleto', {
  params: [pathParam('ticketId', 'Identificador del boleto.')],
  body: body({ type: 'object', additionalProperties: true }),
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

put('/users/boletos/{ticketId}/unarchive', 'Tickets', 'Desarchivar un boleto', {
  params: [pathParam('ticketId', 'Identificador del boleto.')],
  body: body({ type: 'object', additionalProperties: true }),
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

put('/users/boletos/{ticketId}/cancel', 'Tickets', 'Cancelar un boleto', {
  params: [pathParam('ticketId', 'Identificador del boleto.')],
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

del('/users/boletos/{ticketId}', 'Tickets', 'Eliminar un boleto', {
  params: [pathParam('ticketId', 'Identificador del boleto.')],
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

del('/users/boletos/archivedAll', 'Tickets', 'Eliminar todos los boletos archivados', {
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

post('/users/compartir', 'Tickets', 'Compartir un boleto', {
  body: body(ref('ShareTicketRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

post('/users/compartir/prizeReturn', 'Tickets', 'Devolver el premio de un boleto compartido', {
  body: body({
    type: 'object',
    required: ['idBoleto'],
    properties: { idBoleto: { type: 'integer' } },
  }),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

post('/users/boleto/{ticketId}/subscribe', 'Tickets', 'Suscribirse a un boleto', {
  params: [pathParam('ticketId', 'Identificador del boleto.')],
  body: body(ref('SubscribeTicketRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

get('/users/lottery/boleto/{ticketId}/subscribe', 'Tickets', 'Obtener información de suscripción del boleto', {
  params: [pathParam('ticketId', 'Identificador del boleto.')],
  response: json({ type: 'array', items: ref('LotterySubscriptionInfo') }),
  responses: { 200: json({ type: 'array', items: ref('LotterySubscriptionInfo') }) },
});

del('/users/abonos/{subscriptionId}/subscription', 'Tickets', 'Cancelar una suscripción', {
  params: [pathParam('subscriptionId', 'Identificador de la suscripción.')],
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

post('/users/boleto/repeat', 'Tickets', 'Repetir un boleto', {
  body: body(ref('RepeatTicketRequest')),
  response: ok('PlayResult'),
  responses: { 200: ok('PlayResult') },
});

get('/users/boleto/{ticketId}/proof', 'Tickets', 'Descargar el justificante del boleto', {
  params: [pathParam('ticketId', 'Identificador del boleto.')],
  response: binary(),
  responses: { 200: binary() },
});

get('/users/boleto/{ticketId}/notifproof', 'Tickets', 'Enviar el justificante por email', {
  params: [pathParam('ticketId', 'Identificador del boleto.')],
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

post('/users/lotenal/boleto/{ticketId}/constancia', 'Tickets', 'Solicitar constancia de lotería nacional', {
  params: [pathParam('ticketId', 'Identificador del boleto.')],
  body: body({ type: 'object', additionalProperties: true }),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

post('/users/unfinish/boleto/repetir', 'Tickets', 'Guardar una repetición sin finalizar', {
  body: body(ref('RepeatTicketRequest')),
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

post('/users/enviocasa/v2/', 'Tickets', 'Solicitar envío a casa', {
  body: body(ref('ShipmentRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

post('/users/recogida/', 'Tickets', 'Solicitar recogida en administración', {
  body: body({ type: 'object', additionalProperties: true }),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

del('/users/recogida/{ticketId}', 'Tickets', 'Cancelar la recogida', {
  params: [pathParam('ticketId', 'Identificador del boleto.')],
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

get('/users/envioCasa/{ticketId}', 'Tickets', 'Calcular el precio de envío', {
  params: [pathParam('ticketId', 'Identificador del boleto.')],
  query: [queryParam('provinciaEnvio', 'Provincia de destino.', { type: 'string' }, true)],
  response: ok('ShipmentPrice'),
  responses: { 200: ok('ShipmentPrice') },
});

get('/envioCasa/{ticketId}', 'Tickets', 'Calcular el precio de envío (público)', {
  public: true,
  params: [pathParam('ticketId', 'Identificador del boleto.')],
  query: [queryParam('provinciaEnvio', 'Provincia de destino.', { type: 'string' }, true)],
  response: ok('ShipmentPrice'),
  responses: { 200: ok('ShipmentPrice') },
});

get('/delivery/checkCp', 'Tickets', 'Validar un código postal', {
  public: true,
  query: [
    queryParam('cp', 'Código postal.', { type: 'string' }, true),
    queryParam('province', 'Provincia.', { type: 'string' }, true),
  ],
  response: json({ type: 'object', properties: { valid: { type: 'boolean' } } }),
  responses: { 200: json({ type: 'object', properties: { valid: { type: 'boolean' } } }) },
});

/* Premios */
get('/users/premios/status/{ticketId}', 'Prizes', 'Consultar el estado del premio', {
  params: [pathParam('ticketId', 'Identificador del boleto.')],
  response: ok('PrizeStatus'),
  responses: { 200: ok('PrizeStatus') },
});

post('/users/premios/cancelPickup/{ticketId}', 'Prizes', 'Cancelar la recogida del premio', {
  params: [pathParam('ticketId', 'Identificador del boleto.')],
  body: body({ type: 'object', additionalProperties: true }),
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

post('/users/premios/requestDelivery/{ticketId}', 'Prizes', 'Solicitar el envío del premio', {
  params: [pathParam('ticketId', 'Identificador del boleto.')],
  body: body({ type: 'object', additionalProperties: true }),
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

post('/users/premios/signPickup/', 'Prizes', 'Firmar la recogida del premio', {
  body: body({
    type: 'object',
    required: ['signature'],
    properties: { signature: { type: 'string' } },
  }),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

/* Cartera */
get('/users/movimientos/me', 'Wallet', 'Listar movimientos de saldo', {
  response: ok('MoneyMovementsResponse'),
  responses: { 200: ok('MoneyMovementsResponse') },
});

get('/users/movimientos/status/{movementId}', 'Wallet', 'Consultar el estado de un movimiento', {
  params: [pathParam('movementId', 'Identificador del movimiento.')],
  response: ok('MoneyMovement'),
  responses: { 200: ok('MoneyMovement') },
});

get('/users/psp/redsys', 'Wallet', 'Iniciar el pago con Redsys', {
  query: [
    queryParam('amount', 'Importe en euros.', { type: 'number' }, true),
    queryParam('redirectUrlAfter', 'URL de retorno.', { type: 'string', format: 'uri' }),
    queryParam('useSavedCreditCard', 'Usar tarjeta guardada.', { type: 'boolean' }),
    queryParam('creditCardAlias', 'Alias de la tarjeta.', { type: 'string' }),
    queryParam('autoCreditMultiple', 'Recarga automática.', { type: 'integer' }),
  ],
  response: text('Redirección o formulario Redsys'),
  responses: { 200: text('Redirección o formulario Redsys') },
});

get('/users/movimientos/pspResponse', 'Wallet', 'Procesar la respuesta del PSP', {
  response: free(),
  responses: { 200: free() },
});

post('/users/withdraw', 'Wallet', 'Solicitar un reintegro', {
  query: [queryParam('enhanced', 'Activa el flujo mejorado.', { type: 'boolean', default: true })],
  body: formBody(ref('WithdrawRequest'), 'Datos del reintegro.'),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

get('/users/withdrawInfo', 'Wallet', 'Obtener información de reintegro', {
  response: free('Información de reintegro'),
  responses: { 200: free('Información de reintegro') },
});

post('/users/withdraw/v2', 'Wallet', 'Solicitar un reintegro (v2)', {
  body: body(ref('WithdrawV2Request')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

post('/users/withdrawal/send-otp', 'Wallet', 'Enviar OTP para el reintegro', {
  body: body({
    type: 'object',
    properties: { amount: { type: 'number' }, account: { type: 'string' } },
    additionalProperties: true,
  }),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

post('/users/withdrawal/verify-otp', 'Wallet', 'Verificar OTP del reintegro', {
  body: body({
    type: 'object',
    required: ['code'],
    properties: { code: { type: 'string' } },
    additionalProperties: true,
  }),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

get('/users/credit/bankTransferRedirectInfo', 'Wallet', 'Obtener datos para transferencia bancaria', {
  response: free(),
  responses: { 200: free() },
});

post('/users/credit/external', 'Wallet', 'Recargar por método externo', {
  body: body(ref('ExternalCreditRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

del('/users/creditCard', 'Wallet', 'Eliminar la tarjeta guardada', {
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

post('/users/autoCredit', 'Wallet', 'Configurar la recarga automática', {
  body: body(ref('AutoCreditRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

del('/users/autoCredit', 'Wallet', 'Desactivar la recarga automática', {
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

del('/users/bankaccount', 'Wallet', 'Eliminar la cuenta bancaria', {
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

post('/users/credit/native', 'Wallet', 'Recargar con pasarela nativa', {
  body: body({ type: 'object', additionalProperties: true }),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

put('/users/withdrawalrequest/markAsDisplayed/{requestId}', 'Wallet', 'Marcar un reintegro como mostrado', {
  params: [pathParam('requestId', 'Identificador de la solicitud.')],
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

get('/users/movimientos/summary', 'Wallet', 'Obtener el resumen anual', {
  query: [queryParam('year', 'Año del resumen.', { type: 'integer' }, true)],
  response: free('Resumen de movimientos'),
  responses: { 200: free('Resumen de movimientos') },
});

get('/users/movimientos/summary/pdf', 'Wallet', 'Descargar el resumen anual en PDF', {
  query: [queryParam('year', 'Año del resumen.', { type: 'integer' }, true)],
  response: binary(),
  responses: { 200: binary() },
});

post('/users/credit/pci', 'Wallet', 'Recargar con tarjeta (PCI)', {
  body: body(ref('CreditCardRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

post('/users/credit/pci/savedCard', 'Wallet', 'Recargar con tarjeta guardada', {
  body: body(ref('CreditCardRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

post('/users/credit/pci/saveCardWithoutCredit', 'Wallet', 'Guardar tarjeta sin recargar', {
  body: body({
    type: 'object',
    required: ['saveCardAlias'],
    properties: { saveCardAlias: { type: 'string' }, favorite: { type: 'boolean' } },
  }),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

get('/users/paymentmethod', 'Wallet', 'Listar métodos de pago', {
  response: json({ type: 'array', items: ref('PaymentMethod') }),
  responses: { 200: json({ type: 'array', items: ref('PaymentMethod') }) },
});

post('/users/paymentmethod/direct', 'Wallet', 'Añadir método de pago directo', {
  body: body(ref('PaymentMethodLoadRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

post('/users/paymentmethod/widget', 'Wallet', 'Crear widget de método de pago', {
  body: body({ type: 'object', required: ['id'], properties: { id: { type: 'string' } }, additionalProperties: true }),
  response: json({ type: 'object', properties: { html: { type: 'string' } } }),
  responses: { 200: json({ type: 'object', properties: { html: { type: 'string' } } }) },
});

post('/users/paymentmethod/external/create-widget', 'Wallet', 'Crear widget de pasarela externa', {
  body: body({ type: 'object', additionalProperties: true }),
  response: json({ type: 'object', properties: { html: { type: 'string' } } }),
  responses: { 200: json({ type: 'object', properties: { html: { type: 'string' } } }) },
});

post('/users/paymentmethod/load', 'Wallet', 'Cargar saldo con método de pago', {
  body: body(ref('PaymentMethodLoadRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

post('/users/paymentmethod/withdraw', 'Wallet', 'Retirar saldo a método de pago', {
  body: body(ref('PaymentMethodLoadRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

del('/users/paymentmethod/{id}', 'Wallet', 'Eliminar método de pago', {
  params: [pathParam('id', 'Identificador del método de pago.')],
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

post('/users/paymentmethod/favorite/{id}', 'Wallet', 'Marcar método de pago como favorito', {
  params: [pathParam('id', 'Identificador del método de pago.')],
  body: body({ type: 'object', additionalProperties: true }),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

get('/users/android/subscription', 'Wallet', 'Obtener la suscripción de Android', {
  response: free(),
  responses: { 200: free() },
});

post('/users/android/subscription', 'Wallet', 'Crear la suscripción de Android', {
  body: body({ type: 'object', additionalProperties: true }),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

del('/users/android/subscription', 'Wallet', 'Cancelar la suscripción de Android', {
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

/* Grupos */
get('/users/groups/{groupId}', 'Groups', 'Obtener un grupo', {
  params: [pathParam('groupId', 'Identificador del grupo.')],
  query: [queryParam('lastUpdate', 'Timestamp de la última sincronización.', { type: 'integer', format: 'int64' })],
  response: ok('Group'),
  responses: { 200: ok('Group') },
});

post('/users/groups', 'Groups', 'Crear un grupo', {
  body: body(ref('GroupCreateRequest')),
  response: json({ type: 'object', properties: { id: { oneOf: [{ type: 'string' }, { type: 'integer' }] } } }),
  responses: { 200: json({ type: 'object', properties: { id: { oneOf: [{ type: 'string' }, { type: 'integer' }] } } }) },
});

post('/users/groups/join', 'Groups', 'Unirse a un grupo', {
  body: body({ type: 'object', required: ['code'], properties: { code: { type: 'string' } } }),
  response: ok('Group'),
  responses: { 200: ok('Group') },
});

put('/users/groups/{groupId}', 'Groups', 'Actualizar un grupo', {
  params: [pathParam('groupId', 'Identificador del grupo.')],
  body: body(ref('GroupUpdateRequest')),
  response: ok('Group'),
  responses: { 200: ok('Group') },
});

put('/users/groups/{groupId}/members/me/profile', 'Groups', 'Actualizar mi perfil dentro del grupo', {
  params: [pathParam('groupId', 'Identificador del grupo.')],
  body: body(ref('GroupUpdateRequest')),
  response: ok('Group'),
  responses: { 200: ok('Group') },
});

del('/users/groups/{groupId}/members/me', 'Groups', 'Abandonar un grupo', {
  params: [pathParam('groupId', 'Identificador del grupo.')],
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

post('/users/groups/{groupId}/members', 'Groups', 'Invitar miembros al grupo', {
  params: [pathParam('groupId', 'Identificador del grupo.')],
  body: body(ref('GroupMemberInvite')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

del('/users/groups/{groupId}/members/{userId}', 'Groups', 'Expulsar a un miembro del grupo', {
  params: [
    pathParam('groupId', 'Identificador del grupo.'),
    pathParam('userId', 'Identificador del usuario.'),
  ],
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

for (const action of ['request', 'withdraw', 'withdrawParticipants', 'transfer', 'transferPending']) {
  post(`/users/groups/{groupId}/balance/${action}`, 'Groups', `Operación de saldo: ${action}`, {
    params: [pathParam('groupId', 'Identificador del grupo.')],
    body: body(ref('GroupMoneyRequest')),
    response: ok('Group'),
    responses: { 200: ok('Group') },
  });
}

post('/users/groups/{groupId}/balance/transferCycle', 'Groups', 'Transferir saldo del ciclo', {
  params: [pathParam('groupId', 'Identificador del grupo.')],
  body: body({ type: 'object', required: ['amount'], properties: { amount: { type: 'number' } } }),
  response: ok('Group'),
  responses: { 200: ok('Group') },
});

for (const action of ['withdraw', 'withdrawAll', 'transfer']) {
  post(`/users/groups/{groupId}/balanceBlocked/${action}`, 'Groups', `Operación de saldo bloqueado: ${action}`, {
    params: [pathParam('groupId', 'Identificador del grupo.')],
    body: body(ref('GroupMoneyRequest')),
    response: ok('Group'),
    responses: { 200: ok('Group') },
  });
}

post('/users/groups/{groupId}/message', 'Groups', 'Enviar un mensaje al grupo', {
  params: [pathParam('groupId', 'Identificador del grupo.')],
  body: body(ref('GroupMessageRequest')),
  response: ok('Group'),
  responses: { 200: ok('Group') },
});

post('/users/groups/{groupId}/photo', 'Groups', 'Subir la foto del grupo', {
  params: [pathParam('groupId', 'Identificador del grupo.')],
  body: multipartBody(
    { type: 'object', required: ['img'], properties: { img: { type: 'string', format: 'binary' } } },
    'Imagen del grupo.',
  ),
  response: free(),
  responses: { 200: free() },
});

get('/users/codes/{code}/availability', 'Groups', 'Comprobar disponibilidad de código de grupo', {
  params: [pathParam('code', 'Código propuesto.')],
  response: noContent,
  responses: { 200: noContent, 400: { $ref: '#/components/responses/BadRequest' } },
});

get('/groups/{code}', 'Groups', 'Obtener un grupo por código', {
  params: [pathParam('code', 'Código del grupo.')],
  response: ok('Group'),
  responses: { 200: ok('Group') },
});

get('/users/groups/{groupId}/history/balance', 'Groups', 'Historial de saldo del grupo', {
  params: [pathParam('groupId', 'Identificador del grupo.')],
  query: [
    queryParam('idLessThan', 'Cursor: id menor que.', { type: 'integer' }),
    queryParam('types', 'Tipos separados por comas.', { type: 'string' }),
  ],
  response: json({
    type: 'object',
    properties: { items: { type: 'array', items: ref('GroupMoneyActivity') }, total: { type: 'integer' } },
  }),
  responses: {
    200: json({
      type: 'object',
      properties: { items: { type: 'array', items: ref('GroupMoneyActivity') }, total: { type: 'integer' } },
    }),
  },
});

get('/users/groups/{groupId}/history', 'Groups', 'Historial de actividad del grupo', {
  params: [pathParam('groupId', 'Identificador del grupo.')],
  query: [
    queryParam('numResults', 'Número de resultados.', { type: 'integer', default: 10 }),
    queryParam('idLessThan', 'Cursor hacia atrás.', { type: 'integer' }),
    queryParam('idGreaterThan', 'Cursor hacia delante.', { type: 'integer' }),
  ],
  response: json({
    type: 'object',
    properties: { items: { type: 'array', items: ref('GroupMoneyActivity') }, total: { type: 'integer' } },
  }),
  responses: {
    200: json({
      type: 'object',
      properties: { items: { type: 'array', items: ref('GroupMoneyActivity') }, total: { type: 'integer' } },
    }),
  },
});

get('/users/groups/{groupId}/members/{userId}/history', 'Groups', 'Historial de un miembro', {
  params: [
    pathParam('groupId', 'Identificador del grupo.'),
    pathParam('userId', 'Identificador del usuario.'),
  ],
  response: json({
    type: 'object',
    properties: { items: { type: 'array', items: ref('GroupMoneyActivity') }, total: { type: 'integer' } },
  }),
  responses: {
    200: json({
      type: 'object',
      properties: { items: { type: 'array', items: ref('GroupMoneyActivity') }, total: { type: 'integer' } },
    }),
  },
});

/* Clubes y peñas */
get('/penyas/{gameId}', 'Clubs', 'Listar peñas de un juego', {
  public: true,
  params: [pathParam('gameId', 'Identificador del juego.')],
  response: ok('PenyaList'),
  responses: { 200: ok('PenyaList') },
});

get('/users/penyas/{gameId}', 'Clubs', 'Listar peñas de un juego (usuario)', {
  params: [pathParam('gameId', 'Identificador del juego.')],
  response: ok('PenyaList'),
  responses: { 200: ok('PenyaList') },
});

post('/users/penyas/v1/participacion/multiple', 'Clubs', 'Jugar participaciones de peña', {
  body: body(ref('ClubPlayRequest')),
  response: ok('PlayResult'),
  responses: { 200: ok('PlayResult') },
});

post('/users/penyas/private/join', 'Clubs', 'Unirse a una peña privada', {
  body: body(ref('JoinPrivateClubRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

get('/loteriaEmpresas/{code}', 'Clubs', 'Obtener peña de empresa por código', {
  public: true,
  params: [pathParam('code', 'Código de la peña.')],
  response: ok('PenyaList'),
  responses: { 200: ok('PenyaList') },
});

get('/users/penyas/promo/{code}', 'Clubs', 'Obtener peña promocional por código', {
  params: [pathParam('code', 'Código promocional.')],
  response: ok('PenyaList'),
  responses: { 200: ok('PenyaList') },
});

get('/loteriaEmpresas/isChildAvailable/{code}', 'Clubs', 'Comprobar código hijo disponible', {
  public: true,
  params: [pathParam('code', 'Código hijo.')],
  query: [queryParam('parentCode', 'Código padre.', { type: 'string' }, true)],
  response: noContent,
  responses: { 200: noContent, 400: { $ref: '#/components/responses/BadRequest' } },
});

get('/users/loteriaEmpresas/isChildAvailable/{code}', 'Clubs', 'Comprobar código hijo disponible (usuario)', {
  params: [pathParam('code', 'Código hijo.')],
  query: [queryParam('parentCode', 'Código padre.', { type: 'string' }, true)],
  response: noContent,
  responses: { 200: noContent, 400: { $ref: '#/components/responses/BadRequest' } },
});

post('/users/unfinish/penyas/participacion/multiple', 'Clubs', 'Guardar participación de peña sin finalizar', {
  body: body(ref('ClubPlayRequest')),
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

put('/users/penyas/hide/{clubId}', 'Clubs', 'Ocultar una peña', {
  params: [pathParam('clubId', 'Identificador de la peña.')],
  body: body({ type: 'object', additionalProperties: true }),
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

put('/users/penyas/mute/{clubId}', 'Clubs', 'Silenciar una peña', {
  params: [pathParam('clubId', 'Identificador de la peña.')],
  body: body({ type: 'object', additionalProperties: true }),
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

post('/users/loteriaEmpresas', 'Clubs', 'Crear peña de empresa', {
  body: body(ref('CompanyClubRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

put('/users/loteriaEmpresas', 'Clubs', 'Actualizar peña de empresa', {
  body: body(ref('CompanyClubRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

del('/users/loteriaEmpresas/{id}', 'Clubs', 'Eliminar peña de empresa', {
  params: [pathParam('id', 'Identificador de la peña.')],
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

get('/users/loteriaEmpresas/{id}', 'Clubs', 'Obtener peña de empresa', {
  params: [pathParam('id', 'Identificador de la peña.')],
  response: ok('Penya'),
  responses: { 200: ok('Penya') },
});

post('/users/loteriaEmpresas/image', 'Clubs', 'Subir imagen de peña de empresa', {
  body: multipartBody(
    {
      type: 'object',
      required: ['penyaId', 'img'],
      properties: {
        penyaId: { type: 'string' },
        img: { type: 'string', format: 'binary' },
      },
    },
    'Imagen y peña asociada.',
  ),
  response: free(),
  responses: { 200: free() },
});

get('/users/loteriaEmpresas/isPromoCodeFree/{code}', 'Clubs', 'Comprobar si el código promocional está libre', {
  params: [pathParam('code', 'Código promocional.')],
  response: json({ type: 'boolean' }),
  responses: { 200: json({ type: 'boolean' }) },
});

get('/users/loteriaEmpresas/penyasCreationInfo/{code}', 'Clubs', 'Obtener información para crear la peña', {
  params: [pathParam('code', 'Código promocional.')],
  response: free(),
  responses: { 200: free() },
});

get('/users/penyas/boletos/{penyaId}', 'Clubs', 'Listar boletos de una peña', {
  params: [pathParam('penyaId', 'Identificador de la peña.')],
  response: json({ type: 'object', properties: { object: { type: 'array', items: ref('Ticket') } } }),
  responses: {
    200: json({ type: 'object', properties: { object: { type: 'array', items: ref('Ticket') } } }),
  },
});

/* KYC */
post('/users/kyc/servlet/{processId}', 'KYC', 'Abrir el proceso KYC', {
  params: [pathParam('processId', 'Identificador del proceso.')],
  query: [queryParam('id', 'Identificador del documento o proceso.', { type: 'string' }, true)],
  body: body({ type: 'object', additionalProperties: true }),
  response: ok('KycStatus'),
  responses: { 200: ok('KycStatus') },
});

post('/users/kyc/scanner/parse', 'KYC', 'Parsear un documento con el escáner', {
  body: body(ref('KycScannerParseRequest')),
  response: ok('KycScannerParseResponse'),
  responses: { 200: ok('KycScannerParseResponse') },
});

/* Noticias */
get('/newsflash', 'News', 'Listar noticias públicas', {
  public: true,
  params: [headerRef('Region')],
  query: [
    queryParam('firstResult', 'Offset de paginación.', { type: 'integer', default: 0 }),
  ],
  response: ok('NewsResponse'),
  responses: { 200: ok('NewsResponse') },
});

get('/users/news', 'News', 'Listar noticias del usuario', {
  params: [headerRef('Region')],
  query: [
    queryParam('firstResult', 'Offset de paginación.', { type: 'integer', default: 0 }),
  ],
  response: ok('NewsResponse'),
  responses: { 200: ok('NewsResponse') },
});

get('/guestnews/{id}', 'News', 'Marcar noticia pública como visitada', {
  public: true,
  params: [pathParam('id', 'Identificador de la noticia.')],
  response: free(),
  responses: { 200: free() },
});

get('/users/news/{id}', 'News', 'Marcar noticia del usuario como visitada', {
  params: [pathParam('id', 'Identificador de la noticia.')],
  response: free(),
  responses: { 200: free() },
});

post('/users/news/touch', 'News', 'Marcar todas las noticias como leídas', {
  body: body({ type: 'object', additionalProperties: true }),
  response: noContent,
  responses: { 200: noContent, 204: noContent },
});

/* Plataforma */
get('/endpoint', 'Platform', 'Obtener la configuración de la plataforma', {
  public: true,
  desc: 'Configuración por endpoint/dominio: moneda, locales, horas de reintegro, features y textos legales.',
  response: ok('EndpointConfig'),
  responses: { 200: ok('EndpointConfig') },
});

get('/users/allinfo/v2', 'Platform', 'Obtener la configuración completa del usuario', {
  query: [queryParam('lastUpdate', 'Timestamp de la última actualización conocida.', { type: 'integer', format: 'int64' })],
  response: ok('AllInfoResponse'),
  responses: { 200: ok('AllInfoResponse') },
});

get('/facebook/login/info', 'Platform', 'Obtener la configuración de login de Facebook', {
  public: true,
  response: ok('FacebookLoginInfo'),
  responses: { 200: ok('FacebookLoginInfo') },
});

/* Soporte */
post('/users/suggestion', 'Support', 'Enviar una sugerencia autenticada', {
  body: body(ref('SuggestionRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

post('/suggestion', 'Support', 'Enviar una sugerencia anónima', {
  public: true,
  body: body(ref('SuggestionRequest')),
  response: ok('MessageResponse'),
  responses: { 200: ok('MessageResponse') },
});

/* -------------------------------------------------------------------------- */
/* Documento                                                                   */
/* -------------------------------------------------------------------------- */

const doc = {
  openapi: '3.0.3',
  info: {
    title: 'Tulotero Web API (reconstruida)',
    version: '1.0.0',
    description: [
      'Contrato reconstruido a partir del bundle público de **web.tulotero.es** y del mirror local de `IV/`.',
      'No es una especificación oficial de Tulotero y puede cambiar sin previo aviso.',
      '',
      '### Autenticación',
      '1. `POST /installation` para obtener `instalacionId`.',
      '2. `POST /userLogin` (form) o login social para obtener `token`, `refreshToken` y `refreshTokenUrl`.',
      '3. Enviar `Authorization: Bearer <token>` en las rutas privadas.',
      '4. Ante `401`/`403`, refrescar una sola vez con `refreshToken` + `clientTimestamp` y reintentar.',
      '5. Ante `body.status === "FRAUD_DETECTED"`, cerrar sesión y no reintentar. Un `426` indica verificación de identidad pendiente.',
      '',
      '### Cabeceras',
      '`AvoidRedirect: true` y `Client: web` son obligatorias. `Accept-Language` y `ngTime` (epoch ms) acompañan a todas las peticiones.',
      'Las rutas de autenticación y `users/` requieren además las cabeceras de dispositivo. Los flujos de juego pueden requerir geolocalización.',
    ].join('\n'),
    contact: { name: 'Reconstrucción no oficial' },
    license: { name: 'Uso informativo — sin licencia oficial de Tulotero' },
  },
  servers: [
    {
      url: 'https://web-backend.es.tulotero.net/tuloteroweb/rest',
      description: 'Producción (ES)',
    },
    {
      url: 'http://127.0.0.1:4300/backend-proxy-es/tuloteroweb/rest',
      description: 'Mirror local de IV/mirror',
    },
  ],
  tags: [
    { name: 'Authentication', description: 'Login, refresh, registro, instalación y dispositivos.' },
    { name: 'Users', description: 'Perfil, preferencias, límites, juego responsable, agenda y verificación.' },
    { name: 'Draws', description: 'Sorteos, resultados y partidos.' },
    { name: 'Play', description: 'Realización y validación de jugadas.' },
    { name: 'Lottery', description: 'Búsqueda y compra de décimos de lotería.' },
    { name: 'Tickets', description: 'Boletos, suscripciones, repeticiones, envíos y justificantes.' },
    { name: 'Prizes', description: 'Estado y entrega de premios.' },
    { name: 'Wallet', description: 'Saldo, movimientos, reintegros, tarjetas y pasarelas.' },
    { name: 'Groups', description: 'Grupos de juego y saldos compartidos.' },
    { name: 'Clubs', description: 'Peñas, clubes y lotería de empresa.' },
    { name: 'KYC', description: 'Verificación de identidad y escaneo de documentos.' },
    { name: 'News', description: 'Noticias públicas y del usuario.' },
    { name: 'Platform', description: 'Configuración, allinfo y estado de registro.' },
    { name: 'Support', description: 'Sugerencias y contacto.' },
  ],
  components: {
    securitySchemes: {
      bearerAuth: {
        type: 'http',
        scheme: 'bearer',
        bearerFormat: 'JWT',
        description: 'JWT devuelto por `/userLogin`. También se acepta el esquema legacy `Basic` (email:password en base64).',
      },
    },
    parameters: {
      AcceptLanguage: {
        name: 'Accept-Language',
        in: 'header',
        description: 'Locale solicitado, p. ej. `es-ES`.',
        schema: { type: 'string', example: 'es-ES' },
      },
      NgTime: {
        name: 'ngTime',
        in: 'header',
        description: 'Marca de tiempo del cliente en milisegundos (epoch).',
        schema: { type: 'string', example: '1729512345678' },
      },
      AvoidRedirect: {
        name: 'AvoidRedirect',
        in: 'header',
        description: 'Evita redirecciones HTML del backend.',
        schema: { type: 'string', enum: ['true'] },
      },
      Client: {
        name: 'Client',
        in: 'header',
        description: 'Canal que realiza la petición.',
        schema: { type: 'string', enum: ['web'] },
      },
      DeviceId: {
        name: 'deviceId',
        in: 'header',
        description: 'Identificador estable del dispositivo.',
        schema: { type: 'string' },
      },
      DeviceType: {
        name: 'deviceType',
        in: 'header',
        description: 'Tipo de dispositivo.',
        schema: { type: 'string', example: 'WEB' },
      },
      DeviceDesc: {
        name: 'deviceDesc',
        in: 'header',
        description: 'Descripción del navegador/dispositivo.',
        schema: { type: 'string', example: 'Chrome(120.0.0.0)' },
      },
      OsVersion: {
        name: 'osVersion',
        in: 'header',
        description: 'Versión del sistema operativo.',
        schema: { type: 'string', example: 'Windows(10)' },
      },
      VersionCode: {
        name: 'versionCode',
        in: 'header',
        description: 'Versión de la app web.',
        schema: { type: 'string', example: '1389' },
      },
      Mode: {
        name: 'mode',
        in: 'header',
        description: 'Modo de presentación.',
        schema: { type: 'string', enum: ['desktop', 'mobile'] },
      },
      AndroidRegistrationId: {
        name: 'androidRegistrationId',
        in: 'header',
        description: 'Token de registro push de Android, si existe.',
        schema: { type: 'string' },
      },
      Geolocation: {
        name: 'x-geolocation',
        in: 'header',
        description: '`latitud:longitud:precisión`',
        schema: { type: 'string', example: '40.4168:-3.7038:20' },
      },
      GeolocationTimestamp: {
        name: 'x-geolocation-timestamp',
        in: 'header',
        description: 'Timestamp de la posición en milisegundos.',
        schema: { type: 'string', example: '1729512345678' },
      },
      Region: {
        name: 'region',
        in: 'header',
        description: 'Región para noticias y contenido localizado.',
        schema: { type: 'string', example: 'ES' },
      },
    },
    responses: {
      BadRequest: {
        description: 'Petición inválida o regla de negocio incumplida.',
        content: { 'application/json': { schema: ref('ApiError') } },
      },
      Unauthorized: {
        description: 'Token ausente, inválido o caducado. Puede devolver `X-Token-Expired`.',
        content: { 'application/json': { schema: ref('ApiError') } },
      },
      Forbidden: {
        description: 'Sin permisos, cuenta bloqueada o sesión no válida.',
        content: { 'application/json': { schema: ref('ApiError') } },
      },
      NotFound: {
        description: 'Recurso no encontrado.',
        content: { 'application/json': { schema: ref('ApiError') } },
      },
      VerificationRequired: {
        description: 'Verificación de identidad requerida (HTTP 426).',
        content: { 'application/json': { schema: ref('ApiError') } },
      },
      FraudDetected: {
        description: 'Antifraude: el cuerpo incluye `status: "FRAUD_DETECTED"`. Cerrar sesión.',
        content: { 'application/json': { schema: ref('ApiError') } },
      },
      ServerError: {
        description: 'Error interno del backend.',
        content: { 'application/json': { schema: ref('ApiError') } },
      },
    },
    schemas: S,
  },
  paths,
};

writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
console.log(`openapi.json generado: ${operationCounter} operaciones, ${Object.keys(paths).length} rutas`);
