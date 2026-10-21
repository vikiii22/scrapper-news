# IA local (offline)

Un LLM en tu equipo, sin depender de ninguna API de pago ni de conexion a
internet (salvo la descarga inicial de la imagen y del modelo).

| Archivo | Que levanta | GPU | Cuando usarlo |
|---|---|---|---|
| `docker-compose.yml` | Ollama en Docker (+ Open WebUI opcional) | No (CPU) | Todo contenido, nada instalado en Windows |
| `docker-compose.hybrid.yml` | Solo Open WebUI; Ollama nativo | Si (Intel Arc) | Si quieres maxima velocidad |
| `chat.py` | Chat minimo en Streamlit | Segun donde corra Ollama | Interfaz del dia a dia |

Hardware de referencia: Intel Core Ultra 5 226V, 16 GB RAM, Arc 130V (memoria
compartida). Con eso entran bien modelos de 3B-8B.

---

## Todo en Docker (recomendado si no quieres instalar nada)

```powershell
# 1. Arranca Docker Desktop y espera a que el icono deje de girar.

# 2. Levanta Ollama
docker compose -f deploy/ia/docker-compose.yml up -d

# 3. Descarga un modelo (una sola vez, esto si necesita internet)
docker compose -f deploy/ia/docker-compose.yml exec ollama ollama pull qwen3:4b

# 4. Interfaz de chat
pip install -r deploy/ia/requirements.txt
streamlit run deploy/ia/chat.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

Chat en <http://localhost:8501>, API en `http://localhost:11434`.

> El flag `--server.address 127.0.0.1` es importante: sin el, Streamlit escucha
> en `0.0.0.0` y cualquiera de tu red local puede abrir tu chat. Con
> `--browser.gatherUsageStats false` desactivas la telemetria de Streamlit.

Si ademas quieres Open WebUI (interfaz completa tipo ChatGPT, consume mas RAM):

```powershell
docker compose -f deploy/ia/docker-compose.yml --profile ui up -d
```

en <http://localhost:3000>.

**Limite importante:** la imagen oficial de Ollama solo acelera con GPU NVIDIA
(CUDA) o AMD (ROCm). La Intel Arc integrada no se puede pasar al contenedor
desde Docker Desktop, asi que **infiere en CPU**. Es la mitad de rapido que
nativo, pero para chat y resumenes va bien.

---

## Opcion hibrida (mas rapida)

Solo si aceptas instalar Ollama en Windows para que use la Arc:

```powershell
winget install Ollama.Ollama
ollama pull qwen3:4b

docker compose -f deploy/ia/docker-compose.hybrid.yml up -d
```

El chat de Streamlit funciona igual en ambos casos: solo cambia la URL en la
barra lateral si apuntas a otro equipo.

---

## Modelos sugeridos

Se descargan con `ollama pull` **dentro del contenedor**:

```powershell
docker compose -f deploy/ia/docker-compose.yml exec ollama ollama pull qwen3:4b
```

| Modelo | Tamano | Para que |
|---|---|---|
| `llama3.2:3b` | ~2 GB | El mas rapido. Chat y resumenes |
| `qwen3:1.7b` | ~1.4 GB | Minimo consumo, respuestas cortas |
| `qwen3:4b` | ~2.5 GB | Mejor en espanol y razonando |
| `gemma3:4b` | ~3.3 GB | Redaccion, tono mas natural |
| `qwen2.5-coder:7b` | ~4.7 GB | Codigo (lento en CPU, ~3 tok/s) |
| `qwen3:8b` | ~5.2 GB | El techo razonable con 16 GB |

Cualquier modelo del catalogo de <https://ollama.com/library> sirve igual:
`docker compose -f deploy/ia/docker-compose.yml exec ollama ollama pull <nombre>`.

En el chat, pulsa **🔄 Recargar modelos** y aparece en el desplegable.

Notas:

- `qwen3` razona antes de responder (mas lento). Para desactivarlo, anade
  `/no_think` al final del mensaje.
- Los modelos ocupan espacio en el disco virtual de Docker. Revisalo con
  `docker system df -v`.
- Para borrar uno: `... exec ollama ollama rm <nombre>`.

Rendimiento aproximado en este equipo (CPU, dentro de Docker):

| Modelo | Velocidad |
|---|---|
| `llama3.2:3b` | ~14 tok/s (medido) |
| `qwen3:4b` | ~7-9 tok/s |
| `qwen2.5-coder:7b` | ~3-4 tok/s |

Nativo con la GPU Intel Arc seria el doble, pero entonces hay que instalar
Ollama en Windows y usar `docker-compose.hybrid.yml`.

---

## Conectar el proyecto Python

`llm_reasoning.py` ya habla el protocolo de OpenAI, asi que basta apuntarlo al
endpoint local en `.env`:

```
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL=qwen3:4b
```

Si el modelo no esta levantado o falla, el predictor sigue funcionando con la
explicacion estadistica por defecto.

---

## Privacidad: que sale y que no

Lo que escribes en el chat **no sale de tu equipo**:

| Elemento | Donde esta |
|---|---|
| El modelo | Contenedor local, descargado una vez |
| Tus mensajes | Memoria del proceso Streamlit, nunca en disco |
| La inferencia | CPU de tu equipo, sin llamadas externas |

Lo unico que usa internet es la descarga inicial del modelo (`ollama pull`)
y, si tu lo pides, `docker compose pull` para actualizar imagenes.

Comprobaciones:

- Ambos servicios escuchan solo en `127.0.0.1` (no accesibles desde la LAN).
- Telemetria de Streamlit desactivada con `--browser.gatherUsageStats false`.
- Docker Desktop si envia sus propias estadisticas de uso (nunca tus prompts):
  se desactiva en Settings > General.

Prueba definitiva: desconecta el wifi y sigue chateando. Si responde, es local.

---

## Operacion

```powershell
# Estado y consumo
docker compose -f deploy/ia/docker-compose.yml ps
docker stats --no-stream

# Modelos descargados y espacio ocupado
docker compose -f deploy/ia/docker-compose.yml exec ollama ollama list
docker system df -v

# Parar (los modelos persisten en el volumen)
docker compose -f deploy/ia/docker-compose.yml down

# Borrar tambien los datos
docker compose -f deploy/ia/docker-compose.yml down -v
```

Variables opcionales en un `.env` junto al compose:

```
OLLAMA_KEEP_ALIVE=30m   # tiempo que el modelo sigue cargado en RAM
```

> Docker Desktop debe estar arrancado antes de usar estos comandos. Si quieres
> que arranque solo al iniciar sesion: Settings > General > *Start Docker
> Desktop when you sign in*.
>
> Si el contenedor se queda sin memoria, limita WSL2 en `%UserProfile%\.wslconfig`:
>
> ```ini
> [wsl2]
> memory=10GB
> ```
>
> y reinicia con `wsl --shutdown`.
