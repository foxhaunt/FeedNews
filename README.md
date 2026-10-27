# 📰 feed-news

Agregador personal de noticias con relevancia configurable y perfil histórico propio.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)
![Tests](https://img.shields.io/badge/tests-202%20passing-brightgreen)
![Fuentes](https://img.shields.io/badge/fuentes-25%20activas-blueviolet)

---

## Contenido

1. [Fuentes de noticias](#1-fuentes-de-noticias)
2. [Distribución editorial](#2-distribución-editorial)
3. [Categorías temáticas](#3-categorías-temáticas)
4. [Sistema de relevancia](#4-sistema-de-relevancia)
5. [Perfil de Historia](#5-perfil-de-historia)
6. [Configuración](#6-configuración)
7. [Instalación](#7-instalación)
8. [API](#8-api)

---

## 1. Fuentes de noticias

25 fuentes activas agrupadas por ámbito geográfico. La columna `fiabilidad` pondera las puntuaciones de relevancia mediante un ajuste suave de ±20% — no suprime ninguna fuente.

### España

| Fuente | Línea editorial | Fiabilidad | Estado |
|---|---|---|---|
| El País | centroizquierda | 0.85 | ✅ activa |
| 20 Minutos | centroizquierda | 0.70 | ✅ activa |
| La Vanguardia | centro | 0.85 | ✅ activa |
| El Confidencial | centro | 0.80 | ✅ activa |
| El Mundo | centroderecha | 0.80 | ✅ activa |
| El Español | centroderecha | 0.75 | ✅ activa |
| ABC España | centroderecha | 0.80 | ✅ activa |
| The Objective | centroderecha | 0.75 | ✅ activa |
| OKDIARIO | derecha | 0.55 | ✅ activa |
| La Bandera | derecha | 0.60 | ✅ activa |
| La Gaceta | derecha | 0.55 | ✅ activa |
| El Diario | izquierda | 0.55 | ❌ desactivada |

### Europa

| Fuente | Idioma | Línea editorial | Fiabilidad |
|---|---|---|---|
| BBC Europe | EN | centro | 0.92 |
| POLITICO Europe | EN | centroderecha | 0.85 |
| Euronews (ES) | ES | centro | 0.80 |
| Euronews (EN) | EN | centro | 0.80 |
| Deutsche Welle (EN) | EN | centro | 0.88 |
| Le Monde Diplomatique (ES) | ES | izquierda | 0.85 |

### Internacional

| Fuente | Idioma | Línea editorial | Fiabilidad |
|---|---|---|---|
| BBC World | EN | centro | 0.92 |
| The Guardian World | EN | centroizquierda | 0.88 |
| France 24 (EN) | EN | centro | 0.85 |
| Deutsche Welle World | EN | centro | 0.88 |
| NPR News | EN | centroizquierda | 0.85 |
| Al Jazeera | EN | no determinado | 0.75 |
| RT (ES) | ES | proruso | 0.45 |

### Historia (fuentes académicas)

| Fuente | Institución | Tipo | Fetch |
|---|---|---|---|
| El Reto Histórico | — | divulgación | 60 min |
| Muy Interesante Historia | — | divulgación | 1440 min |
| Hispania Sacra | CSIC | académica | 1440 min |
| Hispania | CSIC | académica | 1440 min |
| En la España Medieval | UCM | académica | 1440 min |

---

## 2. Distribución editorial

| Posición | Peso en feed España |
|---|---|
| Centroderecha | 31 % |
| Centro | 22 % |
| Centroizquierda | 19 % |
| Derecha | 17 % |
| Izquierda | 11 % |

**HHI ≈ 0.21** — concentración moderada (baja < 0.15 · moderada 0.15–0.25 · alta > 0.25).

---

## 3. Categorías temáticas

Cada artículo recibe hasta 3 categorías mediante coincidencia de palabras clave con límites de palabra. Las fuentes con categoría primaria forzada (como Historia) exigen el **doble del umbral** en categorías secundarias para evitar falsos positivos.

`⚔️ Defensa` `🌍 Geopolítica` `🏛️ Política` `📈 Economía` `🔬 Ciencia` `💻 Tecnología` `🔋 Energía` `🏥 Salud` `🌿 Medioambiente` `🛡️ Seguridad` `⚖️ Sociedad` `🚨 Sucesos` `📜 Historia`

### Multiplicadores de categoría

| Categoría | Multiplicador |
|---|---|
| Defensa | ×1.25 |
| Geopolítica | ×1.20 |
| Política | ×1.10 |
| Economía | ×1.10 |
| Seguridad / Sucesos | ×1.08 |
| Ciencia / Tecnología | ×1.00 |
| Sociedad | ×0.95 |

---

## 4. Sistema de relevancia

Todos los artículos reciben `relevance_score ∈ [0, 1]`. **Historia usa su propio algoritmo** (ver §5). El resto comparte esta fórmula:

```
puntuación = 0.5 (base)
  + recencia    → <1 h: +0.20 · <6 h: +0.15 · <24 h: +0.10 · <72 h: +0.05
  + tier-1 kws  → guerra, atentado, bomba, terremoto … +0.08/hit (máx +0.20)
  + tier-2 kws  → elecciones, crisis, sanciones, OTAN … +0.03/hit (máx +0.09)
  × categoría   → ×0.95 – ×1.25
  × geo         → ×1.05 España · ×1.02 Europa · ×1.00 Internacional
  × fiabilidad  → ajuste suave ±20% en torno a 0.7

Destacada  ≥ 0.72
Relevante  ≥ 0.48
Seguimiento < 0.48
```

---

## 5. Perfil de Historia

Los artículos históricos usan un algoritmo separado basado en preferencias personales. La **recencia tiene peso mínimo** — un artículo académico excelente publicado hace meses puede puntuar más alto que una noticia superficial de hoy.

### Fórmula

```
puntuación = 0.40 × afinidad_temática
           + 0.25 × profundidad_contenido
           + 0.20 × interés_historiográfico
           + 0.15 × calidad_documental
           + recencia (máx +0.05)

Destacada  ≥ 0.70
Relevante  ≥ 0.45
Seguimiento < 0.45
```

### Temas de máxima prioridad *(afinidad alta)*

Historia de España e Hispanidad — artículos dedicados a estos temas puntúan hasta 0.85 en afinidad temática.

`hispania` `hispanidad` `visigodo` `al-ándalus` `califato` `taifa` `reconquista` `castilla` `corona de aragón` `fueros` `siglo de oro` `reyes católicos` `monarquía hispánica` `guerra carlista` `celtíberos` `íberos` `hispania romana` `mozárabe` `mudéjar` `sefardí` `reino de granada` `carlos v` `felipe ii` `descubrimiento de américa`

### Temas de gran interés *(afinidad media)*

`segunda guerra mundial` `nazismo` `holocausto` `historia militar` `batalla` `cruzada` `legión romana` `república romana` `julio césar` `imperio romano` `historia de la iglesia` `papado` `inquisición` `templarios` `hagiografía` `mártir` `faraón` `antiguo egipto` `imperio otomano` `vikingo` `personaje histórico`

### Temas excluidos *(afinidad mínima = 0.05)*

`prehistoria` `paleolítico` `neolítico` `calcolítico` `megalítico` `neandertal` `homo sapiens` `cromañón` `australopithecus` `dólmen`

### Indicadores de calidad

| Dimensión | Señales positivas | Señales negativas |
|---|---|---|
| **Profundidad** | Resumen >400 chars · `se analiza` · `fuentes primarias` · `contexto histórico` · `excavación arqueológica` | `top 10` · `curiosidades` · `sabías que` · `alucinante` |
| **Historiográfico** | `nuevo hallazgo` · `fuente inédita` · `debate historiográfico` · fuente UCM / CSIC | — |
| **Documental** | Alta fiabilidad · `csic` · `ucm` · `universidad` · `real academia` | Baja fiabilidad de fuente |

### Distribución actual (99 artículos)

| Nivel | Artículos |
|---|---|
| Destacada | 4 |
| Relevante | 68 |
| Seguimiento | 27 |

> **Destacados actuales:** mudéjares del Reino de Castilla (0.765) · lazos diplomáticos en la Corona de Castilla (0.765) · diplomacia de la Corona de Aragón / Guerra de los Dos Pedros (0.737) · provisiones episcopales de Orihuela (0.707)

Para ajustar las preferencias edita `app/processing/historia_profile.py` (solo datos, sin lógica) y recalcula:

```bash
python -m app.maintenance rescore_historia
```

---

## 6. Configuración

### Variables de entorno (`.env`)

| Variable | Descripción | Por defecto |
|---|---|---|
| `DATABASE_URL` | URL SQLAlchemy async | `sqlite+aiosqlite:///./feed_news.db` |
| `TRANSLATION_PROVIDER` | `libretranslate` · `openai` · `anthropic` · `none` | `none` |
| `LIBRETRANSLATE_URL` | Instancia LibreTranslate | `http://localhost:5000` |
| `OPENAI_API_KEY` | API key OpenAI | — |
| `ANTHROPIC_API_KEY` | API key Anthropic | — |
| `ADMIN_TOKEN` | Token de administración | `admin-token-change-me` |
| `MAX_CONCURRENT_FETCHES` | Fetches simultáneos | `5` |

### Gestionar fuentes

Edita `app/seeds.py` y añade `"enabled": False` para desactivar una fuente. El próximo arranque aplica el cambio automáticamente.

### Mantenimiento

```bash
python -m app.maintenance reclassify_historia   # recategorizar artículos históricos
python -m app.maintenance rescore_historia       # recalcular puntuaciones de historia
```

---

## 7. Instalación

```bash
# 1. Entorno virtual
python3 -m venv venv
source venv/bin/activate

# 2. Dependencias
pip install -r requirements.txt

# 3. Configuración
cp .env.example .env   # edita ADMIN_TOKEN al menos

# 4. Arrancar
uvicorn app.main:app --host 0.0.0.0 --port 8765
```

La base de datos se inicializa y las fuentes se cargan en el primer arranque. Accede en `http://localhost:8765`.

### Tests

```bash
pytest tests/ -q                              # suite completa (202 tests)
pytest tests/test_historia_scoring.py -v      # perfil de historia (15 tests)
```

---

## 8. API

| Endpoint | Descripción |
|---|---|
| `GET /api/news` | Lista con filtros: `geo`, `category`, `relevance`, `q`, `sort_by`, `page` |
| `GET /api/news/featured` | Noticias destacadas (acepta `geo`, `category`) |
| `GET /api/news/{id}` | Detalle de una noticia |
| `GET /api/categories` | Categorías disponibles |
| `GET /api/sources` | Lista de fuentes |
| `POST /api/sources` | Crear fuente *(requiere `X-Admin-Token`)* |
| `PATCH /api/sources/{id}/toggle` | Habilitar/deshabilitar fuente *(admin)* |
| `GET /api/admin/stats` | Estadísticas del sistema *(admin)* |
| `POST /api/admin/run-ingestion` | Ingestión manual *(admin)* |
| `GET /api/health` | Estado de la aplicación |
| `GET /api/docs` | Swagger UI |

---

## Limitaciones conocidas

- **Sin autenticación de usuario**: los favoritos se guardan en `localStorage` del navegador.
- **SQLite**: adecuado para uso personal. Para múltiples usuarios concurrentes, usar PostgreSQL (`DATABASE_URL=postgresql+asyncpg://...` + `pip install asyncpg`).
- **Traducción**: los artículos en inglés se muestran en su idioma original hasta que se configura un proveedor.
- **RT (ES)**: incluida con fiabilidad reducida (0.45) como fuente de contraste editorial.
