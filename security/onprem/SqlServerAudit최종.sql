--- 버전 확인
SELECT @@VERSION AS SQLServerVersion;

--- 데이터베이스 확인
SELECT 
    d.name AS DatabaseName,
    d.state_desc AS Status,
    d.recovery_model_desc AS RecoveryModel,
    d.compatibility_level,
    SUM(f.size) * 8 / 1024 AS SizeMB
FROM sys.databases d
JOIN sys.master_files f ON d.database_id = f.database_id
GROUP BY d.name, d.state_desc, d.recovery_model_desc, d.compatibility_level
ORDER BY d.name;

-- 서버 로그인 목록
SELECT name, type_desc, is_disabled, default_database_name
FROM sys.server_principals
WHERE type IN ('S', 'U', 'G');  -- SQL Login, Windows Login, Group

-- 데이터베이스 사용자 목록 (master DB 기준, 필요시 다른 DB에서도 실행)
SELECT name, type_desc, authentication_type_desc
FROM sys.database_principals
WHERE type IN ('S', 'U', 'G') AND name NOT LIKE '##%';

-- 네트워크 상태 확인
SELECT 
    listener_id,
    ip_address,
    port,
    type,
    state
FROM sys.dm_tcp_listener_states;

---ip_address: 리스닝 중인 IP (예: 0.0.0.0 → 모든 네트워크 인터페이스)

---port: 연결 가능한 TCP 포트 (보통 1433, 또는 사용자 정의 포트)

---type: 프로토콜 (1=TCP)

---state: 리스닝 상태 (1=Started, 0=Stopped)

---=================================================================================
---=======================server audit 시작========================================
---=================================================================================

--- STEP 1. Server Audit 생성 코드 (파일 기반, CONTINUE 버전)

-- 1. Audit 로그 저장 폴더 지정 (C:\AuditLogs)
-- 먼저 OS 경로에 C:\AuditLogs 폴더가 실제로 있어야 합니다.

USE master;
GO

-- 2. Audit 객체 생성
CREATE SERVER AUDIT Audit_To_File
TO FILE (
    FILEPATH = 'C:\AuditLogs\',   -- 로그 저장 경로
    MAXSIZE = 100 MB,             -- 단일 파일 최대 크기 (필요시 조정 가능)
    MAX_ROLLOVER_FILES = 10,      -- 보관 파일 개수 (10개 넘으면 가장 오래된 것부터 삭제)
    RESERVE_DISK_SPACE = OFF      -- 디스크 공간 선할당 여부 (일반적으로 OFF)
)
WITH (
    QUEUE_DELAY = 1000,           -- 밀리초 단위: 로그 쓰기 지연 (1초 단위 배치 기록)
    ON_FAILURE = CONTINUE         -- 실패 시 DB 작업 계속 진행
);
GO

-- 3. Audit 활성화
ALTER SERVER AUDIT Audit_To_File
WITH (STATE = ON);
GO

--- STEP 2. Server Audit Specification (로그인 & 권한 감사)

--- 1.Server Audit Specification: 로그인 및 권한 감사
USE master;
GO

-- =============================================
-- Server Audit Specification: 로그인 및 권한 감사
-- 혼합 전략 적용 (실제 WHERE 절 불가 → 모든 이벤트 기록 후 조회 시 필터링)
--   1) 모든 계정 → 로그인 실패 이벤트 감사
--   2) 모든 계정 → 로그인 성공 이벤트 감사 (나중에 조회 시 sa/admin_user만 필터링)
--   3) 서버 권한 및 역할(Role) 변경 감사
-- =============================================

CREATE SERVER AUDIT SPECIFICATION ServerAudit_Security
FOR SERVER AUDIT Audit_To_File
    ADD (FAILED_LOGIN_GROUP),              -- 모든 계정 실패 로그인
    ADD (SUCCESSFUL_LOGIN_GROUP),          -- 모든 계정 성공 로그인 (조회 시 계정 필터링)
    ADD (SERVER_ROLE_MEMBER_CHANGE_GROUP), -- 서버 역할(Role) 멤버 추가/삭제
    ADD (SERVER_PERMISSION_CHANGE_GROUP),  -- 서버 권한 부여/회수
    ADD (DATABASE_ROLE_MEMBER_CHANGE_GROUP), -- DB 역할(Role) 멤버 변경
    ADD (DATABASE_PERMISSION_CHANGE_GROUP)   -- DB 권한 부여/회수
