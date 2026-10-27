# 📰 feed-news

Agregador personal de noticias con relevancia configurable, perfil histórico y perfil de catolicismo propios.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)
![Tests](https://img.shields.io/badge/tests-218%20passing-brightgreen)
![Fuentes](https://img.shields.io/badge/fuentes-37%20activas-blueviolet)

---

## Contenido

1. [Fuentes de noticias](#1-fuentes-de-noticias)
2. [Distribución editorial](#2-distribución-editorial)
3. [Categorías temáticas](#3-categorías-temáticas)
4. [Sistema de relevancia](#4-sistema-de-relevancia)
5. [Perfil de Historia](#5-perfil-de-historia)
6. [Perfil de Catolicismo](#6-perfil-de-catolicismo-y-tradicionalismo)
7. [Configuración](#7-configuración)
8. [Instalación](#8-instalación)
9. [API](#9-api)

---

## 1. Fuentes de noticias

37 fuentes activas agrupadas por ámbito geográfico.

### España

| Fuente | Línea editorial | Estado |
|---|---|---|
| El País | centroizquierda | ✅ activa |
| 20 Minutos | centroizquierda | ✅ activa |
| La Vanguardia | centro | ✅ activa |
| El Confidencial | centro | ✅ activa |
| El Mundo | centroderecha | ✅ activa |
| El Español | centroderecha | ✅ activa |
| ABC España | centroderecha | ✅ activa |
| The Objective | centroderecha | ✅ activa |
| La Bandera | derecha | ✅ activa |
| OKDIARIO | derecha | ✅ activa |
| La Gaceta | derecha | ✅ activa |
| El Diario | izquierda | ❌ desactivada |

### Europa

| Fuente | Idioma | Línea editorial |
|---|---|---|
| BBC Europe | EN | centro |
| POLITICO Europe | EN | centroderecha |
| Deutsche Welle (EN) | EN | centro |
| Euronews (ES) | ES | centro |
| Euronews (EN) | EN | centro |
| RFI English | EN | centro |
| Le Monde Diplomatique (ES) | ES | izquierda |

### Internacional

| Fuente | Idioma | Línea editorial |
|---|---|---|
| BBC World | EN | centro |
| The Guardian World | EN | centroizquierda |
| Deutsche Welle World | EN | centro |
| France 24 (EN) | EN | centro |
| NPR News | EN | centroizquierda |
| Al Jazeera | EN | no determinado |
| RT (ES) | ES | proruso |

### Historia (fuentes académicas)

| Fuente | Institución | Tipo | Fetch |
|---|---|---|---|
| El Reto Histórico | — | divulgación | 120 min |
| Muy Interesante Historia | — | divulgación | 120 min |
| Hispania Sacra | CSIC | académica | 1440 min |
| Hispania | CSIC | académica | 1440 min |
| En la España Medieval | UCM | académica | 1440 min |

### Catolicismo y Tradicionalismo

| Fuente | Orientación | Fetch |
|---|---|---|
| InfoVaticana | catolicismo tradicional | 60 min |
| Adelante la Fe | catolicismo tradicional | 120 min |
| FSSPX.News (ES) | FSSPX | 120 min |
| Periódico La Esperanza | catolicismo tradicional | 120 min |
| Un Tradi en el Novus Ordo | catolicismo tradicional | 120 min |
| Vatican News (ES) | vaticano oficial | 30 min |
| Conferencia Episcopal Española | episcopal oficial | 120 min |

---

## 2. Distribución editorial

Fuentes de España (excluida El Diario):

| Posición | Peso en feed |
|---|---|
| Centroderecha | ~36 % |
| Centro | ~18 % |
| Centroizquierda | ~18 % |
| Derecha | ~18 % |
| Izquierda | ~9 % |

**HHI ≈ 0.21** — concentración moderada (baja < 0.15 · moderada 0.15–0.25 · alta > 0.25).

---

## 3. Categorías temáticas

Cada artículo recibe hasta 3 categorías mediante coincidencia de palabras clave con límites de palabra. Las fuentes con categoría primaria forzada (Historia, Catolicismo) exigen el **doble del umbral** en categorías secundarias para evitar falsos positivos.

`⚔️ Defensa` `🌍 Geopolítica` `🏛️ Política` `📈 Economía` `🔬 Ciencia` `💻 Tecnología` `🔋 Energía` `🏥 Salud` `🌿 Medioambiente` `🛡️ Seguridad` `⚖️ Sociedad` `🚨 Sucesos` `📜 Historia` `✝️ Catolicismo`

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

Todos los artículos reciben `relevance_score ∈ [0, 1]`. Historia y Catolicismo usan sus propios algoritmos (§5 y §6). El resto comparte:

```
puntuación = 0.5 (base)
  + recencia    → <1 h: +0.20 · <6 h: +0.15 · <24 h: +0.10 · <72 h: +0.05
  + tier-1 kws  → guerra, atentado, bomba, terremoto … +0.08/hit (máx +0.20)
  + tier-2 kws  → elecciones, crisis, sanciones, OTAN … +0.03/hit (máx +0.09)
  × categoría   → ×0.95 – ×1.25
  × geo         → ×1.05 España · ×1.02 Europa · ×1.00 Internacional

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
| **Documental** | `csic` · `ucm` · `universidad` · `real academia` | — |

### Distribución actual (99 artículos)

| Nivel | Artículos |
|---|---|
| Destacada | 4 |
| Relevante | 68 |
| Seguimiento | 27 |

> **Destacados:** mudéjares del Reino de Castilla (0.765) · lazos diplomáticos en la Corona de Castilla (0.765) · diplomacia de la Corona de Aragón / Guerra de los Dos Pedros (0.737) · provisiones episcopales de Orihuela (0.707)

Para ajustar las preferencias edita `app/processing/historia_profile.py` (solo datos, sin lógica) y recalcula:

```bash
python -m app.maintenance rescore_historia
```

---

## 6. Perfil de Catolicismo y Tradicionalismo

Los artículos de catolicismo usan el mismo algoritmo de cuatro dimensiones que Historia, con keywords centrados en liturgia, doctrina y espiritualidad tradicional.

### Fórmula

```
puntuación = 0.40 × afinidad_temática
           + 0.25 × profundidad_doctrinal
           + 0.20 × contexto_eclesial
           + 0.15 × calidad_de_fuente
           + recencia (máx +0.05)

Destacada  ≥ 0.72
Relevante  ≥ 0.48
Seguimiento < 0.48
```

### Temas de máxima prioridad *(afinidad alta)*

Liturgia tradicional, tomismo y doctrina — artículos dedicados a estos temas puntúan hasta 0.85 en afinidad temática.

`misa tradicional` `forma extraordinaria` `rito tridentino` `motu proprio` `summorum pontificum` `traditionis custodes` `tomismo` `santo tomás de aquino` `escolástica` `catecismo de la iglesia` `canto gregoriano` `música sacra` `tradición católica` `magisterio de la iglesia` `dogma católico` `fraternidad san pío x` `fsspx` `adoración eucarística`

### Temas de gran interés *(afinidad media)*

`papa` `vaticano` `santa sede` `canonización` `beatificación` `historia de la iglesia` `concilio` `jesuitas` `dominicos` `benedictinos` `teología` `pastoral` `inquisición` `carlismo` `sedevacantismo` `liturgia` `conferencia episcopal`

### Indicadores de calidad

| Dimensión | Señales positivas | Señales negativas |
|---|---|---|
| **Profundidad** | `encíclica` · `padres de la iglesia` · `análisis teológico` · `patrística` · Resumen >400 chars | `top 10` · `curiosidades` · `viral` · `alucinante` |
| **Contexto eclesial** | `magisterio` · `sucesión apostólica` · `dogma de fe` · `concilio de trento` | — |
| **Calidad** | `teólogo` · `doctor de la iglesia` | — |

Para ajustar las preferencias edita `app/processing/catolicismo_profile.py` (solo datos, sin lógica) y recalcula:

```bash
python -m app.maintenance rescore_catolicismo
```

---

## 7. Configuración

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
python -m app.maintenance reclassify_historia      # recategorizar artículos históricos
python -m app.maintenance rescore_historia         # recalcular puntuaciones de historia
python -m app.maintenance reclassify_catolicismo   # recategorizar artículos de catolicismo
python -m app.maintenance rescore_catolicismo      # recalcular puntuaciones de catolicismo
```

---

## 8. Instalación

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
pytest tests/ -q                                  # suite completa (218 tests)
pytest tests/test_historia_scoring.py -v          # perfil de historia (15 tests)
pytest tests/test_catolicismo_scoring.py -v       # perfil de catolicismo (16 tests)
```

---

## 9. API

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
- **RT (ES)**: incluida como fuente de contraste editorial.
- **InfoCatólica / Apostolado San Vicente Ferrer**: sin feed RSS verificado — no incorporadas.
