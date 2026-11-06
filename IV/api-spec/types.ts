/**
 * Tulotero Web API — DTOs reconstruidos desde el bundle público `web.tulotero.es`.
 *
 * Convenciones:
 * - `EpochMillis` es un instante UNIX en milisegundos, tal y como lo devuelve el backend.
 * - Los nombres de campo del backend se conservan en los DTOs `*Backend` / request.
 * - Los campos marcados como opcionales pueden no aparecer en todas las versiones del backend.
 *
 * Fuente: chunks `main-C3X6YJSJ.js`, `chunk-JO6APRZG.js`, `chunk-NUHOMZD2.js`,
 * `chunk-WEX6YN76.js`, `chunk-TSL3EOLW.js`, `chunk-FXWRA6BL.js`, `chunk-6OPYFK4X.js`.
 * No es una especificación oficial de Tulotero.
 */

export type EpochMillis = number;
export type ISODateString = string;
export type CurrencyAmount = number;
export type JsonObject = Record<string, unknown>;

/* -------------------------------------------------------------------------- */
/* Envelopes y errores                                                         */
/* -------------------------------------------------------------------------- */

export interface ApiErrorBody {
  status?: string;
  message?: string;
  code?: string;
  info?: string;
  object?: unknown;
  [key: string]: unknown;
}

export interface MessageResponse {
  status?: string;
  message?: string;
  object?: unknown;
}

export interface PaginatedResponse<T> {
  total: number;
  firstResult?: number;
  maxResults?: number;
  items: T[];
}

export interface BackendPage<T = unknown> {
  total?: number;
  totalEntries?: number;
  entries?: T[];
  items?: T[];
  [key: string]: unknown;
}

export interface ResultAvailability {
  result: boolean;
}

/* -------------------------------------------------------------------------- */
/* Configuración de plataforma                                                 */
/* -------------------------------------------------------------------------- */

export interface EndpointConfig {
  id: string;
  name: string;
  minHourWithdrawal?: string;
  maxHourWithdrawal?: string;
  serverLocale?: string;
  supportedLocales?: string[];
  serverTimeZone?: string;
  currencySymbol?: string;
  metricUnit?: string;
  twitter?: string;
  facebook?: string;
  instagram?: string;
  landingUrl?: string;
  terms?: string;
  responsibleGame?: string;
  selfExclusionUrlInfo?: string;
  penyas?: boolean;
  groups?: boolean;
  administrations?: boolean;
  nif?: boolean;
  transferOptions?: TransferOptions;
  adminsUrl?: string;
  [key: string]: unknown;
}

export interface TransferOptions {
  virtualAccountEndpoint?: string;
  createVirtualAccountEndpoint?: string;
  [key: string]: unknown;
}

export interface AllInfoResponse {
  endpoint: EndpointConfig;
  administraciones?: JsonObject[];
  states?: JsonObject[];
  booths?: JsonObject[];
  [key: string]: unknown;
}

export interface VersionFile {
  noDeleteAllInfoInVersion: number[];
}

/* -------------------------------------------------------------------------- */
/* Autenticación                                                               */
/* -------------------------------------------------------------------------- */

export type AuthStrategyType = 'JWT' | 'BASIC';

export interface InstallationRequest {
  /** JSON serializado con `af_status`, `media_source` y `campaign`. */
  jsonInfo: string;
  tipo: 'WEB';
}

export interface InstallationMetadata {
  af_status: 'Organic' | 'Non-organic';
  media_source: string;
  campaign: string;
}

export interface LoginRequest {
  username: string;
  password: string;
  installationId: number;
}

export interface LoginResponse {
  /** Access token JWT. Caduca según `exp` del propio token. */
  token: string;
  refreshToken: string;
  /** URL absoluta contra la que se refresca el token. Puede variar por país/entorno. */
  refreshTokenUrl: string;
  refreshTokenExpirationDate: EpochMillis;
  /** Presente en altas sociales: "true" cuando la cuenta se acaba de registrar. */
  registered?: string;
  jwtLogin?: boolean;
  [key: string]: unknown;
}

