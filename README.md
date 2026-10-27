# Feed News

Agregador inteligente de noticias con actualización automática, clasificación por relevancia y soporte de traducción al español.

## Características

- **Ingestión RSS/Atom** de 20 fuentes (España, Europa, Internacional) con actualización cada 15 minutos
- **Clasificación automática** por ámbito geográfico y 10 categorías temáticas
- **Puntuación de relevancia** ponderada por impacto, urgencia, actualidad y fiabilidad de fuente
- **Detección de duplicados** por similitud de título (Jaccard sobre palabras normalizadas)
- **Agrupación de noticias** sobre el mismo acontecimiento
- **Detección automática de idioma** (langdetect)
- **Traducción al español** vía LibreTranslate (gratuito), con soporte para OpenAI y Anthropic
- **Interfaz web** responsive con modo oscuro, búsqueda, filtros y guardado de favoritos
- **Panel de administración** con estadísticas del sistema y gestión de fuentes
- **Planificador de tareas** (APScheduler): ingestión cada 15m, procesamiento cada 5m

## Arquitectura

```
feed_news/
├── app/
│   ├── main.py              # FastAPI app, startup, lifespan
│   ├── config.py            # Settings from .env
│   ├── database.py          # SQLAlchemy async engine
│   ├── models.py            # Source, News, Event, Category, TranslationCache, SystemLog
│   ├── schemas.py           # Pydantic schemas
│   ├── seeds.py             # Categorías y fuentes iniciales
│   ├── api/                 # Rutas FastAPI
│   │   ├── news.py          # /api/news
│   │   ├── sources.py       # /api/sources
│   │   └── admin.py         # /api/admin
│   ├── ingestion/           # Captación de noticias
│   │   ├── rss_fetcher.py   # Fetcher RSS/Atom
│   │   ├── normalizer.py    # Normalización, geo-hints
│   │   └── manager.py       # Ciclo de ingestión
│   ├── processing/          # Procesamiento
│   │   ├── categorizer.py   # Asignación de categorías por keywords
│   │   ├── scoring.py       # Algoritmo de relevancia ponderada
│   │   ├── deduplication.py # Detección de duplicados
│   │   └── grouping.py      # Agrupación de acontecimientos
│   ├── translation/         # Traducción
│   │   ├── detector.py      # Detección de idioma
│   │   ├── translator.py    # Caché + coordinación
│   │   └── providers/       # LibreTranslate, OpenAI, Anthropic
│   ├── scheduler/
│   │   └── tasks.py         # APScheduler jobs
│   └── static/
│       └── index.html       # SPA frontend
└── tests/                   # Suite de pruebas
```

## Instalación

### Requisitos

- Python 3.10+
- ~200 MB de espacio en disco

### Pasos

```bash
# 1. Clonar / acceder al directorio
cd feed_news

# 2. Crear entorno virtual
python3 -m venv venv  # puede requerir: apt install python3.12-venv
# Si no hay ensurepip:
python3 -m venv --without-pip venv
curl -sS https://bootstrap.pypa.io/get-pip.py | venv/bin/python3

# 3. Activar e instalar dependencias
source venv/bin/activate
pip install -r requirements.txt
pip install "sqlalchemy[asyncio]" greenlet  # greenlet necesario para SQLAlchemy async

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores (especialmente ADMIN_TOKEN)

# 5. Arrancar
python -m uvicorn app.main:app --host 0.0.0.0 --port 8765
```

La base de datos se inicializa y las fuentes se cargan automáticamente en el primer arranque.
La primera ingestión de noticias comienza de inmediato.

Acceder en: http://localhost:8765

## Variables de entorno

