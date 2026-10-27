from abc import ABC, abstractmethod
from typing import Optional


class BaseTranslator(ABC):
    @abstractmethod
    async def translate(self, text: str, source_lang: str, target_lang: str = "es") -> Optional[str]:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    def available(self) -> bool:
        return True