export interface RefreshTokenRequest {
  refreshToken: string;
  /** Marca de tiempo del cliente, en milisegundos. */
  clientTimestamp: string;
}

export interface RefreshTokenResponse {
  /** Formato principal observado. */
  token: string;
  /** Formato alternativo aceptado por el frontend. */
  accessToken?: string | { token: string };
  refreshToken: string;
  refreshTokenExpirationDate?: EpochMillis;
}

export interface SocialLoginRequest {
  token: string;
  deviceType: 'WEB';
  registerDeviceId: string;
  instalacionId: number;
  /** Solo Facebook. Lista de permisos concedidos, p. ej. "email,public_profile". */
  grantedPermissions?: string;
  /** Solo Apple. */
  userName?: string;
}

export interface FacebookLoginInfo {
  appId: string;
  permissions: string;
  disabledMessage?: string;
}

export interface RegisterRequest {
  name: string;
  mail: string;
  password: string;
  promoCode?: string;
  deviceType: 'WEB';
  registerDeviceId: string;
  /** El frontend escribe `instalationId` (con una sola "l") en este endpoint. */
  instalationId: number;
}

export interface StartPasswordResetRequest {
  mail: string;
}

export interface JwtPayload {
  sub?: string;
  exp?: number;
  iat?: number;
  [key: string]: unknown;
}

export interface StoredSession {
  strategy: AuthStrategyType;
  accessToken?: string;
  basicToken?: string;
  refreshToken?: string;
  refreshTokenUrl?: string;
  refreshTokenExpirationDate?: EpochMillis;
}

/* -------------------------------------------------------------------------- */
/* Usuario y perfil                                                            */
/* -------------------------------------------------------------------------- */

export interface UserAddress {
  addressLine: string;
  city: string;
  stateZipCode: {
    zipCode: string;
    state: string;
  };
  observations?: string;
}

export interface DocumentInfo {
  documentType?: string;
  documentNumber?: string;
  documentExpirationDate?: string;
  documentIssuingEntity?: string;
  cifType?: string;
}

export interface UserExtra {
  residente?: boolean;
  comunitario?: boolean;
  pasaporte?: boolean;
  middleName?: string;
  suffixName?: string;
  userStateCode?: string;
  inAppManagedBigPrizeTicketsNotified?: string;
  locale?: string;
  barcodeUsed?: string;
  groups_hide_keep_managed?: boolean;
  documentType?: string;
  documentNumber?: string;
  documentExpirationDate?: string;
  documentIssuingEntity?: string;
  cifType?: string;
  enableTicketBulkActions?: boolean;
  insuranceAvailable?: boolean;
  jwtLogin?: boolean;
  [key: string]: unknown;
}

/** Payload exacto de `PUT /users/me` (nombres del backend). */
export interface UpdateProfileRequest {
  id?: number;
  codigo?: string;
  nombre?: string;
  apellidos?: string;
  iniciales?: string;
  fechaNacimientoString?: string;
  newPassword?: string;
  direccion?: string;
  cp?: string;
  poblacion?: string;
  provincia?: string;
  pais?: string;
  telefono?: string;
  cif?: string;
  saldo?: CurrencyAmount;
  pictureUrl?: string;
  cuentaBancaria?: string;
  administracion?: string;
  emailVerificado?: boolean;
  telefonoVerificado?: boolean;
  creditCardAlias?: string;
  creditCardExpiryDate?: string;
  autoCreditMultiple?: number;
  tokenSponsor?: string;
  tokenSponsorUrl?: string;
  extra?: UserExtra;
  shouldValidateMandatoryFields?: boolean;
}