| Variable | Descripción | Por defecto |
|---|---|---|
| `DATABASE_URL` | URL de SQLAlchemy async | `sqlite+aiosqlite:///./feed_news.db` |
| `TRANSLATION_PROVIDER` | `libre`, `openai`, `anthropic`, `none` | `libre` |
| `LIBRETRANSLATE_URL` | Instancia LibreTranslate | `https://libretranslate.com` |
| `LIBRETRANSLATE_API_KEY` | API key de LibreTranslate (opcional) | `` |
| `OPENAI_API_KEY` | API key de OpenAI (opcional) | `` |
| `ANTHROPIC_API_KEY` | API key de Anthropic (opcional) | `` |
| `ADMIN_TOKEN` | Token de administración | `admin-token-change-me` |
| `INGESTION_INTERVAL_MINUTES` | Intervalo de ingestión | `15` |
| `PROCESSING_INTERVAL_MINUTES` | Intervalo de procesamiento | `5` |

## API

| Endpoint | Descripción |
|---|---|
| `GET /api/news` | Lista de noticias con filtros (`geo`, `category`, `relevance`, `q`, `sort_by`, `page`) |
| `GET /api/news/featured` | Noticias destacadas |
| `GET /api/news/{id}` | Detalle de una noticia |
| `GET /api/categories` | Lista de categorías |
| `GET /api/sources` | Lista de fuentes |
| `POST /api/sources` | Crear fuente (requiere `X-Admin-Token`) |
| `PATCH /api/sources/{id}/toggle` | Habilitar/deshabilitar fuente (admin) |
| `GET /api/admin/stats` | Estadísticas del sistema (admin) |
| `GET /api/admin/logs` | Logs del sistema (admin) |
| `POST /api/admin/run-ingestion` | Lanzar ingestión manual (admin) |
| `POST /api/admin/run-processing` | Lanzar procesamiento manual (admin) |
| `GET /api/health` | Estado de la aplicación |
| `GET /api/docs` | Documentación interactiva (Swagger) |

## Pruebas

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

42 pruebas automatizadas que cubren: ingestión, normalización, detección de idioma, puntuación, deduplicación, traducción y endpoints de API.

## Fuentes configuradas

### España (7 fuentes)
El País, El Mundo, La Vanguardia, El Confidencial, El Diario, 20 Minutos, El Español

### Europa (5 fuentes)
Euronews (EN), POLITICO Europe, BBC Europe, Deutsche Welle (EN), Le Monde Diplomatique (ES)

### Internacional (8 fuentes)
Reuters World, BBC World, Al Jazeera, The Guardian World, France 24, Deutsche Welle World, RT (ES), Agencia EFE

## Traducción

La traducción está desactivada por defecto para artículos en inglés (se muestran con título original mientras `translation_status = "pending"`).

Para activar la traducción automática:

1. **LibreTranslate (gratuito)**: `TRANSLATION_PROVIDER=libre`. Usa instancias públicas como fallback, sin clave API.
2. **OpenAI**: `TRANSLATION_PROVIDER=openai` + `OPENAI_API_KEY=sk-...`
3. **Anthropic**: `TRANSLATION_PROVIDER=anthropic` + `ANTHROPIC_API_KEY=sk-ant-...`

## Limitaciones conocidas

- **Sin autenticación de usuario**: los favoritos se guardan en localStorage del navegador.
- **SQLite**: adecuado para uso personal. Para múltiples usuarios concurrentes, configurar PostgreSQL.
- **Traducción bajo demanda**: los artículos en inglés se muestran en inglés hasta que la traducción se procesa.
- **Imágenes**: algunas fuentes no incluyen imágenes en sus feeds RSS.
- **RT (ES)**: incluida con puntuación de fiabilidad reducida (0.5) como fuente de contraste editorial.

## Despliegue en producción

```bash
# Con gunicorn + uvicorn workers
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8765

# Variables de entorno de producción
SECRET_KEY=<random-64-chars>
ADMIN_TOKEN=<random-secure-token>
DEBUG=false
```

Para PostgreSQL, cambiar `DATABASE_URL` a `postgresql+asyncpg://user:pass@host/dbname` e instalar `asyncpg`.
