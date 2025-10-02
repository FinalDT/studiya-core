import azure.functions as func
import logging
import os
import json
import datetime
import hashlib
from azure.eventhub import EventHubProducerClient, EventData
from batch_data_processor import TimerTriggerDataRetriever

# Function App 생성
app = func.FunctionApp()

def get_korea_now():
    """한국 시간 기준 현재 시각 반환 (분, 초, 마이크로초는 0으로 설정)"""
    utc_now = datetime.datetime.utcnow()
    korea_now = utc_now + datetime.timedelta(hours=9)
    return korea_now.replace(minute=0, second=0, microsecond=0)

def get_target_hour_range():
    """처리할 시간 범위 계산 (이전 1시간)"""
    korea_now = get_korea_now()
    end_time = korea_now
    start_time = korea_now - datetime.timedelta(hours=1)
    return start_time, end_time

def generate_response_hash(response):
    """응답 데이터의 해시 생성 (중복 체크용)"""
    response_str = json.dumps(response, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(response_str.encode('utf-8')).hexdigest()

@app.timer_trigger(
    schedule="0 0 * * * *",  # 매 정시 실행
    arg_name="mytimer",
    run_on_startup=False,
    use_monitor=True
)
def process_hourly_data(mytimer: func.TimerRequest) -> None:
    korea_now = get_korea_now()
    start_time, end_time = get_target_hour_range()

    logging.info(f"Timer trigger ran at {korea_now.isoformat()} (KST)")
    logging.info(f"Processing time range: start={start_time.isoformat()}, end={end_time.isoformat()}")

    if mytimer.past_due:
        logging.warning('The timer is past due!')

    connection_string = os.environ.get("AzureWebJobsStorage")
    eventhub_conn_str = os.environ.get("EVENT_HUB_CONN_STR")
    eventhub_name = os.environ.get("EVENT_HUB_NAME")
    
    if not connection_string or not eventhub_conn_str or not eventhub_name:
        logging.error("Storage or Event Hub connection info missing!")
        return

    retriever = TimerTriggerDataRetriever(connection_string)
    all_batches = []

    grades = ["7학년", "8학년", "9학년"]
    for grade in grades:
        try:
            logging.info(f"Retrieving {grade} data...")
            batches = retriever.get_previous_hour_data(grade)
            if batches:
                for batch in batches:
                    batch['grade'] = grade
                all_batches.extend(batches)
                logging.info(f"Found {len(batches)} batches for {grade}")
            else:
                logging.info(f"No data found for {grade} at hour {start_time.hour}")
        except Exception as e:
            logging.error(f"Error retrieving {grade} data: {str(e)}", exc_info=True)

    if all_batches:
        unique_batches = remove_duplicate_batches(all_batches)
        logging.info(f"Total batches: {len(all_batches)}, Unique batches: {len(unique_batches)}")
        
        # 학년별로 배치 나누기
        batches_by_grade = {grade: [] for grade in grades}
        for batch in unique_batches:
            grade = batch.get("grade")
            if grade in batches_by_grade:
                batches_by_grade[grade].append(batch)

        # Event Hub 전송
        send_responses_by_grade(batches_by_grade, eventhub_conn_str, eventhub_name)
        logging.info(f"Processing completed. Processed {len(unique_batches)} unique batches")
    else:
        logging.info("No data to process")

def remove_duplicate_batches(batches):
    """배치 중복 제거"""
    unique_batches = {}
    for batch in batches:
        batch_id = batch.get('batchId')
        test_id = batch.get('testId')
        unique_key = f"{batch_id}_{test_id}"
        if unique_key not in unique_batches:
            unique_batches[unique_key] = batch
        else:
            logging.warning(f"Duplicate batch found and removed: {unique_key}")
    return list(unique_batches.values())

def send_responses_by_grade(batches_by_grade, connection_str, eventhub_name):
    """
    학년별 순서대로 배치 내 응답을 하나씩 Event Hub로 전송.
    중복 응답은 제외.
    """
    try:
        producer = EventHubProducerClient.from_connection_string(
            conn_str=connection_str,
            eventhub_name=eventhub_name
        )
        sent_hashes = set()
        total_sent = 0

        with producer:
            for grade in ["7학년", "8학년", "9학년"]:
                batches = batches_by_grade.get(grade, [])
                for batch in batches:
                    responses = batch.get("responses", [])
                    if not responses:
                        continue

                    event_batch = producer.create_batch()
                    for response in responses:
                        response_hash = generate_response_hash(response)
                        if response_hash in sent_hashes:
                            continue
                        event_batch.add(EventData(json.dumps(response, ensure_ascii=False)))
                        sent_hashes.add(response_hash)
                        total_sent += 1

                    if len(event_batch) > 0:
                        producer.send_batch(event_batch)
                    logging.info(f"Sent {len(responses)} responses from {grade} batch {batch.get('batchId')}")

        logging.info(f"Total unique responses sent: {total_sent}")

    except Exception as e:
        logging.error(f"Error sending responses to Event Hub: {str(e)}", exc_info=True)