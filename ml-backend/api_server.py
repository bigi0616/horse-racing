"""
馬神(마신) 경마 예측 API 서버 - Render.com 배포 버전
XGBoost 모델(mashin_model_v2.pkl)로 우승마 확률을 예측한다.
"""
import os
import pickle
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import io

app = FastAPI(title="馬神 Horse Racing Prediction API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "mashin_model_v2.pkl")

model = None
feature_names = None


def load_model():
    global model, feature_names
    if model is None:
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        if hasattr(model, "feature_names_in_"):
            feature_names = list(model.feature_names_in_)
        elif hasattr(model, "get_booster"):
            feature_names = model.get_booster().feature_names
        else:
            feature_names = None
    return model


@app.on_event("startup")
def startup_event():
    try:
        load_model()
        print(f"[OK] 모델 로드 완료. feature 수: "
              f"{len(feature_names) if feature_names else 'unknown'}")
    except Exception as e:
        print(f"[WARN] 모델 로드 실패(요청 시 재시도): {e}")


class HorseFeatures(BaseModel):
    features: dict


@app.get("/")
def root():
    return {
        "service": "馬神 Horse Racing Prediction API",
        "status": "running",
        "endpoints": ["/predict", "/predict_csv", "/health"],
    }


@app.get("/health")
def health():
    try:
        load_model()
        return {"status": "healthy", "model_loaded": model is not None,
                "n_features": len(feature_names) if feature_names else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _align_features(df):
    if feature_names is None:
        return df
    for col in feature_names:
        if col not in df.columns:
            df[col] = 0
    return df[feature_names]


@app.post("/predict")
def predict(payload: HorseFeatures):
    load_model()
    try:
        df = pd.DataFrame([payload.features])
        df = _align_features(df)
        proba = float(model.predict_proba(df)[0][1])
        return {"win_probability": proba}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"예측 실패: {e}")


@app.post("/predict_csv")
async def predict_csv(file: UploadFile = File(...)):
    load_model()
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        original = df.copy()

        X = _align_features(df.copy())
        probas = model.predict_proba(X)[:, 1]

        original["win_probability"] = probas
        original = original.sort_values(
            "win_probability", ascending=False
        ).reset_index(drop=True)
        original["predicted_rank"] = original.index + 1

        id_cols = [c for c in ["마명", "마번", "horse_name", "horse_no"]
                   if c in original.columns]
        result_cols = id_cols + ["predicted_rank", "win_probability"]
        results = original[result_cols].to_dict(orient="records")

        return {
            "n_horses": len(results),
            "predictions": results,
            "top_pick": results[0] if results else None,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSV 예측 실패: {e}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api_server:app", host="0.0.0.0", port=port)
