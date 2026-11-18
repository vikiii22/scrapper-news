# Ejecución única de la jornada de quiniela — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un comando obtiene la jornada vigente de Eduardo Losilla, enriquece los 15 partidos con datos reales y escribe un informe con dos boletos de 24 apuestas y su garantía.

**Architecture:** Nuevo paquete `soccer_predictor/quiniela_sources/` con un adaptador por fuente y caché en disco; `boleto.py` genera la reducción de 24 columnas por código de cobertura; `report.py` renderiza Markdown/JSON; `jornada.py` orquesta y expone el CLI. Se reutilizan `predict()`, `resolve_team`, `pleno_suggestion` y los scrapers existentes.

**Tech Stack:** Python 3.9+, requests, BeautifulSoup4, lxml, numpy (ya instalados). Tests con `unittest` (stdlib). Sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-11-18-jornada-unica-design.md`

## Global Constraints

- Solo fuentes gratuitas y sin clave, limitadas a los dominios del spec.
- Nunca inventar datos: una fuente caída se marca `n/d` y el informe se genera igual.
- 24 apuestas por boleto = 18 € (0,75 €/apuesta), pleno incluido en la columna.
- 3 dobles + 3 triples + 8 fijos por boleto, siempre 14 partidos.
- Windows: `pathlib`, sin comandos de shell dentro del código.
- `predict()` se llama en serie; los adaptadores de datos pueden ir en paralelo (máx. 4 hilos).
- No reescribir `prediction_engine.py` ni cambiar el modelo Poisson.
- No guardar en BBDD salvo `--save`; un fallo de Mongo no puede impedir el informe.

## Review Focus

1. **CSV de Losilla sin sección `lae`** (jornada recién abierta): debe usar `real` como referencia, marcar `lae: null` y no imprimir ceros. Test en Tarea 1.
2. **Equipos femeninos**: Eibar (F), Granada (F), Tenerife (F), Madrid CFF (F) deben resolverse solo contra `esp.w.1` y no mezclar datos masculinos. Test en Tareas 1 y 5.
3. **Fuente caída** (Transfermarkt, Understat, ClubElo, mercados): informe generado, columna `n/d`, sin excepción. Test en Tarea 2.
4. **Pleno del CSV en dos filas** (15 + fila en blanco) con 4 porcentajes por equipo: no debe desplazar `%2` ni perder `M`. Test en Tarea 1.
5. **Jornada ya empezada o cerrada**: no emitir un boleto "jugable" en silencio; avisar y exigir `--jornada`/`--force`. Test en Tarea 5.

---

### Task 1: Fuente Losilla (CSV + HTML) y caché

**Files:**
- Create: `soccer_predictor/quiniela_sources/__init__.py`
- Create: `soccer_predictor/quiniela_sources/cache.py`
- Create: `soccer_predictor/quiniela_sources/losilla.py`
- Create: `tests/test_losilla.py`
- Create: `tests/fixtures/jornada23.csv`
- Create: `tests/fixtures/jornada23_home.html`

**Interfaces:**
- Consumes: `soccer_predictor.quiniela.parse_quiniela_html`, `resolve_team`.
- Produces:
  - `Cache(root: Path, max_age_hours: float = 6.0)`, métodos `get(key: str) -> Any | None` y `set(key: str, value: Any) -> None`.
  - `parse_csv(text: str) -> dict[str, list[dict]]` con claves `tecnicos`, `quinielista`, `lae`, `real`.
  - `parse_boleto(html: str) -> dict` con `jornada`, `close`, `matches` (15), usando horarios/equipos del HTML.
  - `fetch_jornada(jornada: int | None = None, html: str | None = None, cache: Cache | None = None, timeout: int = 20) -> dict` con `{jornada, season, close, fetched_at, matches}`.
  - Cada `match`: `n, home, away, home_raw, away_raw, day, hour, is_women, is_pleno, percentages{jugados,lae,probables,tecnicos}, lae, probables, pleno`.

- [ ] **Step 1: Capturar fixtures reales de la jornada 23**

```bash
python - <<'PY'
import pathlib, requests
h={"User-Agent":"Mozilla/5.0"}
d=pathlib.Path("tests/fixtures"); d.mkdir(parents=True, exist_ok=True)
csv=requests.get("https://api.eduardolosilla.es/analisisSigno?num_jornada=23&num_temporada=2027&csv=true",headers=h,timeout=30)
home=requests.get("https://www.eduardolosilla.es/",headers=h,timeout=30)
d.joinpath("jornada23.csv").write_bytes(csv.content)
d.joinpath("jornada23_home.html").write_text(home.text,encoding="utf-8")
print(csv.status_code, home.status_code, len(csv.content), len(home.text))
PY
```

Esperado: `200 200` y dos ficheros no vacíos.

- [ ] **Step 2: Escribir los tests que fallan**

En `tests/test_losilla.py`:

```python
import pathlib, unittest
from soccer_predictor.quiniela_sources import losilla
FIX = pathlib.Path(__file__).parent / "fixtures"

