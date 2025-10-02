# src/mlflow_manager.py
import mlflow
import mlflow.sklearn
from typing import Dict

def init_experiment(experiment_name: str):
    """
    MLflow experiment 설정
    """
    mlflow.set_experiment(experiment_name)

def log_model_mlflow(
    best_name: str,
    best_model,
    results: Dict,
    model_name: str,
    run_name: str = None
):
    """
    선택된 모델 MLflow 기록 및 자동 등록
    """
    if run_name is None:
        run_name = f"{model_name}-{best_name}"

    with mlflow.start_run(run_name=run_name) as run:
        run_id = run.info.run_id

        # 어떤 모델 선택되었는지 기록
        mlflow.log_param("selected_model", best_name)

        # 선택된 모델 하이퍼파라미터 기록
        for p, v in results[best_name]['best_params'].items():
            mlflow.log_param(p, v)

        # 모든 모델 평가 지표 기록
        for name, res in results.items():
            mlflow.log_metric(f"{name}_rmse", res['rmse'])
            mlflow.log_metric(f"{name}_mae", res['mae'])
            mlflow.log_metric(f"{name}_r2", res['r2'])

        # 선택된 모델 최종 지표 기록
        mlflow.log_metric("rmse", results[best_name]['rmse'])
        mlflow.log_metric("mae", results[best_name]['mae'])
        mlflow.log_metric("r2", results[best_name]['r2'])

        # 모델 MLflow에 자동 등록
        mlflow.sklearn.log_model(
            sk_model=best_model,
            artifact_path="model",
            registered_model_name=model_name
        )
        print(f"✅ 모델 '{model_name}' MLflow에 등록 완료 (버전 관리)")