export type UserProfileResponse = UpdateProfileRequest & {
  id: number;
  codigo: string;
  nombre?: string;
  apellidos?: string;
  saldo: CurrencyAmount;
  mailVerificado?: boolean;
  telefonoVerificado?: boolean;
  fechaRegistro?: EpochMillis;
  locale?: string;
  kyc?: KycStatus;
  shouldCallFetchingEvents?: boolean;
  extra?: UserExtra;
};

export interface UpdateEmailRequest {
  mail: string;
}

export interface VerifyPhoneRequest {
  numero: string;
  token?: string;
}

export interface LocaleResponse {
  locale: string;
}

export interface ExtraFieldRequest {
  name: string;
  value: string;
}

export interface ReplaceExtraFieldsRequest {
  extras: Record<string, string>;
}

export interface Preference {
  key: string;
  value: string;
  enabled?: boolean;
  [key: string]: unknown;
}

export interface PreferencesResponse {
  preferences: Preference[];
}

export interface SavePreferencesRequest {
  preferences: Preference[];
}

export interface UserLimits {
  dailyLimit?: CurrencyAmount;
  weeklyLimit?: CurrencyAmount;
  monthlyLimit?: CurrencyAmount;
  maxLoad?: CurrencyAmount;
  maxBalance?: CurrencyAmount;
  [key: string]: unknown;
}

export interface SelfExclusion {
  type?: string;
  durationInMonths?: number;
  reactivationDate?: EpochMillis;
  automaticReactivation?: boolean;
}

export interface SelfExclusionConfirmRequest {
  token: string;
  selfExclusionTypeCode?: string;
  durationInMonths?: number;
  automaticReactivation?: boolean;
  [key: string]: unknown;
}

export interface AutoControlQuestion {
  id: string | number;
  question?: string;
  answers?: unknown[];
  [key: string]: unknown;
}

export interface AutoControlAnswer {
  id: string | number;
  value: unknown;
  [key: string]: unknown;
}

export interface AgendaContact {
  name?: string;
  phoneNumber?: string;
  [key: string]: unknown;
}

export interface SaveAgendaRequest {
  contactos: string[] | AgendaContact[];
  deviceId: string;
}

export interface SponsorInfo {
  token?: string;
  url?: string;
  amount?: CurrencyAmount;
  [key: string]: unknown;
}

export interface SendSponsorSmsRequest {
  contactos: string[];
  deviceId: string;
  text?: string;
}

export interface IdentityVerificationStatus {
  status?: string;
  comment?: string;
  barcodeUsed?: string;
  [key: string]: unknown;
}

export interface ConfirmIdentityVerificationRequest {
  code: string;
  [key: string]: unknown;
}

export interface SuggestionRequest {
  message: string;
  versionCode: number | string;
  deviceType: string;
  suggestionType?: string;
  email?: string;
}

/* -------------------------------------------------------------------------- */
/* Sorteos / resultados                                                        */
/* -------------------------------------------------------------------------- */

export interface CombinationNumber {
  numero: string;
  numero2Digits: string;
  highlighted: boolean;
}

export interface DrawCombination {
  linea: string;
  juego: string;
  numerosCombinacion: CombinationNumber[];
  estrellas: CombinationNumber[];
  plenoAl15?: CombinationNumber;
}

export interface DrawPrize {
  category?: string;
  amount?: CurrencyAmount;
  winners?: number;
  [key: string]: unknown;
}

export interface Draw {
  id: number;
  externalId?: string;
  juego: string;
  juegoVersion?: number;
  fecha: EpochMillis;
  fechaCierre?: EpochMillis;
  premios?: DrawPrize[];
  precio?: CurrencyAmount;
  nombre?: string;
  numSorteo?: string;
  numJornada?: string;
  combinacion?: string;
  activityStartDate?: EpochMillis;
  activityEndDate?: EpochMillis;
  locked?: boolean;
  lockedAbonos?: boolean;
  fechaCierreTope?: EpochMillis;
  apuestasCierre?: number;
  allowFijos?: boolean;
  solicitudAdelantar?: boolean;
  combinacionObject?: DrawCombination;
  resultInfoLines?: unknown[];
  prizeInfos?: unknown[];
  premiosCalculados?: boolean;
  [key: string]: unknown;
}

