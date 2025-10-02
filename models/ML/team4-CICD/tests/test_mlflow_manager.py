import argparse
import os
import mlflow
from azureml.core import Workspace, Model

def register_model_aml(mlflow_model_uri, model_name, version, description=""):
    # 1. AzureML Workspace 연결
    ws = Workspace(
        subscription_id=os.environ["AML_SUBSCRIPTION_ID"],
        resource_group=os.environ["AML_RESOURCE_GROUP"],
        workspace_name=os.environ["AML_WORKSPACE_NAME"]
    )

    # 2. MLflow 모델 다운로드
    print(f"📥 MLflow 모델 다운로드: {mlflow_model_uri}")
    local_path = mlflow.artifacts.download_artifacts(artifact_uri=mlflow_model_uri)
    print(f"✅ 다운로드 완료: {local_path}")

    # 3. AzureML 모델 등록
    print(f"📤 AzureML 모델 등록: {model_name}")
    model_aml = Model.register(
        workspace=ws,
        model_path=local_path,
        model_name=model_name,
        description=description,
        tags={"version": version}
    )
    print(f"✅ AzureML 모델 등록 완료: {model_aml.name} v{model_aml.version}")
    return model_aml

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mlflow_uri", required=True)
    parser.add_argument("--model_name", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()

    register_model_aml(
        mlflow_model_uri=args.mlflow_uri,
        model_name=args.model_name,
        version=args.version,
        description=f"Deploy {args.model_name} version {args.version} from MLflow"
    )
