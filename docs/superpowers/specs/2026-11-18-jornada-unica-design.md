# Diseño: ejecución única de análisis de la jornada de quiniela

Fecha: 2026-11-18
Estado: pendiente de aprobación final

## 1. Intención y porqué

Hoy el análisis de una jornada exige varios pasos manuales: pegar el HTML del
boleto, lanzar `analyze_quiniela`, revisar partido a partido y decidir el
boleto con el método de `quiniela-rentable`. El objetivo es una sola orden que
obtenga la jornada vigente desde la web de Eduardo Losilla, enriquezca cada
partido con datos reales y devuelva un informe listo para jugar, con dos
boletos (rentable y conservador) y el pleno al 15.

Sirve para jugar mejor y más rápido cada semana, no para predecir por predecir.

## 2. Objetivos

- Un comando: `python -m soccer_predictor.jornada` (sin argumentos) detecta y
  analiza la jornada vigente.
- Obtener la jornada desde Losilla: número, partidos, horarios, % Jugados,
  % LAE, % Probables y pleno, con el CSV oficial como fuente primaria.
- Enriquecer los 14 partidos + pleno con: forma (últimos 5), rendimiento
  local/visitante, xG/xGA, Elo, cuotas implícitas, bajas/sancionados, rachas
  y noticias relevantes.
- Reutilizar el motor Poisson y los scrapers existentes; no reescribirlos.
- Producir un informe Markdown + JSON reproducible, con valor modelo−LAE por
  signo y confianza.
- Generar dos boletos de 3 dobles + 3 triples (24 apuestas, 18 €) con garantía
  13 demostrable y el pleno recomendado, más una alternativa "loca" para bote.
- Degradar sin romper: si una fuente falla, el informe se genera y se marca la
  carencia.

## 3. No objetivos

- No validar ni comprar apuestas automáticamente.
- No entrenar modelos nuevos ni reescribir el motor Poisson.
- No cubrir Quinigol, Elige8 ni otras loterías.
- No garantizar premios: el informe declara probabilidades y garantías.
- No depender de APIs de pago ni de claves obligatorias.

## 4. Anti-objetivos

- Fallar entero porque Transfermarkt, un mercado o Understat esté caído.
- Inventar datos cuando una fuente no responde (se marca `n/d`).
- Duplicar lógica de scraping que ya existe en `soccer_predictor/scrapers/`.
- Generar un boleto sin explicar qué garantiza y qué sacrifica.
- Reutilizar literalmente los signos del ejemplo de jornada 14 del skill:
  el método son las reglas, no los picks.

## 5. Restricciones

- Python 3.9+, `requests`, `beautifulsoup4`, `lxml` (ya en requirements).
- Solo fuentes gratuitas y accesibles sin clave: dominios autorizados por el
  usuario.
- Windows: rutas con `pathlib`, sin dependencias de shell.
- Caché en disco por jornada/día y timeouts cortos.
- El análisis debe completarse en un tiempo razonable (< ~10 min con red).

## 6. Enfoques considerados

1. **Pipeline modular + CLI (elegido).** Adaptadores por fuente, orquestador y
   generador de informe. Mantenible, testeable y reutilizable cada jornada.
2. **Script único de ~300 líneas.** Más rápido de escribir, pero duplica
   lógica, no cachea y se rompe al cambiar una fuente.
3. **Pestaña en Streamlit.** Útil para ver, pero añade UI, no es "una única
   ejecución" y no resuelve el pipeline.

Se elige el 1 porque el valor está en repetirlo cada semana y en poder confiar
en los datos: la modularidad y el caché son parte del producto.

## 7. Arquitectura propuesta

```
soccer_predictor/
├── jornada.py                 # CLI + orquestación de la ejecución única
├── quiniela_sources/
│   ├── __init__.py
│   ├── losilla.py             # jornada vigente: CSV + HTML del boleto
│   ├── understat.py           # xG/xGA (best-effort, hoy bloquea)
│   ├── clubelo.py             # Elo (best-effort, hoy inestable)
│   ├── football_data.py       # resultados, xG y cuotas CSV (SP1/SP2)
│   ├── injuries.py            # Transfermarkt: bajas y sanciones
│   ├── markets.py             # Polymarket/Kalshi: solo contexto de outrights
│   ├── news.py                # Google News RSS por partido
│   └── cache.py               # caché JSON en data/cache/jornada_<n>/
├── report.py                  # Markdown + JSON
└── boleto.py                  # combinaciones, garantías y pleno
```

Flujo:

1. `losilla.fetch_current()` → `{jornada, cierre, matches[15]}`.
   - Fuente primaria: `api.eduardolosilla.es/analisisSigno?...&csv=true`.
   - El CSV trae secciones `tecnicos`, `quinielista`, `lae` y `real`.
     Mapeo: %Jugados = `quinielista`; %LAE = `lae`; %Probables = `real`.
     Si `lae` aún está vacío (jornada recién abierta), se usa `real` como
     referencia y el informe lo marca.
   - El HTML de la portada completa equipos, día y hora. El parser actual
     (`parse_quiniela_html`) se reutiliza solo para eso, no para porcentajes.