export interface FinishedDrawsResponse {
  resultados: Draw[];
  total: number;
}

export interface BackendMatch {
  id: number;
  local: string;
  visitante: string;
  fecha: EpochMillis;
  signo?: string;
  marcador?: string;
  sorteoId: number;
  escudo1?: string;
  escudo2?: string;
  info1?: string;
  info2?: string;
  error?: boolean;
  externalId?: string;
  suspended?: boolean;
  resultadoAlDescanso?: boolean;
}

export interface MatchesResponse {
  partidos: BackendMatch[];
  extraInfo?: string[];
}

export interface GameMedia {
  [key: string]: unknown;
}

export interface Program {
  [key: string]: unknown;
}

/* -------------------------------------------------------------------------- */
/* Juego                                                                       */
/* -------------------------------------------------------------------------- */

export interface PlayTypeValue {
  type: string;
  typeId: string;
  value: unknown[];
}

export interface ShareSubscriptionDraw {
  [key: string]: unknown;
}

export interface PlayBet {
  amountBet: number;
  betId: string | number;
  searchAdminId?: string | number;
  subscriptionId?: string | number;
  subscriptionDraws?: ShareSubscriptionDraw[];
  types: PlayTypeValue[];
  boardId?: string | number;
}

export interface PlayCombination {
  aleatoria: boolean;
  juego: string;
  bets: PlayBet[];
  reintegro?: { numero: string };
  complementario?: { numero: string };
  apuestas?: Array<{ numeros: Array<{ numero: string }> }>;
}

export interface AbonoDay {
  day: string;
  hour: string;
  alias?: string | null;
  aliasToShow?: string | null;
}

export interface ShareConfig {
  [key: string]: unknown;
}

export interface ShipmentRequest {
  name?: string;
  addressLine?: string;
  city?: string;
  zipCode?: string;
  state?: string;
  phone?: string;
  [key: string]: unknown;
}

/** Payload común de `/users/play`, `/users/play/descriptor` y variantes de pre-reserva. */
export interface PlayRequest {
  almanaque: boolean;
  confirmacion?: boolean;
  abonarse: boolean;
  abonoDays?: AbonoDay[] | null;
  abonoMinJackpotAmount?: number;
  aleatorio: boolean;
  groupIdToSpoof?: string | number;
  juego: string;
  quickPlay?: boolean;
  sorteoIds: number[];
  numApuestas: number;
  totalApuesta: number;
  comparticion?: ShareConfig;
  extraInfo?: JsonObject;
  combinacionJugada: PlayCombination;
  insurance?: boolean;
  boothId?: number | string;
  envioCasaRequest?: ShipmentRequest;
  recogida?: boolean;
}

export interface LotteryDecimo {
  numero: string;
  adminId?: string | number | null;
  cantidad: number;
  almanaquePrecio?: number;
  reservation?: boolean;
  fijoLoteriaId?: string | number;
}

export interface RandomLottery {
  stock: number;
  adminId?: string | number;
}

export interface LotteryPlayRequest {
  almanaque: boolean;
  aleatorio: boolean;
  quickPlay?: boolean;
  abonarse: boolean;
  abonoDays?: AbonoDay[];
  abonoMinJackpotAmount?: number;
  groupIdToSpoof?: string | number;
  insurance?: boolean;
  comparticion?: ShareConfig;
  sorteoId: number;
  decimos: LotteryDecimo[];
  randomLoteria?: RandomLottery;
  envioCasaRequest?: ShipmentRequest;
  recogida?: boolean;
}

