# ============================================================
# Historia — perfil de preferencias personales
#
# Edita este archivo para ajustar las preferencias sin tocar
# el algoritmo de puntuación (historia_scorer.py).
#
# Estructura:
#   FEATURED_THRESHOLD / RELEVANT_THRESHOLD — umbrales
#   WEIGHTS                                 — pesos por dimensión
#   PRIORITY_HIGH / PRIORITY_MEDIUM         — temas de interés
#   EXCLUDED_TOPICS                         — prehistoria (afinidad mínima)
#   DEPTH_SIGNALS                           — indicadores de rigor
#   SUPERFICIALITY_SIGNALS                  — indicadores de pobreza
#   HISTORIOGRAPHIC_SIGNALS                 — aportación de conocimiento
#   QUALITY_SIGNALS                         — calidad documental en texto
#   ACADEMIC_SOURCE_PATTERNS                — patrones en URL/nombre de fuente
# ============================================================

# ---------------------------------------------------------------------------
# Umbrales de clasificación (solo para Historia)
# No afectan a las demás categorías.
# ---------------------------------------------------------------------------
FEATURED_THRESHOLD = 0.70   # puntuación >= Destacada
RELEVANT_THRESHOLD = 0.45   # puntuación >= Relevante; < Seguimiento

# ---------------------------------------------------------------------------
# Pesos de las dimensiones (deben sumar 1.0)
# ---------------------------------------------------------------------------
WEIGHTS = {
    "thematic_affinity":    0.40,  # coincidencia con mis intereses
    "content_depth":        0.25,  # profundidad y calidad del contenido
    "historiographic":      0.20,  # interés historiográfico y aportación
    "documentary_quality":  0.15,  # calidad documental y solidez de fuentes
}

# ---------------------------------------------------------------------------
# Temas de MÁXIMA prioridad — historia de España y la Hispanidad
#
# Un artículo que trate SUSTANCIALMENTE alguno de estos temas obtendrá
# una afinidad alta. Añadir un término aquí requiere que el artículo
# verse realmente sobre el tema, no que lo mencione de pasada.
# ---------------------------------------------------------------------------
PRIORITY_HIGH = [
    # Hispania / Hispanidad
    "hispania", "hispano", "hispánica", "hispanidad", "hispánico",
    # Visigodos
    "visigodo", "visigodos", "visigótico", "reino visigodo",
    # Al-Ándalus
    "al-ándalus", "al ándalus", "andalusí", "omeya", "omeyas",
    "califato", "califato de córdoba", "emirato de córdoba", "taifa", "taifas",
    # Reconquista
    "reconquista", "reconquistador",
    "cruzada de las navas", "las navas de tolosa",
    # Reinos hispanos medievales
    "corona de castilla", "corona de aragón", "corona de navarra",
    "reino de castilla", "reino de aragón", "reino de navarra", "reino de león",
    "reino de granada", "granada nazarí",
    "castellano-leonés", "castilla", "aragón", "navarra",
    # Personajes de la Reconquista y unión dinástica
    "reyes católicos", "isabel la católica", "fernando el católico",
    "el cid", "rodrigo díaz de vivar",
    "jaime i", "jaime ii", "alfonso x", "alfonso viii",
    "ramón berenguer",
    # Monarquía hispánica y Siglo de Oro
    "monarquía hispánica", "corona española", "imperio español",
    "carlos i", "carlos v", "felipe ii", "felipe iii", "felipe iv", "felipe v",
    "siglo de oro",
    # Conquista y expansión atlántica
    "descubrimiento de américa", "conquista de américa", "conquista española",
    "hernán cortés", "francisco pizarro",
    # Instituciones y derecho
    "fuero", "fueros", "carta puebla",
    # Pueblos prerromanos de Hispania
    "celtíberos", "celtíbero", "celtibérico", "íberos", "ibérico", "ibérica",
    # Hispania romana
    "hispania romana", "hispano-romano", "romanización",
    # Carlismo
    "guerra carlista", "guerras carlistas", "carlismo", "carlista",
    # Cultura y convivencia
    "mozárabe", "mudéjar", "sefardí",
    "convivencia", "tres culturas",
    "repoblación medieval",
    "edad media española", "medieval hispánico",
    # Contexto ibérico medieval (Portugal en relación a Castilla/Aragón)
    "luso-castellano", "luso-aragonés",
]

