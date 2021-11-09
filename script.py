from resources.lib.refresher import refresh
from resources.lib.settings import Settings


settings = Settings()
refresh(clean=settings.manual.clean)