export interface PlayResult {
  status?: string;
  message?: string;
  object?: unknown;
  boleto?: unknown;
  ticket?: unknown;
  [key: string]: unknown;
}

export interface ValidatePlayRequest extends PlayRequest {}

export interface ScannerCodeRequest {
  code: string;
}

export interface LotterySearchType {
  typeId: string;
  value: string[];
}

export interface LotterySearchRequest {
  sorteoId: number;
  types: LotterySearchType[];
  firstResult?: number;
  minAmount?: number;
  maxResults?: number;
  avoidDuplicatedNumbers?: boolean;
}

export interface LotteryTicketBackend {
  numero?: string;
  numero2Digits?: string;
  highlighted?: boolean;
  adminId?: string | number;
  precio?: number;
  [key: string]: unknown;
}

export interface LotterySearchResponse {
  totalDecimosEnSorteo?: number;
  totalNumbers?: number;
  totalStockEnSorteo?: number;
  numbers?: LotteryTicketBackend[];
  decimos?: LotteryTicketBackend[];
  firstResult?: number;
}

export interface LotteryStock {
  stock: number;
  boothId?: number | string;
}

export interface LotterySubscriptionInfo {
  abonoDay: AbonoDay | null;
  amountManual: number;
  manual: boolean;
  precio: number;
  sorteos: number[];
}

export interface FreeLotteryRequest {
  sorteoId: number;
  transactionsIds: string[];
}

/* -------------------------------------------------------------------------- */
/* Boletos                                                                     */
/* -------------------------------------------------------------------------- */

export interface TicketOptions {
  showBigPrizeInstructions?: boolean;
  [key: string]: unknown;
}

export interface TicketShare {
  [key: string]: unknown;
}

export interface TicketSubscription {
  id?: number | string;
  [key: string]: unknown;
}

export interface TicketShipmentInfo {
  status?: string;
  [key: string]: unknown;
}

export interface TicketPendingPrize {
  [key: string]: unknown;
}

export interface TicketBet {
  validationDate?: EpochMillis;
  [key: string]: unknown;
}

/** Respuesta de `GET /users/boletos/{id}` y elemento de `GET /users/boletos/me`. */
export interface Ticket {
  id: number;
  descNombre?: string;
  customName?: string;
  hash?: string;
  fechaSorteo?: EpochMillis;
  fechaPedido?: EpochMillis;
  apuestaId?: number;
  fechasSorteo?: EpochMillis[];
  fechaArchivado?: EpochMillis;
  descPrecio?: string;
  precio?: CurrencyAmount;
  precioOriginal?: CurrencyAmount;
  precioPagado?: CurrencyAmount;
  premioProvisional?: CurrencyAmount;
  premio?: CurrencyAmount;
  prizeFormatted?: string;
  prizeFormattedLong?: string;
  imagenMini?: string;
  imagenMiniSVG?: string;
  imagenType?: string;
  imagenTypeSVG?: string;
  useDescriptorUI?: boolean;
  boletoHtml?: string;
  sorteo?: Draw;
  config?: TicketOptions;
  proof?: boolean;
  groupId?: number | string;
  status?: string;
  numParticipaciones?: number;
  numParticipantes?: number;
  invalidateWhenSorteoFinished?: boolean;
  compartidoPor?: TicketShare;
  comparticiones?: TicketShare[];
  abono?: TicketSubscription;
  penya?: Penya;
  imagenes?: string[];
  apuesta?: TicketBet;
  betInfo?: unknown;
  pendingPrizeAppInfo?: TicketPendingPrize;
  [key: string]: unknown;
}

export interface TicketsPage {
  boletos: Ticket[];
  total: number;
}

export interface TicketFiltersResponse {
  filters: Array<{ id: string; label?: string; [key: string]: unknown }>;
}

export interface EditTicketRequest {
  idBoleto: number;
  name: string;
  almanaquePrecio?: number;
}