WITH (STATE = ON);
GO

--- STEP 3. Database Audit Specification: on-premise DB
--- on-premise DB 감사 설정정
USE [on-premise];
GO

-- =============================================
-- Database Audit Specification: on-premise DB
--   1) DML (INSERT, UPDATE, DELETE) 감사
--   2) SELECT 감사
--   3) 스키마 변경 (DDL) 감사
--   4) DB 권한/역할 변경 감사
--   5) 객체 접근 감사 (SCHEMA_OBJECT_ACCESS_GROUP)
--      👉 성공 + 실패 모두 기록됨
--      👉 권한 없는 사용자가 SELECT/UPDATE 시도 시 "Permission denied"도 로그에 남음

-- =============================================

CREATE DATABASE AUDIT SPECIFICATION DBAudit_OnPremise
FOR SERVER AUDIT Audit_To_File
    ADD (INSERT ON DATABASE::[on-premise] BY PUBLIC), ---  BY public 은 모든 사용자를 추적한다는 의미 . on-premise DB 안에서 누가 어떤 테이블에 INSERT/UPDATE/DELETE 했는지 전부 기록
    ADD (UPDATE ON DATABASE::[on-premise] BY PUBLIC), ---  ""
    ADD (DELETE ON DATABASE::[on-premise] BY PUBLIC), ---  ""
    ADD (SELECT ON DATABASE::[on-premise] BY PUBLIC), --- 누가 어떤 데이터를 조회했는지 추적 가능
    ADD (SCHEMA_OBJECT_CHANGE_GROUP), --- 스키마 변경 (DDL) 감사
    ADD (DATABASE_ROLE_MEMBER_CHANGE_GROUP), --- DB 권한/역할 변경 감사
    ADD (DATABASE_PERMISSION_CHANGE_GROUP), --- DB 권한/역할 변경 감사
    ADD (SCHEMA_OBJECT_ACCESS_GROUP)   -- 객체 접근 (성공/실패 모두 기록)
WITH (STATE = ON);
GO


--- **** 만약 만드는데 오류가 났다면 비활성화 후 DROP 후 다시 생성.
-- 1. Audit Specification 비활성화
ALTER DATABASE AUDIT SPECIFICATION DBAudit_OnPremise
WITH (STATE = OFF);
GO

-- 2. 기존 Audit Specification 삭제
IF EXISTS (SELECT * FROM sys.database_audit_specifications 
           WHERE name = 'DBAudit_OnPremise')
BEGIN
    DROP DATABASE AUDIT SPECIFICATION DBAudit_OnPremise;
END
GO

--- ****

--- STEP 4. 감사 로그 검증

--- 전체 로그 확인
SELECT *
FROM sys.fn_get_audit_file('C:\AuditLogs\*.sqlaudit', DEFAULT, DEFAULT); --- C:\AuditLogs\ 는 VM의 파일 경로.

--- 특정 계정 로그인 확인
SELECT event_time, action_id, succeeded, server_principal_name, statement
FROM sys.fn_get_audit_file('C:\AuditLogs\*.sqlaudit', DEFAULT, DEFAULT)
WHERE server_principal_name IN ('sa', 'admin_user')
ORDER BY event_time DESC;

--- 로그인 실패 확인
SELECT event_time, action_id, server_principal_name, statement, session_server_principal_name
FROM sys.fn_get_audit_file('C:\AuditLogs\*.sqlaudit', DEFAULT, DEFAULT)
WHERE action_id = 'LGIF'  -- Login Failed
ORDER BY event_time DESC;

--- DML 확인 (데이터베이스 내 SELECT / UPDATE / DELETE 추적)
SELECT event_time, action_id, server_principal_name, object_name, statement
FROM sys.fn_get_audit_file('C:\AuditLogs\*.sqlaudit', DEFAULT, DEFAULT)
WHERE action_id IN ('SL','IN','UP','DL')  -- SELECT, INSERT, UPDATE, DELETE
ORDER BY event_time DESC;

--- STEP 5.






--- 감사 로그 비활성화

USE master;
GO

ALTER SERVER AUDIT Audit_To_File
WITH (STATE = OFF);
GO