2. `jornada.build_context()`: adaptadores en paralelo (máx. 4 hilos) por
   partido, con caché.
   - ESPN (existente) → forma, gf/ga, posición, H2H.
   - Football-Data SP1/SP2 → cuotas 1X2 de cierre, resultados y xG recientes.
   - Understat → xG/xGA si responde; hoy devuelve página de bloqueo, así que
     es best-effort y no bloquea.
   - ClubElo → Elo si responde; hoy devuelve 502/timeout, best-effort.
   - Transfermarkt → lesionados/sancionados del equipo.
   - Google News → 3 titulares con fecha.
   - Mercados → solo probabilidad de outright (campeón) como contexto; no hay
     mercados por partido de quiniela, así que nunca sustituyen a las cuotas.
3. `predict()` existente → `prob_1x2`, goles esperados, posiciones y fuentes.
   - Se detecta la competición real por equipo con ESPN (`esp.1`, `esp.2`,
     `esp.w.1`); se acabó el `competition_default="La Liga"` para todos.
   - Se le pasan las bajas detectadas en `absences_home/away`, que el motor ya
     usa. No se añade un segundo ajuste manual de λ: el modelo base, sus
     ajustes internos y el contexto se muestran por separado y sin duplicar.
   - `predict()` se ejecuta en serie (escribe en BBDD y puede llamar al LLM);
     los adaptadores de datos sí van en paralelo. `with_news=False` y sin LLM
     en la ruta crítica.
4. `boleto.build()` → dos boletos de 3 dobles + 3 triples (24 apuestas, 18 €,
   pleno incluido en la columna). Ver §9.
5. `report.write()` → `output/jornada_<n>_<fecha>.md` y `.json`.

Selección de jornada: la próxima cuyo cierre esté en el futuro. Si ya empezó,
se avisa y se pide `--jornada N` (o `--force` para analizarla igual, marcando
los partidos ya jugados). Nunca se genera un boleto silenciosamente inválido.

Persistencia: por defecto solo `output/`. Con `--save` se guarda además en la
BBDD existente (`save_quiniela`), sin que un fallo de Mongo impida el informe.

## 8. Contenido del informe

- Cabecera: jornada, cierre, bote, fuentes consultadas y su estado.
- Tabla por partido: equipos, hora, %Jugados/LAE/Probables, modelo, valor,
  forma, xG, Elo, bajas, titular de prensa y veredicto.
- "Lectura del partido" en 2-3 líneas por encuentro, con el argumento.
- Pleno al 15: probabilidades 0/1/2/M de cada equipo y recomendación.
- Boleto rentable: 14 signos + pleno, dobles/triples, garantías.
- Boleto conservador: ídem, con su probabilidad estimada de 12/13/14.
- Riesgos: partidos de baja confianza y qué se está sacrificando.

## 9. Reglas de decisión del boleto

- Fijo solo si modelo >60% o LAE >75% y el valor no está claramente en contra.
- Triple en partidos con X probable ≥29-33% o trampa de porcentajes.
- Doble preferente `1-2`; `1X` solo si la X es el segundo signo con margen.
- Prohibido doblar el partido de máxima confianza para ahorrar.
- El pleno no condiciona 13/14; se elige por marginales de Poisson y, si hay
  bote, se ofrece la variante "loca" gratis.
- Ambos boletos declaran coste, apuestas, garantía mínima y probabilidad de 14.

**Reducción de 24 apuestas (decisión técnica):** no se transcribe una tabla
externa. Dados los 6 partidos múltiples (3 dobles, 3 triples), se genera un
código de cobertura determinista de 24 columnas sobre las 216 combinaciones
posibles, con radio 1. Verificado por cálculo: cubre las 216 (garantía 13 si
los 8 fijos entran) y acierta 14 cuando la combinación real está entre las 24
(24/216 = 11,1 %). El test unitario recomputa la cobertura, así que la
garantía es comprobable, no una promesa.

## 10. Manejo de errores

- Cada adaptador devuelve `{ok, data, error, source_url, fetched_at}`.
- Timeout 10-15 s, un reintento, y caché de 6 h (jornada) / 24 h (Elo, xG).
- Si Losilla falla, se puede pasar `--jornada N` o `--html archivo`; si no hay
  jornada, se aborta con mensaje claro.
- Nunca se escribe un informe con partidos incompletos sin marcarlos.

## 11. Cobertura por competición

| Competición | Datos | xG | Elo | Cuotas |
|---|---|---|---|---|
| LaLiga (esp.1) | ESPN + Football-Data SP1 | Football-Data / Understat si responde | ClubElo si responde | SP1 |
| Segunda (esp.2) | ESPN + Football-Data SP2 | Football-Data SP2 | n/d | SP2 |
| Liga F (esp.w.1) | ESPN Liga F + clasificación | n/d | n/d | n/d |

`n/d` es un resultado válido y visible, no un fallo. La aceptación exige los 15
partidos analizados; no exige que las tres fuentes opcionales respondan.

## 12. Verificación

- Tests con `unittest` (sin dependencia nueva) y fixtures reales de la jornada
  23 capturados en `tests/fixtures/`: parser CSV/HTML de Losilla, mapeo de
  porcentajes, coste y cobertura de los 24 boletos.
- Test de integración marcado como red (no en CI por defecto).
- Ejecución real de la jornada 23 como aceptación: 15 partidos, informe y dos
  boletos, sin excepciones.
- Comprobación manual: CSV de Losilla y HTML coinciden en signos y horarios.

## 13. Decisiones dejadas al constructor

- Nombres exactos de funciones y estructura interna de los adaptadores.
- Formato preciso de las tablas Markdown.
- Selección de titulares de noticias (3 por partido) y criterio de relevancia.
- Estrategia de caché exacta (fichero único vs. por fuente).
