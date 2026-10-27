# ============================================================
# Catolicismo y Tradicionalismo — perfil de preferencias
#
# Edita este archivo para ajustar las preferencias sin tocar
# el algoritmo de puntuación (catolicismo_scorer.py).
#
# Estructura:
#   FEATURED_THRESHOLD / RELEVANT_THRESHOLD — umbrales
#   WEIGHTS                                 — pesos por dimensión
#   PRIORITY_HIGH / PRIORITY_MEDIUM         — temas de interés
#   DEPTH_SIGNALS                           — indicadores de profundidad teológica
#   SUPERFICIALITY_SIGNALS                  — indicadores de sensacionalismo
#   ECCLESIAL_CONTEXT_SIGNALS               — enraizamiento en tradición y magisterio
#   QUALITY_SIGNALS                         — calidad en texto
#   TRUSTED_SOURCE_PATTERNS                 — patrones de fuentes católicas de confianza
# ============================================================

# ---------------------------------------------------------------------------
# Umbrales de clasificación (solo para Catolicismo)
# ---------------------------------------------------------------------------
FEATURED_THRESHOLD = 0.72   # puntuación >= Destacada
RELEVANT_THRESHOLD = 0.48   # puntuación >= Relevante; < Seguimiento

# ---------------------------------------------------------------------------
# Pesos de las dimensiones (deben sumar 1.0)
# ---------------------------------------------------------------------------
WEIGHTS = {
    "thematic_affinity":    0.40,
    "doctrinal_depth":      0.25,
    "ecclesial_context":    0.20,
    "source_quality":       0.15,
}

# ---------------------------------------------------------------------------
# Temas de MÁXIMA prioridad — liturgia tradicional, tomismo, doctrina
#
# Artículos que traten sustancialmente estos temas obtienen afinidad alta.
# ---------------------------------------------------------------------------
PRIORITY_HIGH = [
    # Misa tradicional / rito tridentino
    "misa tradicional", "forma extraordinaria", "rito tridentino", "tridentino",
    "motu proprio", "summorum pontificum", "traditionis custodes",
    "misa de san pío v", "misa gregoriana", "vetus ordo",
    # Tomismo / filosofía escolástica
    "tomismo", "tomista", "santo tomás de aquino", "tomás de aquino",
    "escolástica", "escolástico",
    "filosofía perenne", "metafísica tomista",
    # Catecismo y doctrina
    "catecismo de la iglesia", "catequesis",
    "doctrina de la fe", "congregación para la doctrina de la fe",
    # Canto gregoriano y música sacra
    "canto gregoriano", "gregoriano", "polifonía sacra", "música sacra",
    # Tradición y magisterio
    "tradición católica", "magisterio de la iglesia",
    "dogma católico", "doctrina católica", "tradición apostólica",
    # Debate sobre el Concilio Vaticano II
    "concilio vaticano ii", "posconciliar",
    # Espiritualidad litúrgica
    "adoración eucarística", "santísimo sacramento",
    "hora santa", "eucaristía",
    # Fraternidad San Pío X
    "fraternidad san pío x", "fsspx", "lefebvre", "écône",
    # Términos del debate litúrgico-doctrinal posconciliar
    "novus ordo",            # término tradicionalista para la misa de Pablo VI
    "misa en latín", "misa latina",
    "reforma litúrgica",     # aparece en artículos sobre el cambio posconciliar
    "sinodalidad",           # debate sobre gobierno eclesial; tema central para tradicionalistas
    "infalibilidad",         # concepto doctrinal clave en argumentación tradicional
]

# ---------------------------------------------------------------------------
# Temas de GRAN interés — historia de la Iglesia, santos, actualidad vaticana
# ---------------------------------------------------------------------------
PRIORITY_MEDIUM = [
    # Actualidad vaticana
    "papa", "francisco", "benedicto xvi", "juan pablo ii",
    "vaticano", "santa sede", "curia romana",
    "obispo", "cardenal", "nuncio", "diócesis",
    # Santos y beatificaciones
    "canonización", "beatificación", "santo", "santa",
    "beato", "beata", "mártir cristiano", "mártires",
    # Historia de la Iglesia
    "historia de la iglesia", "historia eclesiástica",
    "concilio", "sínodo", "papado", "pontificado",
    "reforma protestante", "contrarreforma",
    # Órdenes religiosas
    "jesuitas", "dominicos", "franciscanos", "benedictinos",
    "carmelitas", "capuchinos", "opus dei",
    "monjes", "monasterio", "abadía", "convento",
    # Teología y pastoral
    "teología", "teólogo", "pastoral", "evangelización",
    "apologética",
    # Inquisición (interés histórico)
    "inquisición", "santa inquisición", "inquisidor",
    # Carlismo (conexión Iglesia–tradición española)
    "carlismo", "carlista",
    # Sedevacantismo (informativo)
    "sedevacantismo", "sede vacante",
    # Liturgia y año litúrgico
    "liturgia", "semana santa", "adviento", "cuaresma",
    "exégesis", "sagradas escrituras",
    # Iglesia en España
    "conferencia episcopal", "episcopado español",
    # Apologética y ecumenismo
    "ecumenismo", "diálogo interreligioso",
]