export interface ShareTicketRequest {
  idBoleto: number;
  [key: string]: unknown;
}

export interface SubscribeTicketRequest {
  aleatorio: boolean;
  recompartir: boolean;
  abonoDays?: AbonoDay[];
  abonoMinJackpotAmount?: number;
  cantidad?: number;
}

export interface RepeatTicketRequest {
  idBoleto: number;
  sorteoIds: number[];
  aleatoria?: boolean;
  recompartir?: boolean;
}

export interface TicketProofRequest {
  [key: string]: unknown;
}

export interface ShipmentPrice {
  price?: CurrencyAmount;
  [key: string]: unknown;
}

export interface CollectionRequest {
  [key: string]: unknown;
}

export interface PrizeStatus {
  status?: string;
  [key: string]: unknown;
}

/* -------------------------------------------------------------------------- */
/* Cartera, movimientos y pagos                                                */
/* -------------------------------------------------------------------------- */

export interface MoneyMovement {
  id?: number | string;
  type?: string;
  amount?: CurrencyAmount;
  date?: EpochMillis;
  description?: string;
  status?: string;
  balance?: CurrencyAmount;
  [key: string]: unknown;
}

export interface MoneyMovementsResponse {
  movimientos: MoneyMovement[];
  total: number;
}

export interface WithdrawRequest {
  cuenta: string;
  cantidad: number;
  persist: boolean;
  useOtp?: boolean;
  [key: string]: unknown;
}

export interface WithdrawV2Request {
  amount?: CurrencyAmount;
  account?: string;
  iban?: string;
  saveAccount?: boolean;
  useOtp?: boolean;
  [key: string]: unknown;
}

export interface WithdrawInfo {
  [key: string]: unknown;
}

export interface CreditCardRequest {
  amount: CurrencyAmount;
  saveCardAlias?: string;
  paymentMethodId?: string;
  token?: string;
  security?: string;
  favorite?: boolean;
}

export interface SaveCardRequest {
  saveCardAlias: string;
  favorite?: boolean;
}

export interface ExternalCreditRequest {
  paymentMethod: 'BANK_TRANSFER_REDIRECT' | 'PHONE' | string;
  amount: CurrencyAmount;
  redirectUrlAfter?: string;
  phoneNumber?: string;
  extraData?: {
    bankCode?: string;
    documentType?: string;
    documentNumber?: string;
    [key: string]: unknown;
  };
}

export interface NativeCreditRequest {
  [key: string]: unknown;
}

export interface AutoCreditRequest {
  autoCreditMultiple: number;
}

export interface PaymentMethod {
  id: string | number;
  type?: string;
  alias?: string;
  favorite?: boolean;
  [key: string]: unknown;
}

export interface PaymentMethodLoadRequest {
  [key: string]: unknown;
}

export interface PaymentMethodWidgetRequest {
  id: string;
  [key: string]: unknown;
}

export interface SummaryResponse {
  [key: string]: unknown;
}

export interface PspResponse {
  [key: string]: unknown;
}

/* -------------------------------------------------------------------------- */
/* Grupos                                                                      */
/* -------------------------------------------------------------------------- */

export interface Group {
  id: string | number;
  name?: string;
  code?: string;
  picture?: string;
  balance?: CurrencyAmount;
  role?: string;
  members?: GroupMember[];
  [key: string]: unknown;
}

export interface GroupMember {
  id?: number | string;
  name?: string;
  picture?: string;
  role?: string;
  [key: string]: unknown;
}

export interface GroupCreateRequest {
  name: string;
  [key: string]: unknown;
}

export interface GroupUpdateRequest {
  [key: string]: unknown;
}

export interface GroupJoinRequest {
  code: string;
}

export interface GroupMemberInvite {
  userIds?: Array<number | string>;
  [key: string]: unknown;
}

export interface GroupMoneyRequest {
  amount: CurrencyAmount;
  userIds?: Array<number | string>;
}