class TestLosilla(unittest.TestCase):
    def setUp(self):
        self.csv = (FIX/"jornada23.csv").read_text(encoding="latin-1")
        self.html = (FIX/"jornada23_home.html").read_text(encoding="utf-8")

    def test_parse_csv_sections_and_values(self):
        sec = losilla.parse_csv(self.csv)
        self.assertEqual(set(sec), {"tecnicos","quinielista","lae","real"})
        m1 = sec["real"][0]
        self.assertEqual(m1["n"], 1)
        self.assertEqual(m1["percentages"]["1"], 43.0)
        self.assertEqual(m1["percentages"]["X"], 29.0)
        self.assertEqual(m1["percentages"]["2"], 28.0)
        self.assertEqual(sec["quinielista"][0]["percentages"]["1"], 47.0)
        self.assertIsNone(sec["lae"][0]["lae"])

    def test_pleno_two_rows_and_four_columns(self):
        sec = losilla.parse_csv(self.csv)
        p = sec["real"][14]["pleno"]
        self.assertEqual(p["home"], {"0":29.0,"1":36.0,"2":22.0,"M":13.0})
        self.assertEqual(p["away"], {"0":23.0,"1":34.0,"2":25.0,"M":18.0})

    def test_parse_boleto_schedule_and_flags(self):
        b = losilla.parse_boleto(self.html)
        self.assertEqual(b["jornada"], 23)
        self.assertEqual(len(b["matches"]), 15)
        self.assertEqual(b["matches"][0]["day"], "SAB")
        self.assertEqual(b["matches"][0]["hour"], "14:00")
        self.assertFalse(b["matches"][0]["is_women"])
        self.assertTrue(b["matches"][10]["is_women"])
        self.assertTrue(b["matches"][14]["is_pleno"])

    def test_fetch_merges_and_falls_back_to_real(self):
        def fake_get(url, params=None, timeout=20):
            return self.csv if "analisisSigno" in url else self.html
        original = losilla._get_text
        losilla._get_text = fake_get
        try:
            j = losilla.fetch_jornada(jornada=23)
        finally:
            losilla._get_text = original
        self.assertEqual(j["jornada"], 23)
        self.assertEqual(j["matches"][0]["home"], "Alaves")
        self.assertEqual(j["matches"][0]["percentages"]["probables"]["1"], 43.0)
        self.assertIsNone(j["matches"][0]["lae"])
        self.assertTrue(j["matches"][10]["is_women"])

    def test_cache_roundtrip(self):
        import tempfile
        from soccer_predictor.quiniela_sources.cache import Cache
        with tempfile.TemporaryDirectory() as d:
            c = Cache(pathlib.Path(d), max_age_hours=6)
            self.assertIsNone(c.get("x"))
            c.set("x", {"a": 1})
            self.assertEqual(c.get("x"), {"a": 1})
