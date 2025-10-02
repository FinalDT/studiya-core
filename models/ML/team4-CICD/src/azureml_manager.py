import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
import mlflow
from azureml.core import Workspace, Model

# Databricks MLflow URI 설정
mlflow.set_tracking_uri("databricks")  # Databricks MLflow Tracking URI
mlflow.set_registry_uri("databricks")  # 모델 레지스트리도 Databricks

def register_model_aml(
    mlflow_model_name: str, 
    model_name: str,
    stage: str = "Production",
    description: str = ""
):
    """
    Databricks MLflow 모델을 Azure ML에 등록 (최신 Production 모델 기준)
    """
    ws = Workspace.get(
        name=os.environ["AML_WORKSPACE_NAME"],
        subscription_id=os.environ["AML_SUBSCRIPTION_ID"],
        resource_group=os.environ["AML_RESOURCE_GROUP"]
    )

    mlflow_uri = f"models:/{mlflow_model_name}/{stage}"
    print(f"Registering model '{model_name}' from MLflow URI '{mlflow_uri}'...")

    # 최신 모델 다운로드
    local_model_path = mlflow.pyfunc.load_model(mlflow_uri)._model_impl.pyfunc_loader.model_path
    print(f"Model downloaded to: {local_model_path}")

    # AML에 등록
    registered_model = Model.register(
        workspace=ws,
        model_path=local_model_path,
        model_name=model_name,
        description=description,
        tags={"mlflow_uri": mlflow_uri, "stage": stage}
    )

    print(f"Model '{model_name}' registered in AML with version {registered_model.version}")
    return registered_model
