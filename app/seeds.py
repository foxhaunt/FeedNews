"""Seed initial sources and categories into the database."""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal, init_db
from app.models import Source, Category

CATEGORIES = [
    {"slug": "historia", "name_es": "Historia", "name_en": "History", "icon": "📜", "order": 0},
    {"slug": "politica", "name_es": "Política", "name_en": "Politics", "icon": "🏛️", "order": 1},
    {"slug": "economia", "name_es": "Economía y mercados", "name_en": "Economy & Markets", "icon": "📈", "order": 2},
    {"slug": "geopolitica", "name_es": "Geopolítica", "name_en": "Geopolitics", "icon": "🌍", "order": 3},
    {"slug": "defensa", "name_es": "Defensa y conflictos", "name_en": "Defense & Conflicts", "icon": "⚔️", "order": 4},
    {"slug": "seguridad", "name_es": "Seguridad", "name_en": "Security", "icon": "🔒", "order": 5},
    {"slug": "tecnologia", "name_es": "Tecnología e IA", "name_en": "Technology & AI", "icon": "💻", "order": 6},
    {"slug": "ciencia", "name_es": "Ciencia y salud", "name_en": "Science & Health", "icon": "🔬", "order": 7},
    {"slug": "sociedad", "name_es": "Sociedad y tribunales", "name_en": "Society & Courts", "icon": "⚖️", "order": 8},
    {"slug": "energia", "name_es": "Energía y medioambiente", "name_en": "Energy & Environment", "icon": "🌱", "order": 9},
    {"slug": "sucesos", "name_es": "Sucesos y emergencias", "name_en": "Incidents & Emergencies", "icon": "🚨", "order": 10},
]