export interface GroupTransferRequest {
  amount: CurrencyAmount;
  userId: number | string;
}

export interface GroupMessageRequest {
  message: string;
  [key: string]: unknown;
}

export interface GroupMoneyActivity {
  id?: number | string;
  type?: string;
  amount?: CurrencyAmount;
  date?: EpochMillis;
  [key: string]: unknown;
}

/* -------------------------------------------------------------------------- */
/* Peñas / clubes / lotería de empresa                                         */
/* -------------------------------------------------------------------------- */

export interface Penya {
  id: number | string;
  name?: string;
  code?: string;
  image?: string;
  raffleId?: number;
  gameId?: string;
  entryMin?: number;
  entryPrice?: CurrencyAmount;
  type?: string;
  [key: string]: unknown;
}

export interface ClubPlayRequest {
  participaciones: Array<{
    juego: string;
    abonarse: boolean;
    penyaId: number | string;
    groupIdToSpoof?: string | number;
    numParticipaciones?: number;
  }>;
}

export interface JoinPrivateClubRequest {
  promo: string;
}

export interface CompanyClubRequest {
  [key: string]: unknown;
}

export interface ClubCreationInfo {
  [key: string]: unknown;
}

/* -------------------------------------------------------------------------- */
/* KYC                                                                         */
/* -------------------------------------------------------------------------- */

export interface KycStatus {
  status?: string;
  comment?: string;
  barcodeUsed?: string;
  [key: string]: unknown;
}

export interface KycScannerParseRequest {
  [key: string]: unknown;
}

export interface KycScannerParseResponse {
  message?: string;
  object?: unknown;
  [key: string]: unknown;
}

/* -------------------------------------------------------------------------- */
/* Noticias                                                                    */
/* -------------------------------------------------------------------------- */

export interface NewsBackend {
  id: number | string;
  title: string;
  content?: string;
  comments?: number;
  views?: number;
  date?: EpochMillis;
  mainImg?: string;
  img?: string;
  urlVideo?: string;
  url?: string;
  layout?: string;
  category?: string;
  videoVertical?: boolean;
  [key: string]: unknown;
}

export interface NewsItem {
  id: number | string;
  headLine: string;
  content?: string;
  comments?: number;
  views?: number;
  date?: EpochMillis;
  image?: string;
  squareImage?: string;
  videoUrl?: string;
  articleUrl?: string;
  layout: 'normal' | 'vertical' | string;
  type: string;
  isVerticalVideo: boolean;
}

export interface NewsResponse {
  news: NewsBackend[] | NewsItem[];
  total?: number;
  totalUnread?: number;
}

/* -------------------------------------------------------------------------- */
/* Utilidades                                                                  */
/* -------------------------------------------------------------------------- */

export interface GeolocationContext {
  coords: {
    latitude: number;
    longitude: number;
    accuracy: number;
  };
  timestamp: number;
}

export interface DeviceContext {
  deviceId?: string;
  androidRegistrationId?: string;
  deviceType?: string;
  deviceDesc?: string;
  osVersion?: string;
  versionCode?: string | number;
  mode?: 'mobile' | 'desktop';
}

export interface RequestOptions {
  signal?: AbortSignal;
  headers?: Record<string, string>;
  query?: Record<string, QueryValue>;
  timeoutMs?: number;
  retry?: boolean | number;
  /** Evita inyectar Authorization (login, refresh, endpoints públicos). */
  skipAuth?: boolean;
  /** Evita el refresco proactivo y el reintento tras 401. */
  skipRefresh?: boolean;
  responseType?: 'json' | 'text' | 'blob' | 'arrayBuffer';
  body?: unknown;
  form?: Record<string, string | number | boolean | undefined>;
  multipart?: FormData;
}

export type QueryValue =
  | string
  | number
  | boolean
  | null
  | undefined
  | Array<string | number | boolean>;
