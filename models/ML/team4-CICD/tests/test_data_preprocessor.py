# tests/test_preprocess_mock.py
import pandas as pd
import numpy as np
import pytest
from src.data_preprocessor import preprocess_common  # 공통 전처리 함수

# -----------------------
# V1 테스트
# -----------------------
def test_v1_drop_mean_columns():
    df = pd.DataFrame({
        "score_mean": [1, 2],
        "score": [3, 4],
        "correct_cnt": [2, 3],
        "items_attempted": [5, 6]
    })
    config = {"drop_columns": []}
    df_processed, _ = preprocess_common(df, version="v1", config=config)
    assert "score_mean" not in df_processed.columns
    assert "score" in df_processed.columns
    assert "accuracy" in df_processed.columns
    assert np.allclose(df_processed["accuracy"].values, [0.4, 0.5])

# -----------------------
# V2 테스트 (추가 데이터 병합 포함)
# -----------------------
def test_v2_merge_extra_data():
    df_main = pd.DataFrame({
        "learnerID": [1, 2],
        "testID": ["t1", "t2"],
        "correct_cnt": [2, 3],
        "items_attempted": [5, 6]
    })
    df_extra = pd.DataFrame({
        "learnerID": [1, 2],
        "testID": ["t1", "t2"],
        "extra_feature": [10, 20]
    })
    config = {"drop_columns": [], "merge_extra_data": True}
    df_processed, _ = preprocess_common(df_main, version="v2", config=config, extra_df=df_extra)
    assert "extra_feature" in df_processed.columns
    assert "accuracy" in df_processed.columns
    assert np.allclose(df_processed["accuracy"].values, [0.4, 0.5])