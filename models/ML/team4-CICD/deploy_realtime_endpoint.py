#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import time
import requests

# -------------------------------
# 환경변수 로드
# -------------------------------
AZURE_BLOB_CONN_STR = os.getenv("AZURE_BLOB_CONN_STR")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
REALTIME_MODEL_NAME = os.getenv("REALTIME_MODEL_NAME", "realtime-realScore-model")
ENDPOINT_NAME = os.getenv("ENDPOINT_NAME", "realtime-realscore-endpoint")
ENVIRONMENT = os.getenv("ENVIRONMENT", "Staging")  # 기본 Stage

HEADERS = {
    'Authorization': f'Bearer {DATABRICKS_TOKEN}',
    'Content-Type': 'application/json'
}

# -------------------------------
# REST API로 최신 모델 버전 조회
# -------------------------------
def get_latest_model_version(model_name, stage):
    try:
        url = f"{DATABRICKS_HOST}/api/2.0/mlflow/model-versions/search"
        resp = requests.get(url, headers=HEADERS, params={"filter": f"name='{model_name}'"})
        if resp.status_code != 200:
            raise Exception(f"Failed to fetch model versions: {resp.status_code} {resp.text}")

        versions = resp.json().get("model_versions", [])
        if stage:
            versions = [v for v in versions if v.get("current_stage","").lower() == stage.lower()]

        if not versions:
            raise Exception(f"No model versions found for {model_name} in stage {stage}")

        latest_version = max(int(v["version"]) for v in versions)
        print(f"✅ Latest version for '{model_name}' in stage '{stage}': {latest_version}")
        return latest_version
    except Exception as e:
        print(f"❌ Error getting latest model version: {e}")
        raise

# -------------------------------
# 엔드포인트 확인/생성/업데이트
# -------------------------------
def check_endpoint(endpoint_name):
    resp = requests.get(f"{DATABRICKS_HOST}/api/2.0/serving-endpoints/{endpoint_name}", headers=HEADERS)
    return resp.status_code == 200, resp

def create_endpoint(endpoint_name, model_name, model_version):
    payload = {
        "name": endpoint_name,
        "config": {
            "served_models": [
                {"model_name": model_name, "model_version": str(model_version), "workload_size": "Small", "scale_to_zero_enabled": True}
            ],
            "traffic_config": {"routes": [{"served_model_name": f"{model_name}-{model_version}", "traffic_percentage": 100}]}
        }
    }
    return requests.post(f"{DATABRICKS_HOST}/api/2.0/serving-endpoints", headers=HEADERS, data=json.dumps(payload))

def update_endpoint(endpoint_name, model_name, model_version):
    payload = {
        "served_models": [
            {"model_name": model_name, "model_version": str(model_version), "workload_size": "Small", "scale_to_zero_enabled": True}
        ],
        "traffic_config": {"routes": [{"served_model_name": f"{model_name}-{model_version}", "traffic_percentage": 100}]}
    }
    return requests.put(f"{DATABRICKS_HOST}/api/2.0/serving-endpoints/{endpoint_name}/config", headers=HEADERS, data=json.dumps(payload))

def wait_for_endpoint(endpoint_name, max_minutes=15):
    print(f"⏳ Waiting for endpoint '{endpoint_name}' to be ready...")
    for _ in range(max_minutes * 2):
        resp = requests.get(f"{DATABRICKS_HOST}/api/2.0/serving-endpoints/{endpoint_name}", headers=HEADERS)
        if resp.status_code == 200:
            state = resp.json().get("state", {})
            if state.get("ready") == "READY" and state.get("config_update") != "IN_PROGRESS":
                print(f"✅ Endpoint '{endpoint_name}' is ready!")
                return True
        time.sleep(30)
    print(f"⚠️ Endpoint '{endpoint_name}' not ready after {max_minutes} minutes")
    return False

# -------------------------------
# 배포 실행
# -------------------------------
# -------------------------------
# 배포 실행
# -------------------------------
if __name__ == "__main__":
    try:
        # 1️⃣ 기존: ENVIRONMENT stage에서 모델 가져오기
        try:
            latest_version = get_latest_model_version(REALTIME_MODEL_NAME, ENVIRONMENT)
        except Exception as e:
            # 2️⃣ 추가: stage에 모델이 없으면 stage 무관 최신 모델 사용
            print(f"⚠️ {ENVIRONMENT} stage 모델이 없어서 stage 무관 최신 버전 사용: {e}")
            latest_version = get_latest_model_version(REALTIME_MODEL_NAME, stage=None)

        exists, resp = check_endpoint(ENDPOINT_NAME)
        if exists:
            print(f"⚠️ Endpoint exists. Updating '{ENDPOINT_NAME}'...")
            resp = update_endpoint(ENDPOINT_NAME, REALTIME_MODEL_NAME, latest_version)
        else:
            print(f"🚀 Creating new endpoint '{ENDPOINT_NAME}'...")
            resp = create_endpoint(ENDPOINT_NAME, REALTIME_MODEL_NAME, latest_version)

        print(f"Response: {resp.status_code} {resp.text}")

        if resp.status_code in [200, 201]:
            wait_for_endpoint(ENDPOINT_NAME)
            print("🎉 Deployment completed successfully!")
        else:
            raise Exception(f"Deployment failed: {resp.status_code} {resp.text}")

    except Exception as e:
        print(f"❌ Deployment error: {e}")
        exit(1)