```

- [ ] **Step 3: Ejecutar y ver fallar**

Run: `python -m unittest discover -s tests -p "test_losilla.py" -v`
Expected: `ModuleNotFoundError: No module named 'soccer_predictor.quiniela_sources'`.

- [ ] **Step 4: Implementar `cache.py`**

`Cache.__init__` crea `root`; `set` escribe `root/<sha1(key)>.json` con `{"key","saved_at","value"}`; `get` devuelve `None` si no existe, si el JSON falla o si `saved_at` supera `max_age_hours`. Nunca lanza.

- [ ] **Step 5: Implementar `losilla.py`**

- `_get_text(url, params=None, timeout=20)` devuelve `str` o lanza `requests.RequestException` (una sola función, para poder monkeypatchearla).
- `_SEASON(today)` → `today.year + 1` si `today.month >= 7`, si no `today.year`.
- `parse_csv`: decodifica con `latin-1`, parte por líneas, detecta cabeceras de sección (`tecnicos`, `quinielista`, `lae`, `real`), lee filas `n;equipos;Base;Probable;Posible;Difícil;Bomba;%1;%X;%2`. Para el 15 acumula la fila siguiente (equipo vacío) como visitante. Convierte números con `float` tolerando `''`. Devuelve por sección una lista de 15 dicts con `n, equipos_raw, base, probable, posible, dificil, bomba, percentages, lae, pleno`.
  - En secciones sin fila de pleno separada (`lae` vacía), `pleno=None`.
  - `lae` de cada partido: `percentages` si la sección es `lae`, si no `None`.
- `parse_boleto`: usa `parse_quiniela_html(html)` para `jornada` y `matches`; añade `close` con regex sobre el texto `CIERRE ...` si aparece; devuelve también `matches` con `is_women`/`is_pleno` ya calculados por el parser existente.
- `fetch_jornada`:
  1. Si `jornada is None`, descarga la portada y usa `parse_boleto` para el número.
  2. Descarga CSV con `num_jornada` y `num_temporada=_SEASON(date.today())`.
  3. Mezcla por `n`: horarios del HTML, porcentajes del CSV. `jugados=quinielista`, `lae=lae` (o `None`), `probables=real`, `tecnicos=tecnicos`.
  4. Usa `resolve_team` sobre `home_raw/away_raw`.
  5. `season` = `_SEASON`, `fetched_at` ISO UTC.
  6. Cachea el resultado completo con clave `f"losilla_{jornada}_{season}"`.
- Si el CSV no trae las 15 filas y `html` no se pasa, lanza `ValueError("No se pudo leer la jornada")`.

- [ ] **Step 6: Ejecutar y ver pasar**

Run: `python -m unittest discover -s tests -p "test_losilla.py" -v`
Expected: 5 tests OK.

- [ ] **Step 7: Commit**

```bash
git add soccer_predictor/quiniela_sources tests
git commit -m "feat(quiniela): fuente Losilla con CSV, HTML y cache"
```

---

### Task 2: Adaptadores de contexto (forma, xG, bajas, noticias, mercados)

**Files:**
- Create: `soccer_predictor/quiniela_sources/football_data.py`
- Create: `soccer_predictor/quiniela_sources/injuries.py`
- Create: `soccer_predictor/quiniela_sources/news.py`
- Create: `soccer_predictor/quiniela_sources/understat.py`
- Create: `soccer_predictor/quiniela_sources/clubelo.py`
- Create: `soccer_predictor/quiniela_sources/markets.py`
- Create: `tests/test_sources.py`
- Create: `tests/fixtures/sp1_2627.csv`
- Create: `tests/fixtures/transfermarkt_injuries.html`
- Create: `tests/fixtures/gnews_sevilla_betis.xml`

**Interfaces:**
- `football_data.load_league(code: str, cache: Cache | None = None, timeout: int = 20) -> dict` → `{ok, rows, error, source_url}`. `code` en `{"SP1","SP2"}`.
- `football_data.parse_csv(text: str) -> list[dict]` → filas normalizadas con `Date/HomeTeam/AwayTeam/FTHG/FTAG/HxG/AxG` y cuotas.
- `football_data.team_form(rows: list[dict], team: str, n: int = 5) -> dict` → `{recent, gf, ga, xg, xga, ppg, matches}`; `recent` con `W/D/L` del más antiguo al más reciente.
- `football_data.closing_odds(rows: list[dict], home: str, away: str) -> dict | None` → `{1,X,2}` normalizado a 100.
- `injuries.fetch_injuries(team: str, women: bool = False, cache=None, timeout=12) -> dict` → `{ok, players, count, error, source_url}`; `players[i]={name,position,issue,since,until,matches_out}`.
- `injuries.parse_injuries_html(html: str) -> list[dict]` → lista de jugadores con el mismo formato.
- `news.headlines(query: str, limit: int = 3, cache=None, timeout=10) -> dict` → `{ok, items:[{title,date,source}], error}`.
- `news.parse_rss(xml: str, limit: int = 3) -> list[dict]` → items con `title,date,source`.
- `understat.league_xg(league: str = "La_liga", cache=None) -> dict` → `{ok, teams, error}`; best-effort, `ok=False` si la página no trae `teamsData`.
- `clubelo.elo(team: str, cache=None) -> dict` → `{ok, elo, error}`.
- `markets.outright_context(cache=None) -> dict` → `{ok, markets, error}`; solo contexto, nunca por partido.

- [ ] **Step 1: Capturar fixtures**

```bash
python - <<'PY'
import pathlib, requests
h={"User-Agent":"Mozilla/5.0"}; d=pathlib.Path("tests/fixtures")
fd=requests.get("https://www.football-data.co.uk/mmz4281/2627/SP1.csv",headers=h,timeout=30)
inj=requests.get("https://www.transfermarkt.es/fc-sevilla/sperrenundverletzungen/verein/368",headers=h,timeout=30)
news=requests.get("https://news.google.com/rss/search?q=Sevilla+Betis&hl=es&gl=ES&ceid=ES:es",headers=h,timeout=30)
for name,data in [("sp1_2627.csv",fd.content),("transfermarkt_injuries.html",inj.content),("gnews_sevilla_betis.xml",news.content)]:
    d.joinpath(name).write_bytes(data); print(name,len(data))
PY
```

- [ ] **Step 2: Escribir tests que fallan**

En `tests/test_sources.py`:

```python
import pathlib, unittest
from soccer_predictor.quiniela_sources import football_data, injuries, news
FIX = pathlib.Path(__file__).parent/"fixtures"

