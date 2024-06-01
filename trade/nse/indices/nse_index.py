from dataclasses import dataclass
from typing import Literal
from trade.nse.data_generics import NSEDataGeneric
from trade.nse.indices.nse_indices_config import (
    INDEX_NAME_TYPE,
    INDICES,
    NSEIndexConfig,
)


@dataclass
class NSEIndex(NSEDataGeneric):

    symbol: INDEX_NAME_TYPE
    dated: str

    def __post_init__(self):
        self.symbol = self.symbol.upper()
        self._config = NSEIndexConfig(self.dated)
        quotes = self._config.get_quote_index(self.symbol)

        for key, value in quotes.items():
            if key not in ("symbol", "dated"):
                setattr(self, key, value)


@dataclass
class SpotIndices:

    dated: str

    def __post_init__(self):

        self._config = NSEIndexConfig(self.dated)
        self.symbols = [NSEIndex(i, self.dated) for i in INDICES]
        self.vix = self._config.get_vix()
        self.metrics = self._config.get_index_metrics()
