# 📡 실시간 데이터 처리 파이프라인

이 레포지토리는 **AI Hub - 수학분야 학습자 역량 측정 Validation 데이터셋**을 활용하여  
**배치 데이터(Batch Data)를 실시간 데이터로 가정**하고, 다음과 같은 **실시간 데이터 처리 파이프라인**을 구성합니다.

- **로컬 데이터 → Azure Blob Storage 업로드 (local_to_blob)**
- **Azure Function Timer Trigger 기반 데이터 조회 및 Event Hub 전송 (timer_trigger)**

---

## 📂 프로젝트 구조

```
realtime-data-preprocess
├── local_to_blob/         # 로컬 데이터를 Azure Blob Storage로 업로드
│   └── to_blob.ipynb
├── timer_trigger/         # Timer Trigger 기반 Event Hub 전송
│   ├── batch_data_processor.py
│   ├── function_app.py
│   ├── requirements.txt       # 필요한 Python 라이브러리
│   └── local.settings.json
└── README.md
```

---

## ⚙️ 환경 변수 설정 (.env or local.settings.json)

### Local to Blob 업로드용
```
AZURE_BLOB_CONN_STR="your_blob_connection_string"
```

### Timer Trigger (Azure Functions) 실행용
`local.settings.json`
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "your_blob_connection_string",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "EVENT_HUB_CONN_STR": "your_eventhub_connection_string",
    "EVENT_HUB_NAME": "your_eventhub_name",
    "BLOB_CONTAINER": "processed-data",
    "AzureWebJobsFeatureFlags": "EnableWorkerIndexing"
  }
}
```

---

## 📌 Local to Blob

**목적**: 로컬 JSON 데이터를 불러와 전처리 후 Azure Blob Storage에 업로드합니다.  
데이터셋은 `학년/문항정오답표/` 구조로 저장되어 있으며, 파일명에서 `learner_id, test_id, item_id`를 추출합니다.

- 응답 데이터를 **테스트 단위** / **시간 단위(1시간)** 로 묶어 **배치 데이터(batch)** 생성
- 최소 6개 응답 이상인 경우만 업로드
- 업로드 경로 예시:
<img width="750" height="449" alt="image" src="https://github.com/user-attachments/assets/10759cab-2bdb-48d3-8db1-cc8b1b59c83c" />


---

## ⏱ Timer Trigger + Event Hub

**목적**: Blob Storage에 저장된 배치 데이터를 **실시간 데이터처럼 가정**하고  
Azure Functions의 Timer Trigger를 통해 Event Hub로 전송합니다.

- 매 정시(`0 0 * * * *`)마다 실행
- 이전 1시간 동안의 배치 데이터를 조회
- 중복 응답 제거 후 Event Hub로 전송
- Event Hub를 통해 스트리밍 시스템(예: Databricks, Spark Streaming, Kafka 등)과 연계 가능

---

## 📦 Requirements

`requirements.txt`

```
azure-functions
azure-eventhub
azure-storage-blob
azure-identity
```

---

## 📝 요약

- **배치 데이터를 실시간 데이터로 가정**하여 **실시간 데이터 처리 파이프라인**을 구성
- `local_to_blob`: 로컬 데이터 → Blob Storage 업로드
- `timer_trigger`: Timer Trigger로 이전 시간대 데이터 조회 → Event Hub 전송
- 이를 통해 **실시간 학습 데이터 파이프라인**을 시뮬레이션할 수 있음
