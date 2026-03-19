from __future__ import annotations
from functools import lru_cache
from typing import Dict, List, Literal, Optional, TypedDict

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwk, jwt
from jose.utils import base64url_decode
from pydantic import BaseModel, Field

from app.config import (
    IS_LIVE_ENV,
    SUPABASE_ANON_KEY,
    SUPABASE_ISSUER,
    SUPABASE_JWT_AUD,
    SUPABASE_URL,
    WAIMS_ENV,
    WAIMS_ENV_LABEL,
)
from waims_gm.domain import Player, TeamContext
from waims_gm.services import evaluate_single_player

app = FastAPI(title="WAIMS GM API", version="0.2.0")
security = HTTPBearer()


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
    team_id: str
    timeline: Literal["win_now", "balanced", "rebuild"]
    needs_by_position: Dict[str, float]
    cap_flexibility: float
    risk_tolerance: float


class EvaluateRequest(BaseModel):
    player: PlayerIn
    ctx: TeamContextIn
    mode: Optional[str] = "pro_wnba"


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
    summary_note: Optional[str] = None
    strengths: Optional[str] = None
    concerns: Optional[str] = None
    mode: Optional[str] = "pro_wnba"


class EvaluateAndSaveOut(EvaluationOut):
    evaluation_id: str
    summary_note: Optional[str] = None
    strengths: Optional[str] = None
    concerns: Optional[str] = None
    mode: Optional[str] = None


class EvaluationListItem(BaseModel):
    id: str
    gm_id: str
    team_id: Optional[str] = None
    overall_score: float
    recommended_action: str
    created_at: Optional[str] = None
    player: Dict
    summary_note: Optional[str] = None
    mode: Optional[str] = None


class EvaluationDetailOut(BaseModel):
    id: str
    gm_id: str
    team_id: Optional[str] = None
    overall_score: float
    components: Dict[str, float]
    assumptions: Dict[str, str]
    tension_points: List[str]
    recommended_action: str
    player: Dict
    ctx: Dict
    created_at: Optional[str] = None
    summary_note: Optional[str] = None
    strengths: Optional[str] = None
    concerns: Optional[str] = None
    mode: Optional[str] = None


class DeleteOut(BaseModel):
    ok: bool
    deleted_id: str


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


def get_current_gm(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthedGM:
    token = credentials.credentials
    claims = _verify_supabase_jwt(token)
    return {"gm_id": claims["sub"], "token": token}


def _sb_headers(user_token: str) -> dict:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def sb_headers(user_token: str) -> dict:
    return _sb_headers(user_token)


def _raise_for_supabase_error(action: str, response: httpx.Response) -> None:
    if response.status_code in (200, 201, 204):
        return

    detail = f"Supabase {action} failed: {response.status_code} {response.text}"

    if response.status_code == 401:
        raise HTTPException(status_code=401, detail=detail)
    if response.status_code == 403:
        raise HTTPException(status_code=403, detail=detail)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail=detail)
    if response.status_code in (400, 409, 422):
        raise HTTPException(status_code=400, detail=detail)

    raise HTTPException(status_code=500, detail=detail)


def _perform_supabase_request(action: str, request_fn):
    try:
        return request_fn()
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Supabase {action} request failed: {exc}",
        ) from exc


def upsert_gm_profile(*, gm_id: str, user_token: str, display_name: Optional[str] = None) -> None:
    profile_payload = {"gm_id": gm_id}
    if display_name:
        profile_payload["display_name"] = display_name

    with httpx.Client(timeout=15) as client:
        prof_url = f"{SUPABASE_URL}/rest/v1/gm_profiles?on_conflict=gm_id"
        prof_headers = _sb_headers(user_token) | {
            "Prefer": "resolution=merge-duplicates,return=minimal"
        }
        response = _perform_supabase_request(
            "profile upsert",
            lambda: client.post(prof_url, headers=prof_headers, json=profile_payload),
        )
        _raise_for_supabase_error("profile upsert", response)


def insert_evaluation(
    *,
    gm_id: str,
    user_token: str,
    ctx_dict: Dict,
    scorecard,
    summary_note: Optional[str] = None,
    strengths: Optional[str] = None,
    concerns: Optional[str] = None,
    mode: Optional[str] = None,
) -> str:
    eval_payload = {
        "gm_id": gm_id,
        "team_id": ctx_dict["team_id"],
        "player": scorecard.player.__dict__,
        "ctx": ctx_dict,
        "overall_score": scorecard.overall_score,
        "components": scorecard.components,
        "assumptions": scorecard.assumptions,
        "tension_points": scorecard.tension_points,
        "recommended_action": scorecard.recommended_action,
        "summary_note": summary_note,
        "strengths": strengths,
        "concerns": concerns,
        "mode": mode,
    }

    with httpx.Client(timeout=15) as client:
        eval_url = f"{SUPABASE_URL}/rest/v1/gm_evaluations"
        eval_headers = _sb_headers(user_token) | {"Prefer": "return=representation"}
        response = _perform_supabase_request(
            "evaluation insert",
            lambda: client.post(eval_url, headers=eval_headers, json=eval_payload),
        )
        _raise_for_supabase_error("evaluation insert", response)
        created = response.json()
        evaluation_id = created[0]["id"] if isinstance(created, list) and created else created.get("id")
        return str(evaluation_id)


@app.get("/health")
def health():
    return {
        "ok": True,
        "environment": WAIMS_ENV,
        "environment_label": WAIMS_ENV_LABEL,
        "live": IS_LIVE_ENV,
    }


