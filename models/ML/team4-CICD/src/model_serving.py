# src/model_serving.py
import pandas as pd
from typing import Any, Dict
import joblib
from sklearn.base import RegressorMixin

def predict_with_model(model: RegressorMixin, df: pd.DataFrame, feature_cols: list) -> pd.Series:
    """
    학습된 모델을 이용해 예측값 생성
    Args:
        model: 학습된 sklearn Regressor
        df: 예측할 데이터
        feature_cols: 모델 입력 feature 컬럼 리스트
    Returns:
        pd.Series: 예측값
    """
    X_input = df[feature_cols]
    preds = model.predict(X_input)
    return pd.Series(preds, index=df.index)

def predict_with_fallback(
    primary_model: RegressorMixin,
    fallback_model: RegressorMixin,
    df: pd.DataFrame,
    feature_cols: list,
    threshold: float = 0.1
) -> pd.Series:
    """
    primary_model로 예측 후 threshold 이상 오차 발생 시 fallback_model 사용
    (예: missing 컬럼, 이상치 처리 등)
    """
    preds = primary_model.predict(df[feature_cols])
    # 간단한 예시: 음수나 NaN일 경우 fallback
    fallback_mask = (preds < 0) | pd.isna(preds)
    if fallback_mask.any():
        fallback_preds = fallback_model.predict(df.loc[fallback_mask, feature_cols])
        preds[fallback_mask] = fallback_preds
    return pd.Series(preds, index=df.index)

def save_model(model: RegressorMixin, path: str):
    """
    sklearn 모델 저장
    """
    joblib.dump(model, path)

def load_model(path: str) -> RegressorMixin:
    """
    저장된 sklearn 모델 로드
    """
    return joblib.load(path)
