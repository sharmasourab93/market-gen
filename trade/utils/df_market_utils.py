from abc import ABC

from pandas import DataFrame, set_option

set_option("mode.chained_assignment", None)


class MarketDFUtils(ABC):

    def data_remove_quotes_with_na(
        self, data: DataFrame, column: str = "close"
    ) -> DataFrame:
        return data.loc[~data[column].isna(), :]

    def calculate_pct_change(
        self,
        data: DataFrame,
        column1: str = "close",
        column2: str = "prev_close",
        change_column: str = "pct_change",
    ) -> DataFrame:

        data.loc[:, change_column] = (
            (data[column1] - data[column2]) / data[column2]
        ) * 100

        return data
