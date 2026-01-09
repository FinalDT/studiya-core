## 🧩 Fabric 파이프라인 (Eventstream → Lakehouse/Eventhouse(KQL DB) → MV → 운영 DB)


<img width="1442" height="756" alt="image" src="https://github.com/user-attachments/assets/ac075dd4-9877-4ad7-a1ea-a6ea2a618a88" />


### 0) Fabric 파트는 어디에 붙어있나?
이 레포에서 **Event Hub까지**는 “실시간처럼 보이게 만드는 입력(시뮬레이션)” 구간이고,  
**Fabric 파트부터**는 “들어온 이벤트를 저장·정제·서빙·운영 연동까지 끝내는 처리 구간”입니다.

- 입력(시뮬레이션): Local → Blob → Azure Functions(Timer) → **Event Hub**
- 처리/서빙(실제 파이프라인): **Event Hub → Fabric(Eventstream/Eventhouse/Lakehouse) → 운영 SQL DB + Teams 알림**

---

### 1) 용어 정리
- **Eventstream**: Event Hub에서 들어오는 이벤트를 받아서 **저장소로 보내는 분배기**
- **Lakehouse**: 들어온 데이터를 **원본 그대로 저장**하는 곳(백업/재처리용)
- **Eventhouse(KQL DB)**: 실시간 이벤트를 **빠르게 조회/집계**하기 위한 저장소
- **KQL**: Eventhouse 데이터를 정제/집계하는 **쿼리 언어**
- **Materialized View(MV)**: 자주 쓰는 결과를 **미리 계산해 둔 최종 뷰**(빠르게 서빙)
- **Data Pipeline**: MV 결과를 **운영 SQL DB로 동기화**하고, **검증/알림**까지 수행

---

### 2) Fabric 전체 흐름
**Event Hub** → **Eventstream** → **Lakehouse(Bronze, 원본 백업)** + **Eventhouse(KQL DB, 실시간 분석)** 
→ **KQL 정제/집계(Silver)** → **Materialized View(Gold, 서빙 최적화)** → **Data Pipeline(운영 SQL DB 동기화 + Teams 알림 + 일관성 체크)**

---

### 3) 왜 Lakehouse와 Eventhouse를 둘 다 쓰나?
같은 이벤트를 두 곳에 저장하는 이유는 역할이 다르기 때문입니다.

- **Lakehouse = 원본 보관(안전장치)**  
  - 들어온 이벤트를 “그대로” 남겨 **백업/재현성/재처리**가 가능
- **Eventhouse = 실시간 분석(속도)**  
  - 운영 지표/이상징후를 빠르게 보기 위해 **조회/집계**에 최적화

즉, 원본 보관(안정성)과 실시간 분석(속도)를 동시에 확보하는 설계입니다.

---

### 4) Bronze / Silver / Gold는 무엇이 다른가?
이 프로젝트에서는 다음처럼 단계가 구분됩니다.

#### ✅ Bronze (Lakehouse)
- **무엇을 저장?** Eventstream에서 들어온 **원본 이벤트**
- **왜 필요?** 문제 발생 시 원본으로 다시 계산 가능(재현성)

#### ✅ Silver (Eventhouse + KQL)
- **무엇을 저장/만들어?** KQL로 **정제된 결과**
- **무엇을 하냐?**  
  - 필요한 컬럼만 추출  
  - 정합성/형식 정리  
  - 세션화(이벤트를 세션 단위로 묶기) 등

#### ✅ Gold (Materialized View)
- **무엇을 제공?** 운영/리포트에서 자주 쓰는 최종 결과를 **미리 계산해 둔 뷰**
- **왜 필요?** 반복 조회 시 **지연(latency)과 비용을 줄이고**, 빠르게 서빙하기 위함

---

### 5) 운영 연동(Data Pipeline)은 무엇을 보장하나?
Fabric 내부의 Gold(MV) 결과를 **운영 SQL Database로 동기화**하고, 운영자가 신뢰할 수 있도록 다음을 포함합니다.

- **동기화 전후 검증(예: 행 수 조회)**  
  - 적재 전 기준값 조회 → 적재 후 결과 조회로 이상 여부 확인
- **Teams Webhook 알림**  
  - 성공/실패 또는 증분 결과를 운영 채널로 전송
- **목표**: “복사만 하는 파이프라인”이 아니라 **검증 + 알림을 포함한 운영 자동화**

---

### ✅ 요약
1) Event Hub로 들어온 이벤트를 Eventstream이 받아 Lakehouse(원본)와 Eventhouse(실시간 분석)로 보냅니다.  
2) Eventhouse에서는 KQL로 정제(Silver)하고 자주 쓰는 결과는 MV(Gold)로 빠르게 제공합니다.  
3) 최종 결과는 Data Pipeline으로 운영 SQL DB에 동기화하고 검증 후 Teams로 알립니다.
