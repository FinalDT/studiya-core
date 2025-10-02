# src/data_preprocessor.py
import pandas as pd
import numpy as np
from pyspark.sql import DataFrame as SparkDataFrame
from typing import List, Tuple, Union

def _fix_mean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    '_mean' 컬럼을 단순 제거가 아닌, guess_mean → guess 등으로 컬럼명 변경.
    """
    rename_map = {c: c.replace('_mean', '') for c in df.columns if c.endswith('_mean')}
    df = df.rename(columns=rename_map)
    return df

def _calculate_accuracy(df: pd.DataFrame) -> pd.DataFrame:
    """
    correct_cnt / items_attempted로 정확도 컬럼 생성
    """
    if 'correct_cnt' in df.columns and 'items_attempted' in df.columns:
        df['accuracy'] = df['correct_cnt'] / df['items_attempted'].replace(0, np.nan)
        df['accuracy'] = df['accuracy'].fillna(0)
    else:
        df['accuracy'] = 0
    return df

def preprocess_dataframe(
    df_in: Union[pd.DataFrame, SparkDataFrame],
    categorical_candidates: List[str] = ['gender', 'grade']
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Spark 또는 Pandas DataFrame을 받아 전처리 후 Pandas DataFrame과 범주형 컬럼 리스트 반환

    Steps:
        1. Spark → Pandas 변환 (필요시)
        2. 정확도 컬럼 생성
        3. 결측치 0 또는 'missing' 처리
        4. '_mean' 컬럼 rename
        5. 범주형 컬럼 자동 감지

    Args:
        df_in (pd.DataFrame or SparkDataFrame): 입력 데이터
        categorical_candidates (list): 범주형 후보 컬럼

    Returns:
        df (pd.DataFrame): 전처리 완료 데이터
        categorical_cols (list): 범주형 컬럼 리스트
    """
    # 1. Spark → Pandas
    if isinstance(df_in, SparkDataFrame):
        df = df_in.toPandas()
    else:
        df = df_in.copy()

    # 2. 정확도 컬럼 생성
    df = _calculate_accuracy(df)

    # 3. 결측치 0 처리
    df = df.fillna(0)

    # 4. '_mean' 컬럼 rename
    df = _fix_mean_columns(df)

    # 5. 범주형 컬럼 자동 감지
    categorical_cols = [c for c in categorical_candidates if c in df.columns]

    return df, categorical_cols

def merge_batch_recent(
    df_batch: SparkDataFrame,
    df_recent: SparkDataFrame,
    rename_map: dict = None,
    drop_cols: List[str] = None
) -> SparkDataFrame:
    """
    v2 이상: 배치 + 최근 데이터 병합 (Spark DataFrame)
    
    Args:
        df_batch: 배치 데이터
        df_recent: 최근 데이터
        rename_map: 컬럼명 변경 dict
        drop_cols: 제거할 컬럼 리스트

    Returns:
        SparkDataFrame: 병합된 데이터
    """
    df_recent_copy = df_recent
    if rename_map:
        for old, new in rename_map.items():
            if old in df_recent_copy.columns:
                df_recent_copy = df_recent_copy.withColumnRenamed(old, new)
    
    if drop_cols:
        for c in drop_cols:
            if c in df_recent_copy.columns:
                df_recent_copy = df_recent_copy.drop(c)

    df_merge = df_batch.unionByName(df_recent_copy, allowMissingColumns=True)
    return df_merge
