# src/main.py
from pyspark.sql import SparkSession
from src.config_loader import load_config
from src.data_preprocessor import preprocess_dataframe, merge_batch_recent
from src.model_trainer import build_preprocessor, train_models
from src.mlflow_manager import init_experiment, log_model_mlflow
from src.model_serving import predict_with_model

def run_pipeline(config_path: str):
    # 1️⃣ 설정 로드
    config = load_config(config_path)
    jdbc_url = config['jdbc_url']
    connection_properties = config['connection_properties']
    target = config.get('target', 'realScore_clean')
    exclude_cols = config.get('exclude_cols', ['learnerID','testID','correct_cnt','items_attempted'])
    experiment_name = config.get('experiment_name', 'real_score_experiment')
    model_name = config.get('model_name', 'real-score-model')

    # 2️⃣ Spark 세션
    spark = SparkSession.builder.getOrCreate()

    # 3️⃣ 데이터 로드 및 병합
    df_batch = spark.read.jdbc(url=jdbc_url, table=config['batch_table'], properties=connection_properties)
    df_recent = spark.read.jdbc(url=jdbc_url, table=config['recent_table'], properties=connection_properties)
    df_merge = merge_batch_recent(
        df_batch, df_recent,
        rename_map=config.get('rename_map', {'pred_realScore_clean': target}),
        drop_cols=config.get('drop_cols', ['percent_rank','grade_percentile_calc'])
    )

    # 4️⃣ 전처리
    df_processed, categorical_cols = preprocess_dataframe(df_merge)

    # 5️⃣ feature/target 분리
    feature_cols = [c for c in df_processed.columns if c not in ([target]+exclude_cols)]
    X = df_processed[feature_cols]
    y = df_processed[target]

    # 6️⃣ train/test split
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 7️⃣ 전처리 파이프라인
    preprocessor = build_preprocessor(X_train, categorical_cols)

    # 8️⃣ 모델 학습
    train_results = train_models(X_train, y_train, X_test, y_test, preprocessor)

    # 9️⃣ MLflow 기록
    init_experiment(experiment_name)
    log_model_mlflow(
        best_name=train_results['best_name'],
        best_model=train_results['best_model'],
        results=train_results['results'],
        model_name=model_name
    )

    # 10️⃣ 서빙 테스트 (예시)
    sample_preds = predict_with_model(train_results['best_model'], X_test, feature_cols)
    print("Sample predictions:\n", sample_preds.head())

if __name__ == "__main__":
    import sys
    config_path = sys.argv[1] if len(sys.argv) > 1 else "./config.json"
    run_pipeline(config_path)
