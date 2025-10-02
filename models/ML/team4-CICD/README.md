# 🚀 CI/CD for ML Project

이 프로젝트는 **GitHub Actions**, **Databricks**, **MLflow**를 이용하여  
머신러닝 모델의 **학습 → 검증 → 배포 → 서빙** 과정을 자동화한 **CI/CD 파이프라인**입니다.  

- 코드 버전 관리 및 자동화 (CI/CD)  
- 모델 학습 및 Staging 전환  
- Realtime Inference 엔드포인트 배포  

---

## 📂 프로젝트 구조
```
team4-CICD
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── cd.yml
├── configs/
│   ├── config_v1
│   └── config_v2
├── src/
│   ├── config_loader.py
│   ├── data_preprocessor.py
│   ├── model_trainer.py
│   ├── mlflow_manager.py
│   ├── model_serving.py
│   ├── realtime_model.py
│   └── main.py
├── notebooks/
│   ├── register_model_notebook.ipynb
│   ├── staging_model_notebook.ipynb
│   └── deploy_model_notebook.ipynb
├── realtime_notebooks/
│   ├── register_realtime_inf_notebook.ipynb
│   ├── staging_realtime_inf_notebook.ipynb
│   └── deploy_realtime_inf_notebook.ipynb
├── deploy_realtime_endpoint.py
├── requirements.txt
└── README.md
```

---

## 📌 주요 기능

### ✅ Continuous Integration (CI)
- GitHub push 시 자동 실행  
- 모델 학습 및 등록, Staging 전환  
- Realtime Inference 등록 및 Staging 전환  
- 단위 테스트 실행 (`pytest`)  

> CI 워크플로우 이미지:  
<img width="940" height="232" alt="image" src="https://github.com/user-attachments/assets/3e6c4c35-b445-41a1-8483-bd0075d6e8d0" />



### 🚀 Continuous Deployment (CD)
- CI 완료 후 수동 또는 자동 실행  
- 모델 Production 전환
- Realtime Inference 엔드포인트 배포/업데이트  

> CD 워크플로우 이미지:  
<img width="940" height="282" alt="image" src="https://github.com/user-attachments/assets/ece75f83-e488-453e-ab3e-91dd5f44bd43" />

---

## 🛠️ 실행 방법

### 1️⃣ 로컬 실행
```bash
# 가상환경 생성 & 라이브러리 설치
pip install -r requirements.txt

# 모델 학습 및 등록
python src/main.py

# 엔드포인트 배포
python deploy_realtime_endpoint.py
```

### 2️⃣ GitHub Actions 실행

- CI: main 브랜치로 push 시 자동 실행

- CD: GitHub Actions → workflow_dispatch로 수동 실행