# ---------------------------------------------------------------------------
# Señales de PROFUNDIDAD teológica y doctrinal
# ---------------------------------------------------------------------------
DEPTH_SIGNALS = [
    "encíclica", "carta apostólica", "constitución apostólica",
    "exhortación apostólica", "decreto", "declaración",
    "padres de la iglesia", "padre de la iglesia",
    "concilio de trento", "primer concilio vaticano",
    "catecismo de la iglesia católica",
    "análisis teológico", "reflexión teológica",
    "fuentes patrísticas", "escritura y tradición",
    "se analiza", "se examina", "se estudia",
    "investigación", "debate teológico",
    "sacra scriptura", "patrística",
]

# ---------------------------------------------------------------------------
# Señales de SUPERFICIALIDAD o sensacionalismo
# ---------------------------------------------------------------------------
SUPERFICIALITY_SIGNALS = [
    "curiosidades", "sabías que",
    "top 10", "top 5", "lista de",
    "impactante", "increíble", "alucinante", "viral",
    "sorprendente", "te sorprenderá",
]

# ---------------------------------------------------------------------------
# Señales de CONTEXTO ECLESIAL — enraizamiento en tradición y magisterio
# ---------------------------------------------------------------------------
ECCLESIAL_CONTEXT_SIGNALS = [
    "magisterio", "sucesión apostólica", "infalibilidad",
    "dogma de fe", "ex cathedra",
    "patrística", "san agustín", "san jerónimo",
    "concilio de nicea", "concilio de trento",
    "iglesia primitiva", "iglesia apostólica",
    "escritura sagrada", "sagrada escritura",
    "nuevo testamento", "antiguo testamento",
]

# ---------------------------------------------------------------------------
# Señales de CALIDAD DOCUMENTAL en el texto
#
# "cardenal" y "obispo" se eliminan: son términos temáticos de prioridad
# media que aparecen sistemáticamente en noticias institucionales genéricas,
# lo que inflaba la dimensión source_quality de esas noticias hasta 1.000.
# ---------------------------------------------------------------------------
QUALITY_SIGNALS = [
    "teólogo", "doctor de la iglesia",
    "universidad pontificia", "pontificio",
    "congregación para", "dicastero",
    "según el magisterio", "según la doctrina",
    "documento oficial", "documento pontificio",
]

# ---------------------------------------------------------------------------
# Patrones en URL para reconocer medios TRADICIONALISTAS de confianza.
#
# Solo incluye publicaciones con orientación explícitamente tradicionalista.
# Vatican News y la CEE son fuentes institucionales legítimas pero no
# tradicionalistas; no reciben este bono para no amplificar su ya alto
# volumen de publicación.
# ---------------------------------------------------------------------------
TRUSTED_SOURCE_PATTERNS = [
    "infovaticana", "adelantelafe",
    "fsspx.news", "untradi", "periodicolaesperanza",
]

# ---------------------------------------------------------------------------
# Bono editorial para fuentes tradicionalistas con contenido pertinente.
#
# Se aplica en score_catolicismo_article() cuando:
#   - extra_config["editorial"] == TRADITIONALIST_EDITORIAL, Y
#   - la afinidad temática calculada es >= 0.60.
#
# Propósito: dar prioridad real a fuentes con orientación tradicional cuando
# su contenido toca los temas de alta o media prioridad del perfil.
# No se aplica a artículos de escasa afinidad temática para evitar que una
# fuente tradicionalista suba por el mero hecho de serlo.
# ---------------------------------------------------------------------------
TRADITIONALIST_EDITORIAL = "catolicismo_tradicional"
TRADITIONALIST_AFFINITY_BONUS = 0.12   # aumentado de 0.08; threshold en scorer bajado a 0.45
