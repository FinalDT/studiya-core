# 📡 실시간 데이터 처리 파이프라인

실시간 데이터가 필요했지만 원천이 없어, **수학 학습자 역량 Validation 데이터셋을 배치로 준비한 뒤 트리거로 매시간 유입되도록 시뮬레이션**했습니다. 이를 **실시간 스트림**으로 간주해 아래 실시간 처리 파이프라인을 구성했습니다.

1) **데이터 준비(입력 생성)**  
- 로컬 JSON 데이터를 전처리한 뒤 **Azure Blob Storage에 업로드**

2) **실시간 시뮬레이션(스트리밍 송신)**  
- Azure Functions **Timer Trigger**가 Blob에서 최근 배치 데이터를 주기적으로 조회해  
  **Event Hub로 전송**함으로써 “실시간 이벤트”처럼 제작

3) **Fabric 수집 및 저장(원본 + 실시간 분석 분기)**  
- Fabric **Eventstream**이 Event Hub 이벤트를 수신해  
  Lakehouse(원본 백업)와 Eventhouse(KQL DB, 실시간 분석)로 **동시에 적재**

  **Fabric(정의)**  
- Microsoft Fabric은 데이터 **수집·저장·처리/분석·시각화/서빙**을 한 작업영역에서 통합 운영할 수 있도록 제공하는 **통합 분석 플랫폼(SaaS)**


4) **정제 및 운영 연동(결과 서빙)**  
- Eventhouse에서 **KQL로 정제/집계**한 결과를 만들고, 최종 결과를 **운영 SQL DB에 저장/동기화**하여 서비스/리포트에서 활용

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
├── fabric/
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
<img width="500" height="312" alt="image" src="https://github.com/user-attachments/assets/10759cab-2bdb-48d3-8db1-cc8b1b59c83c" />


---

## ⏱ Timer Trigger + Event Hub

**목적**: Blob Storage에 저장된 배치 데이터를 **실시간 데이터처럼 가정**하고  
Azure Functions의 Timer Trigger를 통해 Event Hub로 전송합니다.

- 매 정시(`0 0 * * * *`)마다 실행
- 이전 1시간 동안의 배치 데이터를 조회
- 중복 응답 제거 후 Event Hub로 전송
- Event Hub를 통해 스트리밍 시스템(예: Databricks, Spark Streaming, Kafka 등)과 연계 가능

### Requirements
`requirements.txt`

```
azure-functions
azure-eventhub
azure-storage-blob
azure-identity
```

---


## Fabric

<img width="1000" height="500" alt="Fabric EventStream" src="fabric/패브릭 작업영역.png" />

**역할**: Event Hub 이후 구간에서 **저장·정제·서빙·운영 연동(알림)**까지를 Fabric에서 엔드투엔드로 처리합니다.

- **흐름**: Event Hub → Eventstream(옵션: Activator 알림) → **Lakehouse(Bronze)** + **Eventhouse(KQL DB)** → **KQL 정제(Silver)** → **Materialized View(Gold)** → **Data Pipeline(운영 SQL DB 동기화 + Teams 알림/검증)**

- **Bronze (Lakehouse)**: 이벤트 **원본 그대로 적재**(백업/재현성, 재처리 가능)
- **Silver (Eventhouse + KQL)**: 컬럼 추출·정합성 정리·세션화 등 **실시간 정제/집계**
- **Gold (Materialized View)**: 자주 조회하는 결과를 **사전계산**해 서빙 지연/비용 감소
- **운영 연동(Data Pipeline)**: Gold 결과를 **운영 SQL DB로 동기화**, 전후 검증 후 Teams Webhook으로 결과 알림
---
## 📝 요약

- 실시간 원천 데이터 부재 상황에서 Validation 배치 데이터 기반 실시간 스트림 시뮬레이션 수행함  
- Local → Blob(`local_to_blob`) → Functions Timer Trigger(`timer_trigger`) → Event Hub 순의 이벤트 생성 및 전송 구성함  
- Fabric(Eventstream → Lakehouse(Bronze) + Eventhouse(KQL DB) → KQL(Silver) → MV(Gold)) 구간에서 원본 보관 및 실시간 정제 수행함  
- Data Pipeline 기반 운영 SQL DB 동기화 및 Teams Webhook 기반 검증·알림 자동화 적용함  

