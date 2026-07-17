
import importlib
import sys
from pathlib import Path

from core.settings import (
    KRONOS_MODEL_NAME,
    KRONOS_REPO_PATH,
    KRONOS_TOKENIZER_NAME,
)
from engines.forecast_provider import ForecastProvider


class KronosUnavailableError(RuntimeError):
    pass


class KronosForecastProvider(ForecastProvider):
    """Optional Kronos-backed forecast provider."""

    required_fields = ("date", "open", "high", "low", "close", "volume")
    numeric_fields = ("open", "high", "low", "close", "volume", "amount")
    minimum_history_rows = 60

    def __init__(
        self,
        repo_path=KRONOS_REPO_PATH,
        model_name=KRONOS_MODEL_NAME,
        tokenizer_name=KRONOS_TOKENIZER_NAME,
        pred_len=7,
    ):
        self.repo_path = repo_path or ""
        self.model_name = model_name
        self.tokenizer_name = tokenizer_name
        self.pred_len = pred_len
        self._model = None
        self._tokenizer = None
        self._predictor = None
        self._kronos_classes = None

    @classmethod
    def is_available(cls, repo_path=KRONOS_REPO_PATH):
        try:
            cls._add_repo_path(repo_path)
            cls._import_kronos_classes()
        except KronosUnavailableError:
            return False

        return True

    def forecast(self, stock):
        if not self.is_available(self.repo_path):
            raise KronosUnavailableError(
                "Kronos is not available. Set KRONOS_REPO_PATH or install "
                "Kronos dependencies, then select FORECAST_PROVIDER='kronos'."
            )

        payload = self._to_kronos_payload(stock)
        dataframe = self._to_kronos_dataframe(payload["dataframe"])
        prediction = self._run_kronos_prediction(dataframe)
        predicted_close = self._extract_predicted_close(prediction)

        return self._score_prediction(
            historical_close=payload["dataframe"]["close"],
            predicted_close=predicted_close,
        )

    def _to_kronos_payload(self, stock):
        history = self._extract_history(stock)
        self._validate_history(history)

        rows = [self._map_ohlcv_row(row) for row in history]
        self._validate_sorted_timestamps(rows)
        self._validate_numeric_columns(rows)

        return {
            "dataframe": self._to_dataframe_columns(rows),
        }

    def _to_kronos_dataframe(self, dataframe_columns):
        import pandas as pd

        dataframe = pd.DataFrame(dataframe_columns)
        dataframe["timestamps"] = pd.to_datetime(dataframe["timestamps"])

        return dataframe

    def _run_temporary_kronos_prediction(
        self,
        dataframe,
        pred_len=3,
        tokenizer_name="NeoQuasar/Kronos-Tokenizer-base",
        model_name="NeoQuasar/Kronos-small"
    ):
        # TODO: Move this into forecast() only after Kronos is installed,
        # configured, and explicitly enabled through ForecastEngine.
        from model import Kronos, KronosPredictor, KronosTokenizer

        tokenizer = KronosTokenizer.from_pretrained(tokenizer_name)
        model = Kronos.from_pretrained(model_name)
        predictor = KronosPredictor(model, tokenizer, max_context=512)

        x_df = dataframe[[
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
        ]]
        x_timestamp = dataframe["timestamps"]
        y_timestamp = self._future_timestamps(x_timestamp, pred_len)

        return predictor.predict(
            df=x_df,
            x_timestamp=x_timestamp,
            y_timestamp=y_timestamp,
            pred_len=pred_len,
            T=1.0,
            top_p=0.9,
            sample_count=1
        )

    def _run_kronos_prediction(self, dataframe):
        predictor = self._load_predictor()
        x_df = dataframe[[
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
        ]]
        x_timestamp = dataframe["timestamps"]
        y_timestamp = self._future_timestamps(x_timestamp, self.pred_len)

        return predictor.predict(
            df=x_df,
            x_timestamp=x_timestamp,
            y_timestamp=y_timestamp,
            pred_len=self.pred_len,
            T=1.0,
            top_p=0.9,
            sample_count=1
        )

    def _load_predictor(self):
        if self._predictor is not None:
            return self._predictor

        Kronos, KronosPredictor, KronosTokenizer = self._load_kronos_classes()
        self._tokenizer = KronosTokenizer.from_pretrained(self.tokenizer_name)
        self._model = Kronos.from_pretrained(self.model_name)
        self._predictor = KronosPredictor(
            self._model,
            self._tokenizer,
            max_context=512
        )

        return self._predictor

    def _load_kronos_classes(self):
        if self._kronos_classes is None:
            self._add_repo_path(self.repo_path)
            self._kronos_classes = self._import_kronos_classes()

        return self._kronos_classes

    @staticmethod
    def _add_repo_path(repo_path):
        if not repo_path:
            return

        path = Path(repo_path).expanduser()

        if not path.exists():
            raise KronosUnavailableError(
                f"Kronos repo path does not exist: {path}"
            )

        path_text = str(path)

        if path_text not in sys.path:
            sys.path.insert(0, path_text)

    @staticmethod
    def _import_kronos_classes():
        try:
            module = importlib.import_module("model")
            return (
                getattr(module, "Kronos"),
                getattr(module, "KronosPredictor"),
                getattr(module, "KronosTokenizer"),
            )
        except Exception as error:
            raise KronosUnavailableError(
                "Kronos dependencies are not importable."
            ) from error

    def _extract_predicted_close(self, prediction):
        if hasattr(prediction, "columns") and "close" in prediction.columns:
            return prediction["close"].tolist()

        if isinstance(prediction, dict):
            close_values = prediction.get("close")

            if close_values is not None:
                return list(close_values)

        if hasattr(prediction, "tolist"):
            values = prediction.tolist()

            if values and isinstance(values[0], list):
                return [row[-1] for row in values]

            return values

        raise ValueError("Kronos prediction does not include close values.")

    def _score_prediction(self, historical_close, predicted_close):
        if not historical_close:
            raise ValueError("Historical close values are required.")

        if not predicted_close:
            raise ValueError("Predicted close values are required.")

        last_close = float(historical_close[-1])
        final_prediction = float(predicted_close[-1])

        if last_close == 0:
            raise ValueError("Last historical close cannot be zero.")

        expected_change = (
            (final_prediction - last_close)
            / last_close
            * 100
        )

        if expected_change > 1:
            direction = "Bullish"
        elif expected_change < -1:
            direction = "Bearish"
        else:
            direction = "Neutral"

        forecast_score = self._forecast_score(expected_change)
        confidence = self._forecast_confidence(expected_change)

        return {
            "direction": direction,
            "confidence": confidence,
            "expected_change": round(expected_change, 2),
            "days": len(predicted_close),
            "forecast_score": forecast_score,
        }

    def _extract_history(self, stock):
        if isinstance(stock, dict):
            return (
                stock.get("ohlcv")
                or stock.get("history")
                or stock.get("prices")
                or []
            )

        return (
            getattr(stock, "ohlcv", None)
            or getattr(stock, "history", None)
            or getattr(stock, "prices", None)
            or []
        )

    def _validate_history(self, history):
        if len(history) < self.minimum_history_rows:
            raise ValueError(
                "Kronos requires at least "
                f"{self.minimum_history_rows} OHLCV rows."
            )

        for row in history:
            missing_fields = [
                field for field in self.required_fields
                if self._get_value(row, field) is None
            ]

            if missing_fields:
                raise ValueError(
                    "Kronos OHLCV row is missing required fields: "
                    + ", ".join(missing_fields)
                )

    def _map_ohlcv_row(self, row):
        close = self._get_value(row, "close")
        volume = self._get_value(row, "volume")
        amount = self._get_value(row, "amount")

        if amount is None:
            amount = close * volume

        return {
            "timestamps": self._get_value(row, "date"),
            "open": self._get_value(row, "open"),
            "high": self._get_value(row, "high"),
            "low": self._get_value(row, "low"),
            "close": close,
            "volume": volume,
            "amount": amount,
        }

    def _get_value(self, row, field):
        if isinstance(row, dict):
            return row.get(field)

        return getattr(row, field, None)

    def _validate_sorted_timestamps(self, rows):
        timestamps = [row["timestamps"] for row in rows]

        if timestamps != sorted(timestamps):
            raise ValueError("Kronos timestamps must be sorted ascending.")

    def _validate_numeric_columns(self, rows):
        for row in rows:
            for field in self.numeric_fields:
                value = row[field]

                if not isinstance(value, (int, float)):
                    raise ValueError(
                        f"Kronos field {field} must be numeric."
                    )

    def _to_dataframe_columns(self, rows):
        columns = [
            "timestamps",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
        ]

        return {
            column: [row[column] for row in rows]
            for column in columns
        }

    def _future_timestamps(self, timestamps, pred_len):
        import pandas as pd

        if len(timestamps) < 2:
            raise ValueError("At least two timestamps are required.")

        step = timestamps.iloc[-1] - timestamps.iloc[-2]
        start = timestamps.iloc[-1] + step

        return pd.Series([
            start + (step * index)
            for index in range(pred_len)
        ])

    def _forecast_score(self, expected_change):
        adjustment = min(30, abs(expected_change) * 3)

        if expected_change > 1:
            score = 50 + adjustment
        elif expected_change < -1:
            score = 50 - adjustment
        else:
            score = 50

        return round(max(0, min(100, score)))

    def _forecast_confidence(self, expected_change):
        confidence = 40 + (abs(expected_change) * 5)

        return round(max(1, min(99, confidence)))