class TestSources(unittest.TestCase):
    def test_team_form_last_five_and_xg(self):
        rows = football_data.parse_csv((FIX/"sp1_2627.csv").read_text(encoding="utf-8-sig"))
        f = football_data.team_form(rows, "Sevilla", n=5)
        self.assertEqual(len(f["matches"]), 5)
        self.assertEqual(len(f["recent"]), 5)
        self.assertTrue(set(f["recent"]) <= set("WDL"))
        self.assertGreaterEqual(f["xg"], 0)

    def test_closing_odds_normalized(self):
        rows = football_data.parse_csv((FIX/"sp1_2627.csv").read_text(encoding="utf-8-sig"))
        odds = football_data.closing_odds(rows, "Sevilla", "Real Betis")
        if odds is not None:
            self.assertAlmostEqual(sum(odds.values()), 100.0, places=0)

    def test_injuries_parse(self):
        html = (FIX/"transfermarkt_injuries.html").read_text(encoding="utf-8", errors="ignore")
        r = injuries.parse_injuries_html(html)
        self.assertGreaterEqual(len(r), 1)
        self.assertIn("name", r[0])
        self.assertIn("issue", r[0])

    def test_injuries_skip_women(self):
        r = injuries.fetch_injuries("Eibar", women=True)
        self.assertFalse(r["ok"])
        self.assertEqual(r["count"], 0)

    def test_news_parse(self):
        xml = (FIX/"gnews_sevilla_betis.xml").read_text(encoding="utf-8", errors="ignore")
        items = news.parse_rss(xml, limit=3)
        self.assertEqual(len(items), 3)
        self.assertTrue(items[0]["title"])

    def test_adapters_never_raise(self):
        def boom(*a, **k): raise RuntimeError("sin red")
        original = football_data._get_text
        football_data._get_text = boom
        try:
            r = football_data.load_league("SP1")
            self.assertFalse(r["ok"])
            self.assertEqual(r["rows"], [])
        finally:
            football_data._get_text = original
        original = injuries._get_text
        injuries._get_text = boom
        try:
            r = injuries.fetch_injuries("Sevilla")
            self.assertFalse(r["ok"])
            self.assertEqual(r["count"], 0)
        finally:
            injuries._get_text = original
```

- [ ] **Step 3: Ejecutar y ver fallar**

Run: `python -m unittest discover -s tests -p "test_sources.py" -v`
Expected: `ModuleNotFoundError` de los módulos.

- [ ] **Step 4: Implementar `football_data.py`**

- `_get_text` igual patrón que Losilla.
- `parse_csv(text) -> list[dict]` con `csv.DictReader`; conserva columnas, convierte a float/int cuando se pueda; `Date` a ISO.
- `load_league` descarga `https://www.football-data.co.uk/mmz4281/{season}/{code}.csv` con `season = f"{y%100:02d}{(y+1)%100:02d}"`, `y = year if month >= 7 else year-1`; cachea 24 h.
- `team_form`: filtra filas con `HomeTeam`/`AwayTeam` que casen con `team` usando `difflib.SequenceMatcher` ≥ 0.72; ordena por fecha; toma las últimas `n`; calcula `gf/ga`, `xg/xga` sumando `HxG/AxG` (0 si no hay), `ppg`, y `recent` en orden cronológico.
- `closing_odds`: busca la fila `home` vs `away`; usa la primera cuota disponible de `B365H/D/A`, `PSCH/D/A`, `BFDH/D/A`; normaliza a 100; `None` si no hay.

- [ ] **Step 5: Implementar `injuries.py`**

- `parse_injuries_html(html) -> list[dict]`: tabla `table.items`; por fila con enlace de jugador; extrae nombre, posición, diagnóstico, desde, hasta, partidos (`matches_out` int si se puede).
- `resolve_team_url(team)`: GET `https://www.transfermarkt.es/schnellsuche/ergebnis/schnellsuche?query={quote(team)}`; de los enlaces `a[href*='/verein/']`, elige el que mejor case con `team` por `SequenceMatcher` (≥ 0.6); devuelve URL base `.../startseite/verein/<id>`.
- `fetch_injuries`: si `women` → `{ok:False, players:[], count:0, error:"sin cobertura femenina"}` sin red. Si no, resuelve URL, cambia `startseite` por `sperrenundverletzungen`, parsea y cachea 12 h. Cualquier excepción → `ok:False`.

- [ ] **Step 6: Implementar `news.py`, `understat.py`, `clubelo.py`, `markets.py`**

- `news.parse_rss(xml, limit)`: `xml.etree.ElementTree`; `item/title`, `pubDate`, `source`; devuelve los `limit` primeros.
- `news.headlines`: URL `https://news.google.com/rss/search?q={quote(query)}&hl=es&gl=ES&ceid=ES:es`; cachea 6 h.
- `understat.league_xg`: GET `https://understat.com/league/{league}`; busca `teamsData`; si no está, `ok=False`. Cachea 24 h.
- `clubelo.elo`: GET `http://api.clubelo.com/{team}`; primera línea con `Elo`; `ok=False` en 502/timeout. Cachea 24 h.
- `markets.outright_context`: GET `https://gamma-api.polymarket.com/events?limit=50&closed=false`; filtra títulos con `La Liga`/`Serie A`; devuelve `[{question, probability}]` con `outcomePrices` si existe. `ok=False` si no hay. Cachea 24 h. No se usa por partido.

- [ ] **Step 7: Ejecutar y ver pasar**

Run: `python -m unittest discover -s tests -p "test_sources.py" -v`
Expected: 6 tests OK.

- [ ] **Step 8: Commit**

```bash
git add soccer_predictor/quiniela_sources tests
git commit -m "feat(quiniela): adaptadores de forma, xG, bajas, noticias y mercados"
```

---

### Task 3: Motor de boletos (selección + reducción de 24)

**Files:**
- Create: `soccer_predictor/boleto.py`
- Create: `tests/test_boleto.py`

