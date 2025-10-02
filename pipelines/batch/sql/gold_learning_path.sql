;WITH OrderedLearning AS (
    SELECT
        lf.learnerID,
        lf.seq_order AS orig_seq_order,
        ROW_NUMBER() OVER (
            PARTITION BY lf.learnerID
            ORDER BY lf.seq_order
        ) AS new_seq_order,
        lf.knowledge_tag AS concept_id,
        lf.answer
    FROM silver.silver_learning_fact lf
),
LearningWithNext AS (
    SELECT
        ol.learnerID,
        ol.new_seq_order,
        ol.orig_seq_order,
        ol.concept_id,
        LEAD(ol.concept_id) OVER (
            PARTITION BY ol.learnerID
            ORDER BY ol.new_seq_order
        ) AS next_concept,
        ol.answer
    FROM OrderedLearning ol
),
-- concept_id 기준으로 연속 구간 표시
Flagged AS (
    SELECT
        learnerID,
        new_seq_order,
        orig_seq_order,
        concept_id,
        COALESCE(next_concept, 0) AS next_concept,
        answer,
        CASE 
            WHEN LAG(concept_id) OVER (PARTITION BY learnerID ORDER BY new_seq_order) = concept_id
            THEN 0 ELSE 1
        END AS is_new_group
    FROM LearningWithNext
),
Marked AS (
    SELECT
        learnerID,
        new_seq_order,
        orig_seq_order,
        concept_id,
        next_concept,
        answer,
        SUM(is_new_group) OVER (PARTITION BY learnerID ORDER BY new_seq_order) AS grp
    FROM Flagged
)
SELECT
    learnerID,
    MIN(new_seq_order) AS start_seq,
    MAX(new_seq_order) AS end_seq,
    concept_id,
    MAX(next_concept) AS next_concept,  -- 그룹 내 마지막 next_concept
    SUM(1) AS total_attempts,
    SUM(CASE WHEN answer = 1 THEN 1 ELSE 0 END) AS correct_cnt,
    SUM(CASE WHEN answer = 0 THEN 1 ELSE 0 END) AS wrong_cnt,
    ROUND(
        SUM(CASE WHEN answer = 1 THEN 1 ELSE 0 END) * 1.0 / SUM(1),
        2
    ) AS accuracy
INTO gold.gold_learning_path  -- ← 테이블 생성 및 저장
FROM Marked
GROUP BY learnerID, grp, concept_id
ORDER BY learnerID, start_seq;