# ---------------------------------------------------------------------------
# Temas de GRAN interés
#
# Historia militar, Segunda Guerra Mundial, Roma, Iglesia, personajes...
# ---------------------------------------------------------------------------
PRIORITY_MEDIUM = [
    # Historia militar general
    "historia militar", "batalla", "asedio", "campaña militar",
    "estrategia militar", "táctica militar",
    "cruzada", "cruzadas",
    "legión romana",
    # Primera y Segunda Guerra Mundial
    "primera guerra mundial", "gran guerra",
    "segunda guerra mundial", "wwii", "nazismo", "tercer reich",
    "holocausto", "operación barbarroja", "desembarco de normandía",
    "hitler",
    # Roma y mundo clásico
    "imperio romano", "república romana", "senado romano",
    "julio césar", "césar", "augusto", "cicerón",
    "grecia clásica", "atenas", "esparta",
    "antiguo egipto", "faraón",
    "mesopotamia", "babilonia", "persia",
    # Otros imperios y civilizaciones
    "imperio bizantino", "imperio otomano",
    "vikingo", "vikingos", "nórdico", "nórdicos",
    "godo", "franco", "carolingio", "plantagenet",
    "habsburgo", "borbón",
    # Historia política e imperios
    "historia política", "geopolítica histórica", "historia de los imperios",
    "dinastía",
    # Iglesia y christianismo
    "historia de la iglesia", "historia del cristianismo",
    "papado", "pontificado", "concilio",
    "orden religiosa", "orden militar",
    "templarios", "hospitalarios",
    "monasterio", "catedral", "diócesis",
    "monacato",
    # Inquisición
    "inquisición", "santa inquisición", "inquisidor", "tribunal de la fe",
    # Hagiografía y santos
    "hagiografía", "canonización", "mártir", "martirio",
    "vida de los santos",
    # Personajes y narrativa histórica
    "personaje histórico", "conspiración histórica",
    "intriga política histórica", "asesinato político histórico",
    "biografía histórica",
]

# ---------------------------------------------------------------------------
# Temas EXCLUIDOS
#
# Artículos centrados PRINCIPALMENTE en estos temas reciben afinidad
# mínima (0.05). Si el artículo solo los menciona de pasada, el resto
# del contenido puede compensar.
# ---------------------------------------------------------------------------
EXCLUDED_TOPICS = [
    "prehistoria", "prehistórico", "prehistórica",
    "homo sapiens", "homo erectus", "homo heidelbergensis",
    "australopithecus", "hominido", "homínido",
    "paleolítico", "neolítico", "calcolítico", "mesolítico",
    "megalítico", "dólmen", "cromañón", "neandertal",
    "edad del bronce", "edad del cobre", "edad del hierro",
]

# ---------------------------------------------------------------------------
# Señales de PROFUNDIDAD y rigor académico
#
# Indican que el artículo explica causas, consecuencias, contexto o
# evidencias. Se suman a la puntuación de profundidad.
# ---------------------------------------------------------------------------
DEPTH_SIGNALS = [
    "causas", "consecuencias",
    "contexto histórico", "contexto político",
    "análisis histórico", "análisis de",
    "se analiza", "se examina", "se estudia", "se evalúa",
    "investigación histórica", "estudio histórico",
    "historiografía", "debate historiográfico",
    "interpretación histórica", "revisión histórica",
    "fuentes primarias", "fuentes históricas",
    "crónica medieval", "crónicas",
    "manuscrito", "documento histórico", "archivo histórico",
    "excavación arqueológica", "yacimiento arqueológico",
    "datación", "cronología", "evidencia arqueológica",
    "profesor", "catedrático", "investigador", "historiador", "arqueólogo",
    "publicación académica", "revista histórica", "monografía", "tesis doctoral",
]

# ---------------------------------------------------------------------------
# Señales de SUPERFICIALIDAD y sensacionalismo
#
# Reducen la puntuación de profundidad.
# ---------------------------------------------------------------------------
SUPERFICIALITY_SIGNALS = [
    "curiosidades", "curiosidades históricas", "sabías que",
    "top 10", "top 5", "top 15", "top 20",
    "los mejores", "los peores", "lista de", "ranking de",
    "impactante", "increíble", "alucinante", "te sorprenderá",
    "viral", "sorprendente historia de",
]

# ---------------------------------------------------------------------------
# Señales de INTERÉS HISTORIOGRÁFICO
#
# Indican que el artículo aporta conocimiento nuevo o debate relevante.
# ---------------------------------------------------------------------------
HISTORIOGRAPHIC_SIGNALS = [
    "nuevo hallazgo", "nuevas evidencias", "nueva interpretación",
    "reciente descubrimiento", "recientes excavaciones",
    "debate historiográfico", "controversia histórica",
    "fuente inédita", "documento inédito", "manuscrito inédito",
    "descifrado", "traducido", "localizado",
    "por primera vez", "primera evidencia",
]

# ---------------------------------------------------------------------------
# Señales de CALIDAD DOCUMENTAL en el texto
# ---------------------------------------------------------------------------
QUALITY_SIGNALS = [
    "csic", "ucm", "universidad complutense",
    "consejo superior de investigaciones", "instituto de historia",
    "revista científica", "publicación académica",
    "real academia", "biblioteca nacional", "archivo nacional",
    "según las fuentes", "fuentes documentales",
]

# ---------------------------------------------------------------------------
# Patrones en URL o nombre de fuente que indican origen académico
# ---------------------------------------------------------------------------
ACADEMIC_SOURCE_PATTERNS = [
    "csic.es", "ucm.es", "uned.es", "unirioja.es",
    "dialnet", "redalyc",
    "csic", "ucm", "universidad", "universidad complutense",
]