@app.post("/evaluate", response_model=EvaluationOut)
def evaluate(req: EvaluateRequest):
    ctx_dict = req.ctx.model_dump()
    ctx_dict["gm_id"] = "anonymous-preview"
    ctx_dict["mode"] = req.mode or "pro_wnba"

    player = Player(**req.player.model_dump())
    ctx = TeamContext(**ctx_dict)
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
def evaluate_and_save(
    req: EvaluateAndSaveRequest,
    gm: AuthedGM = Depends(get_current_gm),
):
    ctx_dict = req.ctx.model_dump()
    ctx_dict["gm_id"] = gm["gm_id"]
    ctx_dict["mode"] = req.mode or "pro_wnba"

    player = Player(**req.player.model_dump())
    ctx = TeamContext(**ctx_dict)
    scorecard = evaluate_single_player(player, ctx)

    upsert_gm_profile(
        gm_id=gm["gm_id"],
        user_token=gm["token"],
        display_name=req.display_name,
    )
    evaluation_id = insert_evaluation(
        gm_id=gm["gm_id"],
        user_token=gm["token"],
        ctx_dict=ctx_dict,
        scorecard=scorecard,
        summary_note=req.summary_note,
        strengths=req.strengths,
        concerns=req.concerns,
        mode=req.mode,
    )

    return EvaluateAndSaveOut(
        evaluation_id=str(evaluation_id),
        overall_score=scorecard.overall_score,
        components=scorecard.components,
        assumptions=scorecard.assumptions,
        tension_points=scorecard.tension_points,
        recommended_action=scorecard.recommended_action,
        player=scorecard.player.__dict__,
        summary_note=req.summary_note,
        strengths=req.strengths,
        concerns=req.concerns,
        mode=req.mode,
    )


@app.get("/evaluations", response_model=List[EvaluationListItem])
def list_evaluations(gm: AuthedGM = Depends(get_current_gm)):
    url = (
        f"{SUPABASE_URL}/rest/v1/gm_evaluations"
        f"?gm_id=eq.{gm['gm_id']}"
        f"&select=id,gm_id,team_id,overall_score,recommended_action,created_at,player,summary_note,mode"
        f"&order=created_at.desc"
    )

    with httpx.Client(timeout=15) as client:
        r = _perform_supabase_request(
            "evaluation list",
            lambda: client.get(url, headers=_sb_headers(gm["token"])),
        )
        _raise_for_supabase_error("evaluation list", r)
        rows = r.json()

    return [
        EvaluationListItem(
            id=str(row["id"]),
            gm_id=str(row["gm_id"]),
            team_id=row.get("team_id"),
            overall_score=row["overall_score"],
            recommended_action=row["recommended_action"],
            created_at=row.get("created_at"),
            player=row["player"],
            summary_note=row.get("summary_note"),
            mode=row.get("mode"),
        )
        for row in rows
    ]


@app.get("/evaluations/{evaluation_id}", response_model=EvaluationDetailOut)
def get_evaluation(evaluation_id: str, gm: AuthedGM = Depends(get_current_gm)):
    url = (
        f"{SUPABASE_URL}/rest/v1/gm_evaluations"
        f"?id=eq.{evaluation_id}"
        f"&gm_id=eq.{gm['gm_id']}"
        f"&select=id,gm_id,team_id,overall_score,components,assumptions,tension_points,recommended_action,player,ctx,created_at,summary_note,strengths,concerns,mode"
    )

    with httpx.Client(timeout=15) as client:
        r = _perform_supabase_request(
            "evaluation detail",
            lambda: client.get(url, headers=_sb_headers(gm["token"])),
        )
        _raise_for_supabase_error("evaluation detail", r)
        rows = r.json()

    if not rows:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    row = rows[0]
    return EvaluationDetailOut(
        id=str(row["id"]),
        gm_id=str(row["gm_id"]),
        team_id=row.get("team_id"),
        overall_score=row["overall_score"],
        components=row.get("components", {}),
        assumptions=row.get("assumptions", {}),
        tension_points=row.get("tension_points", []),
        recommended_action=row["recommended_action"],
        player=row["player"],
        ctx=row["ctx"],
        created_at=row.get("created_at"),
        summary_note=row.get("summary_note"),
        strengths=row.get("strengths"),
        concerns=row.get("concerns"),
        mode=row.get("mode"),
    )


@app.delete("/evaluations/{evaluation_id}", response_model=DeleteOut)
def delete_evaluation(evaluation_id: str, gm: AuthedGM = Depends(get_current_gm)):
    check_url = (
        f"{SUPABASE_URL}/rest/v1/gm_evaluations"
        f"?id=eq.{evaluation_id}"
        f"&gm_id=eq.{gm['gm_id']}"
        f"&select=id"
    )

    with httpx.Client(timeout=15) as client:
        check = _perform_supabase_request(
            "evaluation ownership check",
            lambda: client.get(check_url, headers=_sb_headers(gm["token"])),
        )
        _raise_for_supabase_error("evaluation ownership check", check)
        rows = check.json()

        if not rows:
            raise HTTPException(status_code=404, detail="Evaluation not found")

        delete_url = (
            f"{SUPABASE_URL}/rest/v1/gm_evaluations"
            f"?id=eq.{evaluation_id}"
            f"&gm_id=eq.{gm['gm_id']}"
        )
        delete_headers = _sb_headers(gm["token"]) | {"Prefer": "return=representation"}
        r = _perform_supabase_request(
            "evaluation delete",
            lambda: client.delete(delete_url, headers=delete_headers),
        )
        _raise_for_supabase_error("evaluation delete", r)

        deleted_rows = r.json() if r.text else []
        if not deleted_rows:
            raise HTTPException(status_code=404, detail="Evaluation not deleted")

    return DeleteOut(ok=True, deleted_id=evaluation_id)