**Interfaces:**
- `covering_code(sizes: list[int]) -> list[tuple[int, ...]]`: 24 tuplas deterministas que cubren todas las combinaciones con distancia ≤ 1.
- `select_signs(matches: list[dict], profile: str = "rentable") -> dict[int, list[str]]`: 14 entradas, exactamente 3 con 3 signos, 3 con 2 y 8 con 1.
- `build_boleto(matches: list[dict], profile: str) -> dict`: `{name, profile, cost_eur, bets, signs, multiples, columns, pleno, guarantee}`.
- `pleno_variants(lam_home: float, lam_away: float) -> dict`: `{seguro: {"home","away"}, bota: {"home","away"}}`.
- Consumes: `soccer_predictor.quiniela.pleno_suggestion`, `prediction_engine.poisson_pmf`.

- [ ] **Step 1: Escribir tests que fallan**

```python
import itertools, unittest
from soccer_predictor import boleto

def _entry(n=1, p1=50, px=25, p2=25, prob=None, modelo=None):
    return {"n": n, "modelo": modelo or {"1":p1,"X":px,"2":p2},
            "valor": {"1":0,"X":0,"2":0},
            "percentages": {"probables": prob or {"1":p1,"X":px,"2":p2}},
            "pleno": None}

class TestCovering(unittest.TestCase):
    def test_24_columns_cover_all_216_with_radius_one(self):
        pts = list(itertools.product(*[range(s) for s in (2,2,2,3,3,3)]))
        code = boleto.covering_code([2,2,2,3,3,3])
        self.assertEqual(len(code), 24)
        self.assertEqual(len(set(code)), 24)
        for p in pts:
            self.assertTrue(any(sum(a!=b for a,b in zip(p,c)) <= 1 for c in code))

    def test_signs_shape_and_determinism(self):
        ms = [_entry(i, *[(60,20,20),(40,30,30),(50,30,20),(30,40,30),(70,15,15),
                          (45,25,30),(35,35,30),(55,25,20),(40,35,25),(65,20,15),
                          (20,30,50),(80,12,8),(50,25,25),(45,30,25)][i-1]) for i in range(1,15)]
        s = boleto.select_signs(ms, "rentable")
        self.assertEqual(len(s), 14)
        self.assertEqual(sum(1 for v in s.values() if len(v)==3), 3)
        self.assertEqual(sum(1 for v in s.values() if len(v)==2), 3)
        self.assertEqual(sum(1 for v in s.values() if len(v)==1), 8)
        self.assertEqual(s, boleto.select_signs(ms, "rentable"))

    def test_boleto_cost_columns_and_guarantee(self):
        ms = [_entry(i, *[(60,20,20),(40,30,30),(50,30,20),(30,40,30),(70,15,15),
                          (45,25,30),(35,35,30),(55,25,20),(40,35,25),(65,20,15),
                          (20,30,50),(80,12,8),(50,25,25),(45,30,25)][i-1]) for i in range(1,15)]
        b = boleto.build_boleto(ms, "rentable")
        self.assertEqual(b["bets"], 24)
        self.assertEqual(b["cost_eur"], 18.0)
        self.assertEqual(len(b["columns"]), 24)
        self.assertTrue(all(len(c) == 14 for c in b["columns"]))
        self.assertIn("13", b["guarantee"]["text"])
        self.assertAlmostEqual(b["guarantee"]["p14"], 11.1, places=1)

    def test_profiles_differ(self):
        ms = [_entry(i, *[(60,20,20),(40,30,30),(50,30,20),(30,40,30),(70,15,15),
                          (45,25,30),(35,35,30),(55,25,20),(40,35,25),(65,20,15),
                          (20,30,50),(80,12,8),(50,25,25),(45,30,25)][i-1]) for i in range(1,15)]
        b1 = boleto.build_boleto(ms, "rentable")
        b2 = boleto.build_boleto(ms, "seguro")
        self.assertNotEqual(b1["signs"], b2["signs"])

    def test_pleno_variants(self):
        p = boleto.pleno_variants(1.8, 1.1)
        self.assertIn(p["seguro"]["home"], "012M")
        self.assertIn(p["bota"]["away"], "012M")
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `python -m unittest discover -s tests -p "test_boleto.py" -v`
Expected: `ModuleNotFoundError: soccer_predictor.boleto`.

- [ ] **Step 3: Implementar `covering_code`**

Greedy determinista: universo `itertools.product(range(s) for s in sizes)`; mientras queden puntos, elegir el punto con más puntos no cubiertos a distancia ≤ 1 (empate → orden lexicográfico); añadirlo; repetir. Debe dar exactamente 24 para `[2,2,2,3,3,3]`; si no, lanzar `ValueError`.

- [ ] **Step 4: Implementar `select_signs`**

1. Normaliza `p = {s: modelo[s]/100}`; `ref = percentages.lae or percentages.probables`.
2. Puntúa cada partido: `conf = max(p)`, `x = p["X"]`, `entropy = -Σ p·ln p`, `value = max(valor.values())`.
3. Elige 3 triples: entre todos menos el de mayor `conf`, ordena por `(x >= 0.29, x + 0.35*entropy + 0.01*max(0,value))` desc; toma 3.
4. Elige 3 dobles entre los restantes por `(1-conf) + 0.5*x + 0.01*max(0,value)` desc.
5. Patrón del doble: ordena los signos por probabilidad; si `X` es el 2.º → `[top, "X"]`; si no → `["1","2"]`, salvo que `p["1"] < p["2"]` → `["X","2"]` si X es 2.º (ya cubierto), si no `["1","2"]` igual.
6. Fijos: `modelo` top. En perfil `seguro`, usa `ref` top cuando `ref[top] >= 75` y el modelo no coincide; en `rentable`, usa `modelo` top.
7. Si el reparto no da 3/3/8 por empates, reasigna el partido de menor confianza al grupo que falte.
8. Devuelve `{n: ["1",...]}` con signos en orden `1,X,2`.

- [ ] **Step 5: Implementar `build_boleto`**

- `sizes = [len(v) for v in signs.values() if len(v)>1]` en el orden de los múltiples; `code = covering_code(sizes)`.
- Expande: para cada una de las 24 tuplas, cada partido fijo lleva su signo y cada múltiple el signo `signs[n][idx]`.
- `pleno`: usa `pleno_suggestion(lam_home, lam_away)` si el partido 15 trae `expected_goals`; si no, `{"home":"1","away":"1"}`.
- `guarantee`: `{"text": "13 si los 8 fijos entran; 14 al 24/216", "p14": 11.1, "bets": 24, "fixed": 8}`.
- `cost_eur = 24 * 0.75`.

- [ ] **Step 6: Implementar `pleno_variants`**

`seguro` = `pleno_suggestion`. `bota` = la combinación `(h,a)` con `h+a >= 3` de mayor probabilidad conjunta (Poisson independiente, `k in 0..2` y `M=3+`); si no hay, `{"home":"2","away":"1"}`.

- [ ] **Step 7: Ejecutar y ver pasar**

Run: `python -m unittest discover -s tests -p "test_boleto.py" -v`
Expected: 5 tests OK.

- [ ] **Step 8: Commit**

```bash
git add soccer_predictor/boleto.py tests/test_boleto.py
git commit -m "feat(quiniela): boletos de 24 apuestas con cobertura 13 verificada"
```

---

### Task 4: Informe Markdown + JSON

**Files:**
- Create: `soccer_predictor/report.py`
- Create: `tests/test_report.py`
- Create: `tests/fixtures/entry_min.json`

**Interfaces:**
- `render_markdown(entry: dict) -> str`
- `write_report(entry: dict, output_dir: Path = Path("output")) -> tuple[Path, Path]`
- Consumes: la estructura de `entry` de Tarea 5 y los boletos de Tarea 3.

- [ ] **Step 1: Escribir tests que fallan**

```python
import json, pathlib, tempfile, unittest
from soccer_predictor import report
FIX = pathlib.Path(__file__).parent/"fixtures"

