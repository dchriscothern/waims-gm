from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict, List, Literal, Optional, TypedDict

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from jose import jwk, jwt
from jose.utils import base64url_decode
from pydantic import BaseModel, Field

from waims_gm.domain import Player, TeamContext
from waims_gm.services import evaluate_single_player


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_JWT_AUD = os.getenv("SUPABASE_JWT_AUD", "authenticated")
SUPABASE_ISSUER = f"{SUPABASE_URL}/auth/v1" if SUPABASE_URL else ""

app = FastAPI(title="WAIMS GM API", version="0.1.0")


class PlayerIn(BaseModel):
    id: str
    name: str
    position: str = Field(description="Example: G, F, C")
    age: int

    offense_rating: float
    defense_rating: float
    shooting_rating: float
    playmaking_rating: float
    rebounding_rating: float

    health_risk: float
    upside: float
    minutes_stability: float

    expected_cost_tier: int


class TeamContextIn(BaseModel):
    gm_id: str
    team_id: str
    timeline: Literal["win_now", "balanced", "rebuild"]
    needs_by_position: Dict[str, float]
    cap_flexibility: float
    risk_tolerance: float


class EvaluateRequest(BaseModel):
    player: PlayerIn
    ctx: TeamContextIn


class EvaluationOut(BaseModel):
    overall_score: float
    components: Dict[str, float]
    assumptions: Dict[str, str]
    tension_points: List[str]
    recommended_action: Literal["draft", "sign", "pass"]
    player: Dict


class EvaluateAndSaveRequest(BaseModel):
    player: PlayerIn
    ctx: TeamContextIn
    display_name: Optional[str] = None


class EvaluateAndSaveOut(EvaluationOut):
    evaluation_id: str


class AuthedGM(TypedDict):
    gm_id: str
    token: str


def _require_env():
    if not SUPABASE_URL:
        raise HTTPException(status_code=500, detail="SUPABASE_URL is not set")
    if not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=500, detail="SUPABASE_ANON_KEY is not set")


@lru_cache(maxsize=1)
def _jwks_url() -> str:
    return f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    _require_env()
    with httpx.Client(timeout=10) as client:
        r = client.get(_jwks_url())
        r.raise_for_status()
        return r.json()


def _verify_supabase_jwt(token: str) -> dict:
    _require_env()

    try:
        header = jwt.get_unverified_header(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token header: {e}")

    kid = header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Token missing kid")

    jwks = _get_jwks()
    keys = jwks.get("keys", [])
    key_dict = next((k for k in keys if k.get("kid") == kid), None)
    if not key_dict:
        _get_jwks.cache_clear()
        jwks = _get_jwks()
        keys = jwks.get("keys", [])
        key_dict = next((k for k in keys if k.get("kid") == kid), None)
        if not key_dict:
            raise HTTPException(status_code=401, detail="Unknown signing key (kid)")

    public_key = jwk.construct(key_dict)

    message, encoded_sig = token.rsplit(".", 1)
    decoded_sig = base64url_decode(encoded_sig.encode())

    if not public_key.verify(message.encode(), decoded_sig):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    claims = jwt.get_unverified_claims(token)

    if SUPABASE_ISSUER and claims.get("iss") != SUPABASE_ISSUER:
        raise HTTPException(status_code=401, detail="Invalid issuer")
    if SUPABASE_JWT_AUD and claims.get("aud") != SUPABASE_JWT_AUD:
        raise HTTPException(status_code=401, detail="Invalid audience")

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token missing sub")

    return claims


def get_current_gm(authorization: str = Header(default="")) -> AuthedGM:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    claims = _verify_supabase_jwt(token)
    return {"gm_id": claims["sub"], "token": token}


def _sb_headers(user_token: str) -> dict:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/evaluate", response_model=EvaluationOut)
def evaluate(req: EvaluateRequest):
    player = Player(**req.player.model_dump())
    ctx = TeamContext(**req.ctx.model_dump())
    scorecard = evaluate_single_player(player, ctx)

    return EvaluationOut(
        overall_score=scorecard.overall_score,
        components=scorecard.components,
        assumptions=scorecard.assumptions,
        tension_points=scorecard.tension_points,
        recommended_action=scorecard.recommended_action,
        player=scorecard.player.__dict__,
    )


@app.post("/evaluate-and-save", response_model=EvaluateAndSaveOut)
def evaluate_and_save(req: EvaluateAndSaveRequest, gm: AuthedGM = Depends(get_current_gm)):
    ctx_dict = req.ctx.model_dump()
    ctx_dict["gm_id"] = gm["gm_id"]

    player = Player(**req.player.model_dump())
    ctx = TeamContext(**ctx_dict)
    scorecard = evaluate_single_player(player, ctx)

    profile_payload = {"gm_id": gm["gm_id"]}
    if req.display_name:
        profile_payload["display_name"] = req.display_name

    with httpx.Client(timeout=15) as client:
        prof_url = f"{SUPABASE_URL}/rest/v1/gm_profiles?on_conflict=gm_id"
        prof_headers = _sb_headers(gm["token"]) | {"Prefer": "resolution=merge-duplicates,return=minimal"}
        r1 = client.post(prof_url, headers=prof_headers, json=profile_payload)
        if r1.status_code not in (200, 201, 204):
            raise HTTPException(status_code=500, detail=f"Supabase profile upsert failed: {r1.status_code} {r1.text}")

        eval_url = f"{SUPABASE_URL}/rest/v1/gm_evaluations"
        eval_headers = _sb_headers(gm["token"]) | {"Prefer": "return=representation"}
        eval_payload = {
            "gm_id": gm["gm_id"],
            "team_id": ctx.team_id,
            "player": scorecard.player.__dict__,
            "ctx": ctx_dict,
            "overall_score": scorecard.overall_score,
            "components": scorecard.components,
            "assumptions": scorecard.assumptions,
            "tension_points": scorecard.tension_points,
            "recommended_action": scorecard.recommended_action,
        }
        r2 = client.post(eval_url, headers=eval_headers, json=eval_payload)
        if r2.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail=f"Supabase evaluation insert failed: {r2.status_code} {r2.text}")

        created = r2.json()
        evaluation_id = created[0]["id"] if isinstance(created, list) and created else created.get("id")

    return EvaluateAndSaveOut(
        evaluation_id=str(evaluation_id),
        overall_score=scorecard.overall_score,
        components=scorecard.components,
        assumptions=scorecard.assumptions,
        tension_points=scorecard.tension_points,
        recommended_action=scorecard.recommended_action,
        player=scorecard.player.__dict__,
    )