import os
import mlflow
import mlflow.pyfunc
import mlflow.sklearn
import pandas as pd
import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm
from io import BytesIO
from math import sqrt
from azure.storage.blob import BlobServiceClient
import logging

# ----------------------
# 로깅 설정
# ----------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------
# 상수: Azure Blob Storage
# ----------------------
BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONN_STR","DefaultEndpointsProtocol=https;AccountName=team4mlblob;AccountKey=qU3qjqdPjn/LlGZzIfI/ox6zVb6BhIo1Dn1PRr4akHTJLlpQ9x8rHbtZsRFvTCgjh5Qpn/4td+q3+AStbBi+PQ==;EndpointSuffix=core.windows.net")
blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
CONTAINER_NAME = "blobml"
BLOB_NAME = "bronze_questions.csv"

# ----------------------
# RealtimeRealScoreModel 클래스 정의
# ----------------------
class RealtimeRealScoreModel(mlflow.pyfunc.PythonModel):
    """
    실시간 실력점수 추론 모델
    입력: learnerID, testID, assessmentItemID, is_correct
    출력: theta, realScore_clean, percentile, top_percent
    """

    def load_context(self, context):
        """MLflow 컨텍스트에서 베이스 모델 로드"""
        self.model = mlflow.sklearn.load_model(context.artifacts["model"])
        logger.info("베이스 모델 로드 완료")

    def fetch_bronze_question(self):
        """Azure Blob Storage에서 bronze_questions.csv 불러오기"""
        blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=BLOB_NAME)
        download_stream = blob_client.download_blob()
        df_bronze = pd.read_csv(BytesIO(download_stream.readall()))
        logger.info(f"Bronze questions 데이터 로드 완료: {len(df_bronze)}행")
        return df_bronze

    def prepare_input(self, df_input):
        """입력 데이터와 bronze_question 조인 및 전처리"""
        df_bronze = self.fetch_bronze_question()
        if not df_input.empty and not df_bronze.empty:
            join_cols = ["testID", "assessmentItemID"]
            for col in join_cols:
                df_input[col] = df_input[col].astype(str)
                df_bronze[col] = df_bronze[col].astype(str)
            df_merged = pd.merge(df_input, df_bronze, on=join_cols, how="left")
            # _x/_y 처리
            for col in list(df_merged.columns):
                if col.endswith('_x'):
                    base_col = col[:-2]
                    bronze_col = f"{base_col}_y"
                    df_merged[base_col] = df_merged[col].combine_first(df_merged.get(bronze_col, None))
            df_merged = df_merged[[c for c in df_merged.columns if not c.endswith('_x') and not c.endswith('_y')]]
        else:
            df_merged = df_bronze.copy() if not df_bronze.empty else df_input.copy()

        required_cols = ['is_correct', 'grade', 'gender', 'discriminationLevel', 'difficultyLevel', 'guessLevel']
        df_merged = df_merged.reindex(columns=df_merged.columns.union(required_cols))
        for col in required_cols:
            df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce')
        return df_merged

    def estimate_theta(self, a_list, b_list, c_list, y_list, grid_n=161):
        """3PL 모델 능력 추정"""
        def p_3pl(theta, a, b, c):
            z = np.outer(theta, a) - a * b
            sigmoid = 1 / (1 + np.exp(-np.clip(z, -500, 500)))
            return c + (1 - c) * sigmoid

        def neg_loglike(th):
            probs = p_3pl(np.array([th[0]]), a_list, b_list, c_list)[0]
            probs = np.clip(probs, 1e-12, 1-1e-12)
            return -np.sum(y_list * np.log(probs) + (1-y_list) * np.log(1-probs))

        res = minimize(neg_loglike, x0=[0.0], bounds=[(-4.0, 4.0)], method='L-BFGS-B')
        theta_mle = float(res.x[0]) if res.success else np.nan

        theta_grid = np.linspace(-4, 4, grid_n)
        probs_grid = p_3pl(theta_grid, a_list, b_list, c_list)
        probs_grid = np.clip(probs_grid, 1e-12, 1-1e-12)
        log_lik = np.sum(y_list*np.log(probs_grid) + (1-y_list)*np.log(1-probs_grid), axis=1)
        log_post = log_lik + norm.logpdf(theta_grid, 0, 1)
        log_post = log_post - np.max(log_post)
        post = np.exp(log_post) / np.sum(np.exp(log_post))
        theta_eap = float(np.sum(post * theta_grid))
        theta_sd = sqrt(np.sum((theta_grid - theta_eap)**2 * post))
        expected_score = float(np.sum(p_3pl([theta_eap], a_list, b_list, c_list)[0]))
        return theta_mle, theta_eap, theta_sd, expected_score

    def calculate_theta_features(self, df_input):
        results = []
        for (learner, test), group in df_input.groupby(['learnerID', 'testID']):
            a_list = group['discriminationLevel'].fillna(1.0).values
            b_list = group['difficultyLevel'].fillna(0.0).values
            c_list = group['guessLevel'].fillna(0.0).values
            y_list = group['is_correct'].fillna(0).astype(int).values
            theta_mle, theta_eap, theta_sd, expected_score = self.estimate_theta(a_list, b_list, c_list, y_list) if len(y_list) > 0 else (np.nan,0,1,0)
            results.append({
                'learnerID': learner,
                'testID': test,
                'gender': group['gender'].iloc[0] if 'gender' in group.columns else np.nan,
                'grade': group['grade'].iloc[0] if 'grade' in group.columns else np.nan,
                'theta_clean': theta_eap,
                'theta_sd': theta_sd,
                'difficultyLevel': group['difficultyLevel'].mean(),
                'discriminationLevel': group['discriminationLevel'].mean(),
                'guessLevel': group['guessLevel'].mean(),
                'correct_cnt': int(y_list.sum()),
                'items_attempted': len(y_list),
                'expected_score': expected_score
            })
        df_features = pd.DataFrame(results)
        df_features['accuracy'] = df_features['correct_cnt'] / df_features['items_attempted'].replace(0,1)
        return df_features

    def calculate_percentile(self, df_features, reference_df):
        """학년별 백분위 계산 (배치 데이터 기준)"""
        combined_df = pd.concat([reference_df, df_features], ignore_index=True)

        def calc_percentile(row):
            grade_scores = combined_df[combined_df['grade']==row['grade']]['realScore_clean'].dropna()
            if len(grade_scores) == 0:
                return 50.0
            return (grade_scores < row['realScore_clean']).mean() * 100

        df_features['percentile'] = df_features.apply(calc_percentile, axis=1)
        df_features['top_percent'] = 100 - df_features['percentile']
        return df_features

    def predict(self, context, model_input: pd.DataFrame):
        df_merged = self.prepare_input(model_input)
        if df_merged.empty:
            return pd.DataFrame({'error':['입력 데이터가 없습니다']})
        
        df_features = self.calculate_theta_features(df_merged)

        feature_cols = ['theta_clean', 'accuracy', 'grade', 'gender', 'difficultyLevel', 'discriminationLevel', 'guessLevel']
        for col in feature_cols:
            df_features[col] = pd.to_numeric(df_features.get(col, 0.0), errors='coerce').fillna(0.0)

        if hasattr(self, 'model') and self.model is not None:
            df_features['realScore_clean'] = self.model.predict(df_features[feature_cols])
        else:
            df_features['realScore_clean'] = df_features['theta_clean'] * 100 + 500

        return df_features