class TestReport(unittest.TestCase):
    def test_markdown_has_required_sections(self):
        e = json.loads((FIX/"entry_min.json").read_text(encoding="utf-8"))
        md = report.render_markdown(e)
        for s in ["JORNADA 23", "Boleto rentable", "Boleto conservador",
                  "Pleno al 15", "Garantía", "n/d", "Valor"]:
            self.assertIn(s, md)

    def test_write_report_creates_both_files(self):
        e = json.loads((FIX/"entry_min.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as d:
            md, js = report.write_report(e, pathlib.Path(d))
            self.assertTrue(md.exists() and js.exists())
            self.assertEqual(json.loads(js.read_text(encoding="utf-8"))["jornada"], 23)
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `python -m unittest discover -s tests -p "test_report.py" -v`
Expected: `ModuleNotFoundError: soccer_predictor.report`.

- [ ] **Step 3: Crear `tests/fixtures/entry_min.json`**

Un entry de **15 partidos** (n=1..15, el 15 con `is_pleno`) con todos los campos de la Tarea 5 (`jornada`, `close`, `sources`, `matches` con `modelo`, `valor`, `percentages`, `context`, `boleto_rentable`, `boleto_conservador`). Al menos un partido debe tener una fuente a `None` para que el test compruebe `n/d`. Sirve de contrato; el implementador lo rellena con valores reales de la jornada 23.

- [ ] **Step 4: Implementar `render_markdown`**

Secciones exactas:
1. `# JORNADA {n} — {close}` y tabla de estado de fuentes (`fuente | estado | nota`).
2. `## Partidos` tabla: `# | Local | Visitante | Hora | %Jug | %LAE | %Prob | Modelo 1X2 | Valor | Forma | xG | Elo | Bajas | Pick`.
3. `## Lectura` una línea por partido con `pick`, `value_pick`, `low_confidence` y la ausencia de datos como `n/d`.
4. `## Pleno al 15` con las 4 probabilidades por equipo y la recomendación.
5. `## Boleto rentable` y `## Boleto conservador`: tabla de signos, múltiples, 24 columnas en bloque `code`, pleno y `Garantía`.
6. `## Riesgos` lista de partidos con `low_confidence` o sin datos.
7. Pie: `Generado ... Fuentes: ...`.

- [ ] **Step 5: Implementar `write_report`**

Crea `output/`; nombre `jornada_{n}_{YYYY-MM-DD}.md` y `.json`; escribe UTF-8; devuelve ambas rutas. No escribe si no hay 15 partidos (lanza `ValueError`).

- [ ] **Step 6: Ejecutar y ver pasar**

Run: `python -m unittest discover -s tests -p "test_report.py" -v`
Expected: 2 tests OK.

- [ ] **Step 7: Commit**

```bash
git add soccer_predictor/report.py tests
git commit -m "feat(quiniela): informe Markdown y JSON"
```

---

### Task 5: Orquestador y CLI de una sola ejecución

**Files:**
- Modify: `soccer_predictor/orchestrator.py:22-35` (nuevos flags `log`, `explain`) y `:148-163`.
- Create: `soccer_predictor/jornada.py`
- Create: `tests/test_jornada.py`

**Interfaces:**
- `orchestrator.predict(..., log: bool = True, explain: bool = True)` (retrocompatible).
- `jornada.competition_for(match: dict, context: dict) -> str`: `"Liga F"` si `is_women`; `"Segunda División"` si `context.league == "esp.2"`; `"La Liga"` si `esp.1`; si no, `"Fútbol"`.
- `jornada.analyze_matches(entry: dict, predict_fn=predict, contexts: dict | None = None, fast: bool = False) -> dict`
- `jornada.run(jornada: int | None = None, html: str | None = None, force: bool = False, save: bool = False, output_dir: Path = Path("output"), fast: bool = False, predict_fn=None) -> dict`
- `jornada.main(argv: list[str] | None = None) -> int`
- CLI: `--jornada N`, `--html PATH`, `--force`, `--save`, `--fast`, `--output DIR`, `--no-cache`.

- [ ] **Step 1: Escribir tests que fallan**

```python
import pathlib, tempfile, unittest
from soccer_predictor import jornada

def fake_predict(home, away, comp="", **kw):
    return {"prob_1x2": {"home":0.5,"draw":0.3,"away":0.2},
            "prediction_1x2": "1", "expected_goals": {"home":1.6,"away":1.0},
            "positions": {"home":5,"away":10}, "low_confidence": False,
            "data_sources": {"home":"fake","away":"fake","home_recent":"WWDLW","away_recent":"LDLWW"}}

class TestJornada(unittest.TestCase):
    def _entry(self):
        base = {"home":"Alaves","away":"Deportivo","is_women":False,"is_pleno":False,
                "percentages":{"jugados":{"1":47,"X":36,"2":17},
                               "lae":None,"probables":{"1":43,"X":29,"2":28},
                               "tecnicos":{"1":44,"X":30,"2":26}},
                "lae":None,"probables":{"1":43,"X":29,"2":28},"pleno":None}
        ms = [dict(base, n=i) for i in range(1,15)]
        ms.append(dict(base, n=15, is_pleno=True,
                       pleno={"home":{"0":29,"1":36,"2":22,"M":13},
                              "away":{"0":23,"1":34,"2":25,"M":18}}))
        return {"jornada": 23, "season": 2027, "close": "SAB 21/11 12:00",
                "sources": {}, "matches": ms}

    def test_uses_probables_when_lae_missing(self):
        e = jornada.analyze_matches(self._entry(), predict_fn=fake_predict)
        m = e["matches"][0]
        self.assertEqual(m["modelo"], {"1":50.0,"X":30.0,"2":20.0})
        self.assertAlmostEqual(m["valor"]["2"], -8.0, places=1)
        self.assertIsNone(m["lae"])

    def test_competition_detection(self):
        self.assertEqual(jornada.competition_for({"is_women":True}, {}), "Liga F")
        self.assertEqual(jornada.competition_for({}, {"league":"esp.2"}), "Segunda División")
        self.assertEqual(jornada.competition_for({}, {"league":"esp.1"}), "La Liga")

    def test_run_writes_report_and_boletos(self):
        e = self._entry()
        original = jornada.fetch_jornada
        jornada.fetch_jornada = lambda **k: e
        try:
            with tempfile.TemporaryDirectory() as d:
                out = jornada.run(jornada=23, predict_fn=fake_predict,
                                  output_dir=pathlib.Path(d))
        finally:
            jornada.fetch_jornada = original
        self.assertEqual(out["jornada"], 23)
        self.assertIn("boleto_rentable", out)
        self.assertIn("boleto_conservador", out)

    def test_main_aborts_when_not_playable(self):
        e = self._entry(); e["played"] = True
        original = jornada.fetch_jornada
        jornada.fetch_jornada = lambda **k: e
        try:
            code = jornada.main(["--jornada","23"])
        finally:
            jornada.fetch_jornada = original
        self.assertNotEqual(code, 0)
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `python -m unittest discover -s tests -p "test_jornada.py" -v`
Expected: `ModuleNotFoundError` o `ImportError`.

- [ ] **Step 3: Añadir flags a `predict`**

En `orchestrator.py`:
- Firma: `def predict(..., women=False, log=True, explain=True)`.
- Paso 6: `if explain: enriched, source = llm.enrich_explanation(...)`; si no, `source="estadistico"`.
- Paso 7: `if log: ... log_prediction(result)`.

- [ ] **Step 4: Implementar `analyze_matches`**

Para cada partido:
1. `ctx = contexts.get(n, {})`; `comp = competition_for(m, ctx)`.
2. `abs_home = ctx.get("injuries",{}).get("home",{}).get("count",0)`; ídem away.
3. `r = predict_fn(m["home"], m["away"], comp, live=True, with_news=False, player_form=not fast, absences_home=abs_home, absences_away=abs_away, women=m["is_women"], log=False, explain=False)`.
4. `modelo = {s: round(p[s]*100,1)}`; `valor = {s: round(modelo[s] - ref[s],1)}` con `ref = lae or probables or {1:33.3,X:33.3,2:33.3}`.
5. `value_pick = max(valor) si valor[max] >= 3 else None`.
6. `pleno_sugerido` si `is_pleno` con `expected_goals`.
7. Guarda `context`, `competition`, `absences`, `low_confidence` y `sources`.

- [ ] **Step 5: Implementar `run`**

1. `entry = fetch_jornada(jornada, html)`.
2. Valida 15 partidos; si no, `ValueError`.
3. Determina `played`: comparar `entry["close"]` con `datetime.now()`; si el cierre ya pasó o `fetch` marca partidos jugados y no `force` → imprime aviso y devuelve `{"error":"jornada_no_jugable"}`.
4. `contexts = build_contexts(entry["matches"])` con `ThreadPoolExecutor(max_workers=4)`: ESPN (reutiliza `espn.search_team`), Football-Data (`team_form`), lesiones, noticias. Cada uno en `try/except` y su resultado en `entry["sources"]`.
5. `entry = analyze_matches(entry, predict_fn=predict_fn or predict, contexts=contexts, fast=fast)`.
6. `entry["boleto_rentable"] = build_boleto(matches, "rentable")`; `entry["boleto_conservador"] = build_boleto(matches, "seguro")`.
7. `write_report(entry, output_dir)`.
8. Si `save`, `database.save_quiniela(entry["jornada"], entry["matches"])` dentro de `try/except`.
9. Devuelve `entry`.

- [ ] **Step 6: Implementar `main`**

`argparse`; `--jornada` int, `--html` ruta, `--force`, `--save`, `--fast`, `--output`, `--no-cache`. Llama a `run`; imprime un resumen con jornada, cierre, rutas y los dos boletos en formato legible (`1 X 2 ...`). Devuelve 0 si ok, 2 si jornada no jugable, 1 si error.

- [ ] **Step 7: Ejecutar y ver pasar**

Run: `python -m unittest discover -s tests -p "test_jornada.py" -v`
Expected: 4 tests OK.

- [ ] **Step 8: Ejecutar toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK (sin tests de red).

- [ ] **Step 9: Commit**

```bash
git add soccer_predictor/orchestrator.py soccer_predictor/jornada.py tests
git commit -m "feat(quiniela): ejecucion unica con analisis, informe y boletos"
```

---

### Task 6: Aceptación con la jornada 23 real y documentación

**Files:**
- Modify: `README.md` (sección nueva "Análisis de la jornada en una ejecución").
- Create: `output/.gitkeep` (el directorio de salida se ignora salvo el marcador).
- Modify: `.gitignore` (añadir `output/` y `data/cache/jornada_*/`).

- [ ] **Step 1: Ejecutar contra la jornada real**

```bash
python -m soccer_predictor.jornada --jornada 23 --force
```

Esperado: 15 partidos analizados; dos ficheros en `output/`; resumen con dos boletos; sin traceback.

- [ ] **Step 2: Verificar el contenido**

```bash
python - <<'PY'
import json, glob
f=sorted(glob.glob("output/jornada_23_*.json"))[-1]
e=json.load(open(f,encoding="utf-8"))
print(e["jornada"], len(e["matches"]))
for k in ("boleto_rentable","boleto_conservador"):
    b=e[k]; print(k, b["bets"], b["cost_eur"], len(b["columns"]), b["pleno"], b["guarantee"]["p14"])
print([ (m["n"], m["competition"], bool(m.get("lae"))) for m in e["matches"] ])
PY
```

Esperado: `23 15`, ambos boletos `24 18.0 24`, y competiciones correctas (`Liga F` en 11-14).

- [ ] **Step 3: Revisar el informe a mano**

Abrir `output/jornada_23_*.md` y comprobar: los 4 partidos femeninos usan datos de Liga F; los partidos sin xG/Elo muestran `n/d`; el pleno tiene las 4 probabilidades; la garantía dice 13/14 y 24/216.

- [ ] **Step 4: Documentar en README**

Añadir: qué hace, comando, flags, fuentes, formato de salida, garantía del boleto y aviso de que son probabilidades. Incluir el ejemplo de la jornada 23.

- [ ] **Step 5: Commit final**

```bash
git add README.md .gitignore output/.gitkeep
git commit -m "docs(quiniela): ejecucion unica de la jornada y aceptacion J23"
```