SOURCES = [
    # ── España ──────────────────────────────────────────────────────────────
    # Centroizquierda / progresistas
    {
        "name": "El País",
        "url": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
        "feed_type": "rss", "geographic_scope": "spain", "language": "es",
        "reliability_score": 0.9, "fetch_interval_minutes": 20,
        "extra_config": {"editorial": "centroizquierda"},
    },
    {
        "name": "El Diario",
        "url": "https://www.eldiario.es/rss/",
        "feed_type": "rss", "geographic_scope": "spain", "language": "es",
        "reliability_score": 0.55, "fetch_interval_minutes": 30,
        "enabled": False,
        "extra_config": {"editorial": "izquierda"},
    },
    {
        "name": "20 Minutos",
        "url": "https://www.20minutos.es/rss/",
        "feed_type": "rss", "geographic_scope": "spain", "language": "es",
        "reliability_score": 0.7, "fetch_interval_minutes": 25,
        "extra_config": {"editorial": "centroizquierda"},
    },
    # Centro / generalistas
    {
        "name": "La Vanguardia",
        "url": "https://www.lavanguardia.com/rss/home.xml",
        "feed_type": "rss", "geographic_scope": "spain", "language": "es",
        "reliability_score": 0.85, "fetch_interval_minutes": 25,
        "extra_config": {"editorial": "centro"},
    },
    {
        "name": "El Confidencial",
        "url": "https://rss.elconfidencial.com/espana/",
        "feed_type": "rss", "geographic_scope": "spain", "language": "es",
        "reliability_score": 0.8, "fetch_interval_minutes": 25,
        "extra_config": {"editorial": "centro"},
    },
    # Centroderecha / derecha
    {
        "name": "El Mundo",
        "url": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
        "feed_type": "rss", "geographic_scope": "spain", "language": "es",
        "reliability_score": 0.85, "fetch_interval_minutes": 20,
        "extra_config": {"editorial": "centroderecha"},
    },
    {
        "name": "El Español",
        "url": "https://www.elespanol.com/rss/",
        "feed_type": "rss", "geographic_scope": "spain", "language": "es",
        "reliability_score": 0.75, "fetch_interval_minutes": 25,
        "extra_config": {"editorial": "centroderecha"},
    },
    {
        "name": "ABC España",
        "url": "https://www.abc.es/rss/feeds/abc_EspanaEspana.xml",
        "feed_type": "rss", "geographic_scope": "spain", "language": "es",
        "reliability_score": 0.8, "fetch_interval_minutes": 25,
        "extra_config": {"editorial": "centroderecha"},
    },
    {
        "name": "The Objective",
        "url": "https://theobjective.com/feed/",
        "feed_type": "rss", "geographic_scope": "spain", "language": "es",
        "reliability_score": 0.75, "fetch_interval_minutes": 30,
        "extra_config": {"editorial": "centroderecha"},
    },
    {
        "name": "La Bandera",
        "url": "https://labandera.es/feed/",
        "feed_type": "rss", "geographic_scope": "spain", "language": "es",
        "reliability_score": 0.65, "fetch_interval_minutes": 30,
        "extra_config": {"editorial": "derecha"},
    },
    {
        "name": "OKDIARIO",
        "url": "https://okdiario.com/feed/",
        "feed_type": "rss", "geographic_scope": "spain", "language": "es",
        "reliability_score": 0.6, "fetch_interval_minutes": 30,
        "extra_config": {"editorial": "derecha"},
    },
    {
        "name": "La Gaceta",
        "url": "https://gaceta.es/feed/",
        "feed_type": "rss", "geographic_scope": "spain", "language": "es",
        "reliability_score": 0.6, "fetch_interval_minutes": 30,
        "extra_config": {"editorial": "derecha"},
    },
    # ── Europa ───────────────────────────────────────────────────────────────
    {
        "name": "Euronews (EN)",
        "url": "https://feeds.feedburner.com/euronews/en/news/",
        "feed_type": "rss", "geographic_scope": "europe", "language": "en",
        "reliability_score": 0.85, "fetch_interval_minutes": 20,
        "extra_config": {"editorial": "centro"},
    },
    {
        "name": "Euronews (ES)",
        "url": "https://feeds.feedburner.com/euronews/es/news/",
        "feed_type": "rss", "geographic_scope": "europe", "language": "es",
        "reliability_score": 0.85, "fetch_interval_minutes": 20,
        "extra_config": {"editorial": "centro"},
    },
    {
        "name": "POLITICO Europe",
        "url": "https://www.politico.eu/rss",
        "feed_type": "rss", "geographic_scope": "europe", "language": "en",
        "reliability_score": 0.9, "fetch_interval_minutes": 20,
        "extra_config": {"editorial": "centroderecha"},
    },
    {
        "name": "BBC Europe",
        "url": "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
        "feed_type": "rss", "geographic_scope": "europe", "language": "en",
        "reliability_score": 0.95, "fetch_interval_minutes": 20,
        "extra_config": {"editorial": "centro"},
    },
    {
        "name": "Deutsche Welle (EN)",
        "url": "https://rss.dw.com/rdf/rss-en-all",
        "feed_type": "rss", "geographic_scope": "europe", "language": "en",
        "reliability_score": 0.9, "fetch_interval_minutes": 25,
        "extra_config": {"editorial": "centro"},
    },
    {
        "name": "RFI English",
        "url": "https://www.rfi.fr/en/rss",
        "feed_type": "rss", "geographic_scope": "europe", "language": "en",
        "reliability_score": 0.85, "fetch_interval_minutes": 30,
        "extra_config": {"editorial": "centro"},
    },
    {
        "name": "Le Monde Diplomatique (ES)",
        "url": "https://mondiplo.com/spip.php?page=backend",
        "feed_type": "rss", "geographic_scope": "europe", "language": "es",
        "reliability_score": 0.85, "fetch_interval_minutes": 60,
        "extra_config": {"editorial": "izquierda"},
    },
    # ── Internacional ────────────────────────────────────────────────────────
    # Reuters: DNS no resuelve en este entorno; documentado como no disponible
    {
        "name": "BBC World",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "feed_type": "rss", "geographic_scope": "international", "language": "en",
        "reliability_score": 0.95, "fetch_interval_minutes": 15,
        "extra_config": {"editorial": "centro"},
    },
    {
        "name": "Al Jazeera",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "feed_type": "rss", "geographic_scope": "international", "language": "en",
        "reliability_score": 0.8, "fetch_interval_minutes": 20,
        "extra_config": {"editorial": "no_determinada"},
    },
    {
        "name": "The Guardian World",
        "url": "https://www.theguardian.com/world/rss",
        "feed_type": "rss", "geographic_scope": "international", "language": "en",
        "reliability_score": 0.9, "fetch_interval_minutes": 20,
        "extra_config": {"editorial": "centroizquierda"},
    },
    {
        "name": "France 24 (EN)",
        "url": "https://www.france24.com/en/rss",
        "feed_type": "rss", "geographic_scope": "international", "language": "en",
        "reliability_score": 0.85, "fetch_interval_minutes": 20,
        "extra_config": {"editorial": "centro"},
    },
    {
        "name": "Deutsche Welle World (EN)",
        "url": "https://rss.dw.com/rdf/rss-en-world",
        "feed_type": "rss", "geographic_scope": "international", "language": "en",
        "reliability_score": 0.9, "fetch_interval_minutes": 25,
        "extra_config": {"editorial": "centro"},
    },
    {
        "name": "NPR News",
        "url": "https://feeds.npr.org/1001/rss.xml",
        "feed_type": "rss", "geographic_scope": "international", "language": "en",
        "reliability_score": 0.88, "fetch_interval_minutes": 30,
        "extra_config": {"editorial": "centroizquierda"},
    },
    {
        "name": "RT (ES)",
        "url": "https://actualidad.rt.com/rss",
        "feed_type": "rss", "geographic_scope": "international", "language": "es",
        "reliability_score": 0.45, "fetch_interval_minutes": 30,
        "extra_config": {"editorial": "proruso"},
    },
    # Agencia EFE: feed oficial sin acceso libre verificado; se mantiene desactivada
    {
        "name": "Agencia EFE",
        "url": "https://www.efe.com/efe/espana/portada/1/rss",
        "feed_type": "rss", "geographic_scope": "international", "language": "es",
        "reliability_score": 0.9, "fetch_interval_minutes": 15,
        "enabled": False,
        "extra_config": {"editorial": "agencia", "note": "feed oficial sin acceso libre verificado"},
    },
    # ── Historia ─────────────────────────────────────────────────────────────
    {
        "name": "Historia National Geographic",
        "url": "https://historia.nationalgeographic.com.es/feed",
        "feed_type": "rss", "geographic_scope": "spain", "language": "es",
        "reliability_score": 0.9, "fetch_interval_minutes": 120,
        "enabled": False,
        "extra_config": {
            "primary_category": "historia",
            "note": "feed devuelve 403 Forbidden; bloqueado por CDN Akamai",
        },
    },
    {
        "name": "El Reto Histórico",
        "url": "https://elretohistorico.com/feed/",
        "feed_type": "rss", "geographic_scope": "spain", "language": "es",
        "reliability_score": 0.75, "fetch_interval_minutes": 120,
        "extra_config": {"primary_category": "historia", "editorial": "divulgacion"},
    },
    {
        "name": "Muy Interesante Historia",
        "url": "https://muyinteresante.okdiario.com/historia/feed/",
        "feed_type": "rss", "geographic_scope": "spain", "language": "es",
        "reliability_score": 0.8, "fetch_interval_minutes": 120,
        "extra_config": {"primary_category": "historia", "editorial": "divulgacion"},
    },
    # CSIC Hispania Sacra: certificado SSL inválido; ssl_verify=False necesario
    {
        "name": "Hispania Sacra (CSIC)",
        "url": "https://hispaniasacra.revistas.csic.es/index.php/hispaniasacra/gateway/plugin/WebFeedGatewayPlugin/rss2",
        "feed_type": "rss", "geographic_scope": "spain", "language": "es",
        "reliability_score": 0.9, "fetch_interval_minutes": 1440,
        "extra_config": {
            "primary_category": "historia",
            "editorial": "academico",
            "ssl_verify": False,
        },
    },
    # CSIC Hispania: certificado SSL inválido; ssl_verify=False necesario
    {
        "name": "Hispania (CSIC)",
        "url": "https://hispania.revistas.csic.es/index.php/hispania/gateway/plugin/WebFeedGatewayPlugin/rss2",
        "feed_type": "rss", "geographic_scope": "spain", "language": "es",
        "reliability_score": 0.9, "fetch_interval_minutes": 1440,
        "extra_config": {
            "primary_category": "historia",
            "editorial": "academico",
            "ssl_verify": False,
        },
    },
    {
        "name": "En la España Medieval (UCM)",
        "url": "https://revistas.ucm.es/index.php/ELEM/gateway/plugin/WebFeedGatewayPlugin/rss2",
        "feed_type": "rss", "geographic_scope": "spain", "language": "es",
        "reliability_score": 0.9, "fetch_interval_minutes": 1440,
        "extra_config": {"primary_category": "historia", "editorial": "academico"},
    },
]


