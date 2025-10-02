# 📘 Team4-databricks

## 📌 프로젝트 개요
- 신규 학습자의 진단 평가 데이터를 기반으로 **이해력 및 진점수(진단 점수) 예측**  
- 모델 개발 → MLOps 환경 구축 → 배포 및 모니터링

### 프로젝트 배경
- 초기 프로토타입은 **Azure ML Designer**에서 수행  
  - 간단한 데이터 연결, 모델 실험, 예측 테스트 수행  
  - 이후 **Databricks 환경으로 이전** → 본격적인 MLOps 파이프라인 구축  
- **ML Designer 이미지 예시**
  <img width="1352" height="1164" alt="image" src="https://github.com/user-attachments/assets/57c5f63d-e9cf-4258-8c04-3f850a175da0" />

---

## 🏗️ 모델 구성
### Version 1 (v1)
- 배치 학습 기반 진점수 예측 모델
- `/v1` 폴더
- 배치 데이터 학습 → 모델 등록 → 실시간 추론 모델 → 테스트  

### Version 2 (v2)
- 신규 유저 데이터 기반 주기적 재학습 모델
- `/v2` 폴더
- 모델 학습 → Staging → Production → Rollback  
- 실시간 추론 모델 등록

---

## ⚙️ MLOps 주요 기능

### 1. MLflow 기반 모델 관리
- **실험 추적**: 파라미터, 메트릭, 아티팩트 자동 로깅  
- **모델 등록**: 버전 관리, 단계별 승격(Staging → Production)  
- 재현성 확보, 버전별 성능 비교  
- 데이터 드리프트 감지 → 필요 시 모델 재학습 지정  

### 2. CI/CD 자동화
- **CI(Continuous Integration)**: Git Push → 코드 통합, 자동 빌드 및 테스트
  <img width="1632" height="379" alt="image" src="https://github.com/user-attachments/assets/4b19070b-5343-43e2-86f6-e99b700a9b88" />

- **CD(Continuous Deployment)**: Staging → Production 전환, 엔드포인트 업데이트
  <img width="940" height="282" alt="image" src="https://github.com/user-attachments/assets/d766c021-843e-43d1-a5e5-92f15c2abfb0" />

### 3. 주기적 재학습(Job)
- 목적: 데이터 드리프트 감지 → 필요 시 모델 재학습 → Staging 배포
- 실행 방법: Databricks Job Scheduler로 Drift Monitoring 노트북 실행
  <img width="940" height="405" alt="image" src="https://github.com/user-attachments/assets/defbf942-6585-4da7-b701-3834659fcf21" />

### 4. 실시간 모니터링 대시보드
- 엔드포인트의 실시간 성능과 운영 상태
- 모니터링 항목:
  - 시도 횟수 및 성공 횟수, 오류율
  - 엔드포인트 작동 상태 및 요청 처리 속도
  - 버전별 성공횟수 및 오류율
<img width="1603" height="1210" alt="image" src="https://github.com/user-attachments/assets/adb7cd20-6a0d-40f3-8527-9198444ab711" />

## 📡 배포 및 운영
 - CI 실행: Git Push → 테스트/빌드 자동 수행
 - CD 실행: Staging → Production 배포
 - 재학습 Job: Drift 감지 → 모델 재학습 → Staging
 - 모니터링: 엔드포인트 상태
