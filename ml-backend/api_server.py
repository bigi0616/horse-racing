"""
馬神(마신) 경마 예측 API - Render 배포 버전
pkl 구조: {'model': XGBClassifier, 'features': [컬럼 14개]}
전처리: fillna(0)만 적용 (학습 코드와 동일)
"""
import os
import pickle
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import io

app = FastAPI(title="馬神 Horse Racing Prediction API", version="2.1")

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
    """pkl = {'model': clf, 'features': [...]} 구조로 저장된 모델 로드."""
    global model, feature_names
    if model is None:
        with open(MODEL_PATH, "rb") as f:
            obj = pickle.load(f)
        if isinstance(obj, dict) and "model" in obj and "features" in obj:
            model = obj["model"]
            feature_names = list(obj["features"])
        else:
            # 혹시 다른 포맷일 경우의 폴백
            model = obj
            feature_names = (
                list(getattr(model, "feature_names_in_", []))
                or (model.get_booster().feature_names
                    if hasattr(model, "get_booster") else None)
            )
    return model


@app.on_event("startup")
def startup_event():
    try:
        load_model()
        print(f"[OK] 모델 로드 완료. features({len(feature_names)}): "
              f"{feature_names}")
    except Exception as e:
        print(f"[WARN] 모델 로드 실패(요청 시 재시도): {e}")


class HorseFeatures(BaseModel):
    features: dict


@app.get("/")
def root():
    return {
        "service": "馬神 Horse Racing Prediction API",
        "status": "running",
        "endpoints": ["/predict", "/predict_csv", "/features", "/health"],
    }


@app.get("/health")
def health():
    load_model()
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "n_features": len(feature_names) if feature_names else None,
    }


@app.get("/features")
def get_features():
    """프론트엔드가 어떤 컬럼을 보내야 하는지 확인할 수 있게 노출."""
    load_model()
    return {"features": feature_names, "n_features": len(feature_names)}


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    """학습 코드와 동일하게: 필요한 컬럼만 추리고, 없는 건 0으로 채우고, fillna(0)."""
    for col in feature_names:
        if col not in df.columns:
            df[col] = 0
    return df[feature_names].fillna(0)


@app.post("/predict")
def predict(payload: HorseFeatures):
    """단일 마필의 우승 확률."""
    load_model()
    try:
        df = pd.DataFrame([payload.features])
        X = _prepare(df)
        proba = float(model.predict_proba(X)[0][1])
        return {"win_probability": proba}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"예측 실패: {e}")


@app.post("/predict_csv")
async def predict_csv(file: UploadFile = File(...)):
    """출주표 CSV → 마필별 우승 확률 + 순위."""
    load_model()
    try:
        content = await file.read()
        # 한국어 헤더 대응: utf-8-sig 우선, 실패 시 cp949
        try:
            df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(content), encoding="cp949")

        original = df.copy()
        X = _prepare(df.copy())
        probas = model.predict_proba(X)[:, 1]

        # 1위 합이 1이 되도록 경주 단위로 정규화 (학습 테스트 코드와 동일한 방식)
        total = probas.sum()
        norm_pct = (probas / total * 100).round(2) if total > 0 else probas * 0

        original["win_probability"] = probas
        original["win_probability_pct"] = norm_pct
        original = original.sort_values(
            "win_probability", ascending=False
        ).reset_index(drop=True)
        original["predicted_rank"] = original.index + 1

        id_cols = [c for c in ["hrName", "마명", "chul_no", "마번",
                               "horse_name", "horse_no"]
                   if c in original.columns]
        result_cols = id_cols + ["predicted_rank",
                                 "win_probability", "win_probability_pct"]
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
