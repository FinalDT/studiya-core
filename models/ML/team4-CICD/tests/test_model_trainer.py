import pandas as pd
import numpy as np
from src.model_trainer import train_models

def test_train_models():
    df = pd.DataFrame({
        "feature1": [1,2,3,4,5],
        "feature2": [5,4,3,2,1],
        "realScore_clean": [10,20,30,40,50]
    })
    categorical_cols = []
    best_model, best_name, results = train_models(df, categorical_cols)
    assert best_model is not None
    assert best_name in ["dt","rf"]
    assert "rmse" in results[best_name]