async def seed():
    await init_db()
    async with AsyncSessionLocal() as session:
        # Categories
        for cat_data in CATEGORIES:
            existing = (await session.execute(
                select(Category).where(Category.slug == cat_data["slug"])
            )).scalar_one_or_none()
            if not existing:
                session.add(Category(**cat_data))

        # Sources — upsert by URL first, then by name to handle URL changes
        for src_data in SOURCES:
            by_url = (await session.execute(
                select(Source).where(Source.url == src_data["url"])
            )).scalar_one_or_none()

            if by_url:
                # URL already present — update mutable fields
                by_url.name = src_data["name"]
                by_url.reliability_score = src_data["reliability_score"]
                by_url.fetch_interval_minutes = src_data["fetch_interval_minutes"]
                by_url.enabled = src_data.get("enabled", True)
                by_url.extra_config = src_data.get("extra_config", {})
                continue

            # URL not found — check if a source with the same name exists (URL may have changed)
            by_name = (await session.execute(
                select(Source).where(Source.name == src_data["name"])
            )).scalar_one_or_none()

            if by_name:
                # Update all fields including URL
                by_name.url = src_data["url"]
                by_name.geographic_scope = src_data["geographic_scope"]
                by_name.language = src_data["language"]
                by_name.reliability_score = src_data["reliability_score"]
                by_name.fetch_interval_minutes = src_data["fetch_interval_minutes"]
                by_name.enabled = src_data.get("enabled", True)
                # Reset error counters so the source is retried immediately
                by_name.last_error = None
                by_name.consecutive_errors = 0
                by_name.extra_config = src_data.get("extra_config", {})
            else:
                session.add(Source(**{k: v for k, v in src_data.items()}))

        await session.commit()
        print("Seeding completed.")


if __name__ == "__main__":
    asyncio.run(seed())
