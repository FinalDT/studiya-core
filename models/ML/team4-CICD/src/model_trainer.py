# src/model_trainer.py
from typing import List, Dict
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from math import sqrt

def build_preprocessor(X_train, categorical_cols: List[str]) -> ColumnTransformer:
    """
    숫자/범주형 컬럼 전처리 파이프라인 생성
    """
    numeric_cols = [c for c in X_train.columns if c not in categorical_cols]

    num_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value=0))
    ])

    cat_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
        ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])

    preprocessor = ColumnTransformer([
        ('num', num_pipeline, numeric_cols),
        ('cat', cat_pipeline, categorical_cols)
    ])
    return preprocessor

def train_models(X_train, y_train, X_test, y_test, preprocessor, random_state=42) -> Dict:
    """
    여러 모델 후보 학습, GridSearchCV 수행 후 평가 지표 반환
    """
    pipelines = {
        'dt': Pipeline([('preproc', preprocessor),
                        ('model', DecisionTreeRegressor(random_state=random_state))]),
        'rf': Pipeline([('preproc', preprocessor),
                        ('model', RandomForestRegressor(random_state=random_state, n_jobs=-1))])
    }

    param_grids = {
        'dt': {'model__max_depth': [3, 5, 7]},
        'rf': {'model__n_estimators': [50, 100], 'model__max_depth': [5, 10, None]}
    }

    results = {}
    for name, pipe in pipelines.items():
        gs = GridSearchCV(pipe, param_grids[name], cv=3,
                          scoring='neg_mean_squared_error', n_jobs=-1)
        gs.fit(X_train, y_train)

        best = gs.best_estimator_
        preds = best.predict(X_test)

        rmse = sqrt(mean_squared_error(y_test, preds))
        mae = mean_absolute_error(y_test, preds)
        r2 = r2_score(y_test, preds)

        results[name] = {
            'best_model': best,
            'best_params': gs.best_params_,
            'rmse': rmse,
            'mae': mae,
            'r2': r2
        }

    # RMSE 기준 베스트 모델 선택
    best_name = min(results.keys(), key=lambda k: results[k]['rmse'])
    best_model = results[best_name]['best_model']
    return {
        'results': results,
        'best_name': best_name,
        'best_model': best_model
    }
