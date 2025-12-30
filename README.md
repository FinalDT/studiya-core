# Studiya-core (Final Team Project)
## 🌊 프로젝트 소개

**Studiya**는 진단 기반 맞춤형 학습 관리 플랫폼을 목표로 구현한 서비스로, 온프레미스와 클라우드를 사용하는 하이브리드 환경에서 Azure 서비스들을 이용하여 **정적/실시간 데이터**를 엔지니어링 하는 **엔드-투-엔드 데이터 응용 프로그램**을 구현하는 프로젝트입니다.

이 프로젝트의 목표는, 팀원이 직접 온프레미스 환경부터 마이그레이션을 통한 클라우드 운영과 동시에 **Python, SQL, Power BI, Databricks, Azure Data Factory, Azure Functions, Fabric, Azure ML, Open AI, Power BI**에 대한 실전 경험을 쌓는 것입니다.

> **"학원에, 문제집에, 인강까지 너무 많다고? 한번에 모아줄게!" – Studiya**

<img width="9778" height="5024" alt="최종 프로젝트 구조도_figzam_2" src="web/web_png/웹 홈화면.png" />


## 🏗️ 아키텍처 개요

```plaintext
📦 외부 데이터 소스 (AI Hub,JSON)
    ↓
🐍 데이터 수집 및 정제 (Python, Azure Functions, Event Hubs, Fabric, Azure Data Factory, Databricks)
    ↓
💾 데이터 저장소 (Azure SQL Database, Lakehouse)
    ↓
🧠 데이터 분석 (Azure ML, Databricks, Open AI) 
    ↓
📊 Power BI 대시보드 연결 및 시각화 (PowerBI)
    ↓
🌐 웹 제작(Next.js)
```

## 🛠️ 기술 스택

| 구분           | 사용 기술                                       |
|---------------|--------------------------------------------------|
| 데이터 수집     | Python, Azure Functions, Event Hub, Fabric  |
| 데이터 처리     | Python, Databricks, Azure Data Factory, Fabric(KQL Query), SSMS, SQL Query             |
| 저장 및 분산처리 | Databricks, Azure Data Factory, Fabric, SQL Database               |
| 시각화         | Power BI                                       |
| 웹 제작        | Next.js                                         |
| AI 연동        | Azure AI Foundary, Open AI                               |
| 모델 개발      | Azure ML                               |
| 버전관리 | Git + GitHub |

## 📁 디렉토리 구조
``` bash
studiya/
├─ README.md                 # 전체 개요/설치/데모 링크
├─ LICENSE
├─ docs/                     # 아키텍처, 발표자료, 다이어그램
├─ data/                     # 샘플 데이터(비식별, 소량)
│  └─ README.md
├─ pipelines/                # 배치/스트리밍(쿼리·함수·파이프라인)
│  ├─ batch/
│  │  ├─ Data Factory/       # Azure DataFactory 작업 이미지
│  │  └─ sql/                # Silver/Gold DDL/DML, 검증쿼리
│  └─ streaming/
│     ├─ local_to_blob/      # Blob Storage에 저장
│     ├─ timmer_trigger/     # Azure Function (트리거)
│     ├─ fabric/             # Event Stream 설정 내보낸 파일/문서
│     └─ README.md           
├─ models/                   # ML/RAG, 노트북/파이프라인
│  ├─ ML/
│  └─ rag/
├─ dashboards/               # Power BI, 리포트
│  ├─ pbix/                  # LFS 권장
│  └─ datasets/
├─ web/                      # Next.js 프론트엔드
│  ├─ app/ or src/
│  ├─ public/
│  ├─ .env.example           # 예: API_URL, TENANT_ID
│  └─ README.md
└─ security/                 # RLS/마스킹/TDE/감사 스크립트
   ├─ onprem_sql/
   └─ azure_sql/

```

## 👥 팀원 및 역할 분담

| 이름 | 역할            | 담당 업무                                  |
|------|-----------------|--------------------------------------------|
| 김동현   | Data Engineer  |  데이터 프로세스 개발, ML 개발  |
| 김진우   | PM, Data Analyst   |  데이터 프로세스 개발, 프로젝트 관리, 시각화 구현           |
| 서창범    | Data Engineer         |  데이터 프로세스 개발, AI 연동             |
| 이재훈    | Data Engineer    |   데이터 프로세스 개발, AI 연동, 프론트 개발                 |
| 정민철    | Data Engineer, Data Analyst    |  데이터 프로세스 개발, ML 개발, 시각화 구현 보조          |


## 📈 결과 요약
- 진단 기반 개인화
    - 초기 진단 결과로 학습자 프로필 생성(학년/난이도/취약개념), 맞춤 피드백 제공
- 배치+실시간 파이프라인
    - 배치: 온프레→Azure SQL 마이그레이션, 메달리온(브론즈·실버·골드) 정제
    - 실시간(데모): Event Hub→Event Stream→Lakehouse/KQL→Gold→SQL 동기화
- 대시보드 & 리포트
    - Power BI 대시보드(학생용), Report Builder 요약 리포트(교사/학부모용)
    - URL/RLS(전환 예정) 기반 개인화 화면
- AI 튜터 & 문제 생성
    - RAG로 학년·난이도 기반 문제/유사문항 추천, GPT-4o mini로 튜터링·요약
- 웹 서비스
    - Next.js 프런트엔드, Azure App Service 배포(HTTPS/TLS 기본)
- 보안·거버넌스
    - 카탈로그·민감도 레벨링, 온프레(RLS/마스킹/TDE/감사)와 클라우드(TDE/감사/TLS)
- 모니터링·운영
    - Log Analytics/Insights/Metrics 통합, 파이프라인 성공/실패 Teams 웹훅 알림
- 확장성
    - 현재 PoC는 고정 스케일, 운영 전환 시 App Service 자동확장·Event Hubs auto-inflate·SQL Serverless 적용 가능
- 하이브리드 이점
    -   온프레 PII는 보관/검증용, 클라우드엔 비식별·분석 데이터만 이관해 안전한 분석 환경 구축

