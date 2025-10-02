import os
import json
import asyncio
import datetime
from datetime import timedelta
from collections import defaultdict
from azure.storage.blob import BlobServiceClient
from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient
import concurrent.futures
from pathlib import Path

class BatchDataProcessor:
    def __init__(self, connection_string, container_name="processed-data"):
        self.connection_string = connection_string
        self.container_name = container_name
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # 요일 매핑
        self.day_mapping = {
            0: "monday", 1: "tuesday", 2: "wednesday", 3: "thursday",
            4: "friday", 5: "saturday", 6: "sunday"
        }
        
    def setup_container(self):
        """컨테이너 생성"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            container_client.create_container()
            print(f"Container '{self.container_name}' created successfully.")
        except Exception as e:
            if "ContainerAlreadyExists" in str(e):
                print(f"Container '{self.container_name}' already exists.")
            else:
                print(f"Error creating container: {e}")

    def parse_filename(self, filename):
        """파일명에서 정보 추출: A070000008_A070000001_A070001001.json"""
        name_without_ext = filename.replace('.json', '')
        parts = name_without_ext.split('_')
        if len(parts) == 3:
            return {
                'learner_id': parts[0],
                'test_id': parts[1], 
                'item_id': parts[2]
            }
        return None

    def load_json_file(self, file_path):
        """JSON 파일 로드"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None

    def map_timestamp_to_current(self, original_timestamp):
        """과거 timestamp를 현재 날짜 기준으로 매핑"""
        try:
            original_dt = datetime.datetime.strptime(original_timestamp, "%Y-%m-%d %H:%M:%S")
            current_date = datetime.datetime.now().date()
            
            # 현재 날짜 + 원본 시간
            mapped_dt = datetime.datetime.combine(current_date, original_dt.time())
            
            # 요일 차이 계산해서 조정
            original_weekday = original_dt.weekday()
            current_weekday = datetime.datetime.now().weekday()
            day_diff = original_weekday - current_weekday
            
            if day_diff != 0:
                mapped_dt += timedelta(days=day_diff)
                
            return mapped_dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"Error mapping timestamp {original_timestamp}: {e}")
            return original_timestamp

    def group_responses_into_batches(self, responses):
        """응답을 테스트별, 시간별 배치로 그룹화"""
        batches = defaultdict(lambda: defaultdict(list))
        
        for response in responses:
            test_id = response.get('testID')
            timestamp = response.get('Timestamp')
            
            if not test_id or not timestamp:
                continue
                
            try:
                dt = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                hour_key = dt.strftime("%Y-%m-%d_%H")  # 날짜_시간으로 그룹화
                batches[test_id][hour_key].append(response)
            except Exception as e:
                print(f"Error processing timestamp {timestamp}: {e}")
                
        return batches

    def create_batch_data(self, test_id, hour_key, responses):
        """배치 데이터 생성"""
        if not responses:
            return None
            
        # 가장 늦은 timestamp 찾기
        latest_response = max(responses, key=lambda x: x.get('Timestamp', ''))
        latest_timestamp = latest_response.get('Timestamp')
        
        if not latest_timestamp:
            return None
            
        try:
            latest_dt = datetime.datetime.strptime(latest_timestamp, "%Y-%m-%d %H:%M:%S")
            mapped_timestamp = self.map_timestamp_to_current(latest_timestamp)
            mapped_dt = datetime.datetime.strptime(mapped_timestamp, "%Y-%m-%d %H:%M:%S")
            
            day_of_week = self.day_mapping[latest_dt.weekday()]
            
            batch_data = {
                "batchId": f"{test_id}_{latest_dt.strftime('%Y%m%d%H%M%S')}",
                "testId": test_id,
                "latestTimestamp": latest_timestamp,
                "mappedTimestamp": mapped_timestamp,
                "dayOfWeek": day_of_week,
                "hour": latest_dt.hour,
                "itemCount": len(responses),
                "responses": responses
            }
            
            return batch_data, day_of_week, latest_dt.hour
            
        except Exception as e:
            print(f"Error creating batch data: {e}")
            return None

    def process_grade_folder(self, grade_path):
        """학년 폴더 처리"""
        grade_name = os.path.basename(grade_path)
        print(f"Processing {grade_name}...")
        
        all_responses = []
        
        # 모든 하위 폴더 탐색
        for root, dirs, files in os.walk(grade_path):
            if "문항정오답표" in root:
                for filename in files:
                    if filename.endswith('.json'):
                        file_path = os.path.join(root, filename)
                        file_info = self.parse_filename(filename)
                        
                        if file_info:
                            data = self.load_json_file(file_path)
                            if data:
                                all_responses.append(data)
        
        print(f"{grade_name}: Loaded {len(all_responses)} responses")
        
        # 배치로 그룹화
        batches = self.group_responses_into_batches(all_responses)
        
        uploaded_count = 0
        for test_id, hour_groups in batches.items():
            for hour_key, responses in hour_groups.items():
                # 진단평가 6문항만 처리 (필요시 필터링 로직 추가)
                if len(responses) >= 6:  # 최소 6문항 응답이 있는 경우만
                    batch_info = self.create_batch_data(test_id, hour_key, responses[:6])
                    
                    if batch_info:
                        batch_data, day_of_week, hour = batch_info
                        
                        # Blob 경로 생성
                        blob_name = f"{grade_name}/batches/{day_of_week}/hour-{hour:02d}/{batch_data['batchId']}.json"
                        
                        # Blob 업로드
                        success = self.upload_to_blob(blob_name, batch_data)
                        if success:
                            uploaded_count += 1
                            
        print(f"{grade_name}: Uploaded {uploaded_count} batches")
        return uploaded_count

    def upload_to_blob(self, blob_name, data):
        """Blob에 데이터 업로드"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_name
            )
            
            json_data = json.dumps(data, ensure_ascii=False, indent=2)
            blob_client.upload_blob(json_data, overwrite=True)
            
            print(f"Uploaded: {blob_name}")
            return True
            
        except Exception as e:
            print(f"Error uploading {blob_name}: {e}")
            return False

    def process_all_grades_parallel(self, data_root_path):
        """모든 학년을 병렬로 처리"""
        grade_folders = []
        
        # 학년 폴더 찾기
        for item in os.listdir(data_root_path):
            item_path = os.path.join(data_root_path, item)
            if os.path.isdir(item_path) and ("학년" in item):
                grade_folders.append(item_path)
        
        print(f"Found grade folders: {[os.path.basename(f) for f in grade_folders]}")
        
        # 컨테이너 설정
        self.setup_container()
        
        # 병렬 처리
        total_uploaded = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_grade = {
                executor.submit(self.process_grade_folder, grade_path): grade_path 
                for grade_path in grade_folders
            }
            
            for future in concurrent.futures.as_completed(future_to_grade):
                grade_path = future_to_grade[future]
                try:
                    uploaded_count = future.result()
                    total_uploaded += uploaded_count
                    print(f"Completed: {os.path.basename(grade_path)} - {uploaded_count} batches")
                except Exception as e:
                    print(f"Error processing {grade_path}: {e}")
        
        print(f"Total uploaded batches: {total_uploaded}")
        return total_uploaded

# 사용 예제
def main():
    # Azure Blob Storage 연결 문자열
    connection_string = "your_connection_string_here"
    
    # 데이터 루트 경로
    data_root_path = "./Data"
    
    # 프로세서 초기화
    processor = BatchDataProcessor(connection_string)
    
    # 모든 학년 데이터 처리
    processor.process_all_grades_parallel(data_root_path)

# Timer Trigger용 시간 기반 데이터 조회 함수
class TimerTriggerDataRetriever:
    def __init__(self, connection_string, container_name="processed-data"):
        self.connection_string = connection_string
        self.container_name = container_name
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        self.day_mapping = {
            0: "monday", 1: "tuesday", 2: "wednesday", 3: "thursday",
            4: "friday", 5: "saturday", 6: "sunday"
        }

    def get_korea_now(self):
        """한국 시간 기준 현재 시각 반환 (분, 초, 마이크로초는 0으로 설정)"""
        utc_now = datetime.datetime.utcnow()
        korea_now = utc_now + datetime.timedelta(hours=9)
        return korea_now.replace(minute=0, second=0, microsecond=0)

    def get_previous_hour_data(self, grade="7학년"):
        """이전 시간대 데이터 조회 (한국시간 기준)"""
        korea_now = self.get_korea_now()
        prev_hour = korea_now - timedelta(hours=1)
        
        day_of_week = self.day_mapping[prev_hour.weekday()]
        hour = prev_hour.hour
        
        print(f"Retrieving data for {grade} - {day_of_week} {hour:02d}:00 (KST: {prev_hour.isoformat()})")
        
        blob_prefix = f"{grade}/batches/{day_of_week}/hour-{hour:02d}/"
        
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            blob_list = container_client.list_blobs(name_starts_with=blob_prefix)
            
            batches = []
            for blob in blob_list:
                try:
                    blob_client = self.blob_service_client.get_blob_client(
                        container=self.container_name, 
                        blob=blob.name
                    )
                    
                    content = blob_client.download_blob().readall()
                    batch_data = json.loads(content.decode('utf-8'))
                    
                    # 배치 데이터 검증 및 로깅
                    print(f"Found batch: {batch_data.get('batchId')} - "
                          f"Day: {batch_data.get('dayOfWeek')}, "
                          f"Hour: {batch_data.get('hour')}, "
                          f"Items: {batch_data.get('itemCount')}")
                    
                    batches.append(batch_data)
                    
                except Exception as e:
                    print(f"Error processing blob {blob.name}: {e}")
                    continue
                
            print(f"Retrieved {len(batches)} batches for {grade} - {day_of_week} {hour:02d}:00")
            return batches
            
        except Exception as e:
            print(f"Error retrieving data for {grade}: {e}")
            return []

    def get_batches_by_time_filter(self, grade, target_hour, target_day_of_week):
        """특정 시간과 요일로 배치 데이터 조회"""
        print(f"Retrieving data for {grade} - {target_day_of_week} {target_hour:02d}:00")
        
        blob_prefix = f"{grade}/batches/{target_day_of_week}/hour-{target_hour:02d}/"
        
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            blob_list = container_client.list_blobs(name_starts_with=blob_prefix)
            
            batches = []
            for blob in blob_list:
                try:
                    blob_client = self.blob_service_client.get_blob_client(
                        container=self.container_name, 
                        blob=blob.name
                    )
                    
                    content = blob_client.download_blob().readall()
                    batch_data = json.loads(content.decode('utf-8'))
                    
                    # 배치 데이터 검증
                    if (batch_data.get('hour') == target_hour and 
                        batch_data.get('dayOfWeek') == target_day_of_week):
                        
                        print(f"Found matching batch: {batch_data.get('batchId')} - "
                              f"Day: {batch_data.get('dayOfWeek')}, "
                              f"Hour: {batch_data.get('hour')}, "
                              f"Items: {batch_data.get('itemCount')}")
                        
                        batches.append(batch_data)
                    
                except Exception as e:
                    print(f"Error processing blob {blob.name}: {e}")
                    continue
                
            print(f"Retrieved {len(batches)} matching batches for {grade}")
            return batches
            
        except Exception as e:
            print(f"Error retrieving data for {grade}: {e}")
            return []

if __name__ == "__main__":
    main()