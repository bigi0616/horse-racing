from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import pickle, os, io
import pandas as pd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 모델 로드 ──────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, "mashin_model_v2.pkl"), "rb") as f:
    v2 = pickle.load(f)
MODEL_B      = v2["model"]
FEATURES_B   = v2["features"]

with open(os.path.join(BASE_DIR, "mashin_model_v3_no_odds.pkl"), "rb") as f:
    v3 = pickle.load(f)
MODEL_A      = v3["model"]
FEATURES_A   = v3["features"]

# ── 스키마 ─────────────────────────────────────────────
class Horse(BaseModel):
    hrName:     str
    rating_val: Optional[float] = 0
    prev_ord:   Optional[float] = 0
    prev_ord2:  Optional[float] = 0
    prev_ord3:  Optional[float] = 0
    avg_ord_3:  Optional[float] = 0
    prev_odds:  Optional[float] = 0
    chul_no:    Optional[float] = 0
    rc_dist:    Optional[float] = 0
    jk_winrate: Optional[float] = 0
    tr_winrate: Optional[float] = 0
    odds_val:   Optional[float] = 0
    odds_grp:   Optional[float] = 0
    wg_hr:      Optional[float] = 0
    wg_change:  Optional[float] = 0

class RaceRequest(BaseModel):
    horses: List[Horse]

# ── 공통 예측 함수 ──────────────────────────────────────
def predict_with(model, features, horses):
    df = pd.DataFrame([h.dict() for h in horses])
    X  = df[features].fillna(0)
    probs = model.predict_proba(X)[:, 1]
    total = probs.sum() or 1
    results = []
    for i, h in enumerate(horses):
        results.append({
            "hrName":      h.hrName,
            "win_prob_pct": round(float(probs[i] / total * 100), 1)
        })
    results.sort(key=lambda x: x["win_prob_pct"], reverse=True)
    for rank, r in enumerate(results, 1):
        r["rank"] = rank
    return results

# ── 엔드포인트 ─────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "models": ["v2(B)", "v3(A)"]}

@app.get("/features")
def features_b():
    return {"model": "v2_B", "features": FEATURES_B}

@app.get("/features_v3")
def features_a():
    return {"model": "v3_A", "features": FEATURES_A}

@app.post("/predict")
def predict_b(req: RaceRequest):
    """모델 B (v2, 배당 포함) — 사후 분석용"""
    return {"model": "v2_B", "predictions": predict_with(MODEL_B, FEATURES_B, req.horses)}

@app.post("/predict_v3")
def predict_a(req: RaceRequest):
    """모델 A (v3, 배당 없음) — 실시간 서빙용"""
    return {"model": "v3_A", "predictions": predict_with(MODEL_A, FEATURES_A, req.horses)}

@app.post("/predict_csv")
def predict_csv_b(req: RaceRequest):
    """모델 B CSV 검증용 (하위 호환)"""
    return predict_b(req)
