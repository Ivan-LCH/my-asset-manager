import uuid
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.models import (
    Asset, AssetHistory,
    RealEstateDetail, StockDetail, PensionDetail, SavingsDetail,
)

# ──────────────────────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────────────────────
TYPE_LABELS = {
    "REAL_ESTATE": "🏠 부동산",
    "STOCK":       "📈 주식",
    "PENSION":     "🛡️ 연금",
    "SAVINGS":     "💰 예적금/현금",
    "PHYSICAL":    "💎 실물자산",
    "ETC":         "🎸 기타",
}

def _now() -> str:
    return datetime.now().isoformat()

def _asset_to_dict(asset: Asset) -> dict:
    """Asset ORM → dict (이력 + 상세 포함)"""
    d = {
        "id":                asset.id,
        "type":              asset.type,
        "name":              asset.name,
        "current_value":     asset.current_value,
        "acquisition_date":  asset.acquisition_date,
        "acquisition_price": asset.acquisition_price,
        "disposal_date":     asset.disposal_date,
        "disposal_price":    asset.disposal_price,
        "quantity":          asset.quantity,
        "created_at":        asset.created_at,
        "updated_at":        asset.updated_at,
        "history": [
            {"date": h.date, "value": h.value, "price": h.price, "quantity": h.quantity}
            for h in sorted(asset.history, key=lambda x: x.date)
        ],
        "detail": _detail_to_dict(asset),
    }
    return d

def _detail_to_dict(asset: Asset) -> Optional[dict]:
    """유형별 상세 ORM → dict"""
    if asset.type == "REAL_ESTATE" and asset.real_estate:
        r = asset.real_estate
        return {
            "is_owned":       bool(r.is_owned),
            "has_tenant":     bool(r.has_tenant),
            "tenant_deposit": r.tenant_deposit,
            "address":        r.address,
            "loan_amount":    r.loan_amount,
        }
    if asset.type == "STOCK" and asset.stock:
        s = asset.stock
        return {
            "account_name":       s.account_name,
            "currency":           s.currency,
            "is_pension_like":    bool(s.is_pension_like),
            "pension_start_year": s.pension_start_year,
            "pension_monthly":    s.pension_monthly,
            "ticker":             s.ticker,
        }
    if asset.type == "PENSION" and asset.pension:
        p = asset.pension
        return {
            "pension_type":            p.pension_type,
            "expected_start_year":     p.expected_start_year,
            "expected_end_year":       p.expected_end_year,
            "expected_monthly_payout": p.expected_monthly_payout,
            "annual_growth_rate":      p.annual_growth_rate,
        }
    if asset.type == "SAVINGS" and asset.savings:
        sv = asset.savings
        return {
            "is_pension_like":    bool(sv.is_pension_like),
            "pension_start_year": sv.pension_start_year,
            "pension_monthly":    sv.pension_monthly,
        }
    return None

def _load_options():
    """모든 관계를 Eager Load하는 옵션"""
    return [
        selectinload(Asset.history),
        selectinload(Asset.real_estate),
        selectinload(Asset.stock),
        selectinload(Asset.pension),
        selectinload(Asset.savings),
    ]


# ──────────────────────────────────────────────────────────────
# CRUD - Assets
# ──────────────────────────────────────────────────────────────
async def get_all_assets(db: AsyncSession, asset_type: Optional[str] = None) -> list[dict]:
    q = select(Asset).options(*_load_options())
    if asset_type:
        q = q.where(Asset.type == asset_type)
    result = await db.execute(q)
    return [_asset_to_dict(a) for a in result.scalars().all()]


async def get_asset_by_id(db: AsyncSession, asset_id: str) -> Optional[dict]:
    q = select(Asset).options(*_load_options()).where(Asset.id == asset_id)
    result = await db.execute(q)
    asset = result.scalar_one_or_none()
    return _asset_to_dict(asset) if asset else None


async def create_asset(db: AsyncSession, data: dict) -> str:
    asset_id = data.get("id") or str(uuid.uuid4())
    now = _now()

    asset = Asset(
        id                = asset_id,
        type              = data["type"],
        name              = data["name"],
        current_value     = data.get("current_value", 0),
        acquisition_date  = data.get("acquisition_date"),
        acquisition_price = data.get("acquisition_price", 0),
        disposal_date     = data.get("disposal_date"),
        disposal_price    = data.get("disposal_price", 0),
        quantity          = data.get("quantity", 0),
        created_at        = now,
        updated_at        = now,
    )
    db.add(asset)
    await db.flush()  # PK 생성

    # 유형별 상세 저장
    _add_detail(db, asset_id, data)

    # 초기 이력 저장
    if "initial_history" in data and data["initial_history"]:
        h = data["initial_history"]
        db.add(AssetHistory(
            asset_id = asset_id,
            date     = h.get("date", data.get("acquisition_date", "")),
            value    = h.get("value"),
            price    = h.get("price"),
            quantity = h.get("quantity"),
        ))

    return asset_id


async def update_asset(db: AsyncSession, asset_id: str, data: dict):
    q = select(Asset).where(Asset.id == asset_id)
    result = await db.execute(q)
    asset = result.scalar_one_or_none()
    if not asset:
        return

    asset.name              = data.get("name", asset.name)
    asset.current_value     = data.get("current_value", asset.current_value)
    asset.acquisition_date  = data.get("acquisition_date", asset.acquisition_date)
    asset.acquisition_price = data.get("acquisition_price", asset.acquisition_price)
    asset.disposal_date     = data.get("disposal_date", asset.disposal_date)
    asset.disposal_price    = data.get("disposal_price", asset.disposal_price)
    asset.quantity          = data.get("quantity", asset.quantity)
    asset.updated_at        = _now()

    # 상세 테이블: 삭제 후 재삽입
    await _delete_detail(db, asset_id, asset.type)
    _add_detail(db, asset_id, data)


async def delete_asset(db: AsyncSession, asset_id: str):
    await db.execute(delete(Asset).where(Asset.id == asset_id))


def _add_detail(db: AsyncSession, asset_id: str, data: dict):
    """유형별 상세 레코드 추가"""
    a_type = data.get("type")
    detail = data.get("detail", {}) or {}

    if a_type == "REAL_ESTATE":
        db.add(RealEstateDetail(
            asset_id       = asset_id,
            is_owned       = 1 if detail.get("is_owned", True) else 0,
            has_tenant     = 1 if detail.get("has_tenant") else 0,
            tenant_deposit = detail.get("tenant_deposit", 0),
            address        = detail.get("address"),
            loan_amount    = detail.get("loan_amount", 0),
        ))
    elif a_type == "STOCK":
        db.add(StockDetail(
            asset_id           = asset_id,
            account_name       = detail.get("account_name"),
            currency           = detail.get("currency", "KRW"),
            is_pension_like    = 1 if detail.get("is_pension_like") else 0,
            pension_start_year = detail.get("pension_start_year"),
            pension_monthly    = detail.get("pension_monthly"),
            ticker             = detail.get("ticker"),
        ))
    elif a_type == "PENSION":
        db.add(PensionDetail(
            asset_id                = asset_id,
            pension_type            = detail.get("pension_type"),
            expected_start_year     = detail.get("expected_start_year"),
            expected_end_year       = detail.get("expected_end_year"),
            expected_monthly_payout = detail.get("expected_monthly_payout", 0),
            annual_growth_rate      = detail.get("annual_growth_rate", 0),
        ))
    elif a_type == "SAVINGS":
        db.add(SavingsDetail(
            asset_id           = asset_id,
            is_pension_like    = 1 if detail.get("is_pension_like") else 0,
            pension_start_year = detail.get("pension_start_year"),
            pension_monthly    = detail.get("pension_monthly"),
        ))


async def _delete_detail(db: AsyncSession, asset_id: str, a_type: str):
    """유형별 상세 삭제"""
    table_map = {
        "REAL_ESTATE": RealEstateDetail,
        "STOCK":       StockDetail,
        "PENSION":     PensionDetail,
        "SAVINGS":     SavingsDetail,
    }
    if a_type in table_map:
        model = table_map[a_type]
        await db.execute(delete(model).where(model.asset_id == asset_id))


# ──────────────────────────────────────────────────────────────
# CRUD - History
# ──────────────────────────────────────────────────────────────
async def get_history(db: AsyncSession, asset_id: str) -> list[dict]:
    q = select(AssetHistory).where(AssetHistory.asset_id == asset_id).order_by(AssetHistory.date)
    result = await db.execute(q)
    return [{"date": h.date, "value": h.value, "price": h.price, "quantity": h.quantity}
            for h in result.scalars().all()]


async def add_history(db: AsyncSession, asset_id: str, data: dict):
    db.add(AssetHistory(
        asset_id = asset_id,
        date     = data["date"],
        value    = data.get("value"),
        price    = data.get("price"),
        quantity = data.get("quantity"),
    ))


async def update_history(db: AsyncSession, asset_id: str, date: str, data: dict, exchange_rate: float = 1.0) -> int:
    """
    이력 수정. 수량이 변경되면 해당 날짜 이후 모든 이력에 수량 전파.
    반환값: 전파된 행 수
    """
    q = select(AssetHistory).where(
        AssetHistory.asset_id == asset_id,
        AssetHistory.date == date,
    )
    result = await db.execute(q)
    hist = result.scalar_one_or_none()

    new_price    = data.get("price")
    new_quantity = data.get("quantity")
    new_value    = data.get("value")

    # value가 없으면 price * quantity * rate로 자동 계산
    if new_value is None and new_price is not None and new_quantity is not None:
        new_value = new_price * new_quantity * exchange_rate

    propagated_count = 0

    if hist is None:
        # 신규 추가
        db.add(AssetHistory(asset_id=asset_id, date=date,
                            value=new_value, price=new_price, quantity=new_quantity))
    else:
        old_qty = hist.quantity
        hist.price    = new_price    if new_price    is not None else hist.price
        hist.quantity = new_quantity if new_quantity is not None else hist.quantity
        hist.value    = new_value    if new_value    is not None else hist.value

        # 수량 변경 시 이후 이력 전파
        if new_quantity is not None and old_qty != new_quantity:
            future_q = select(AssetHistory).where(
                AssetHistory.asset_id == asset_id,
                AssetHistory.date > date,
            ).order_by(AssetHistory.date)
            future_result = await db.execute(future_q)
            for fh in future_result.scalars().all():
                fh.quantity = new_quantity
                if fh.price is not None:
                    fh.value = fh.price * new_quantity * exchange_rate
                propagated_count += 1

    # assets 테이블 current_value / quantity 동기화 (최신 이력 기준)
    await _sync_asset_value(db, asset_id)

    return propagated_count


async def delete_history(db: AsyncSession, asset_id: str, date: str):
    await db.execute(
        delete(AssetHistory).where(
            AssetHistory.asset_id == asset_id,
            AssetHistory.date == date,
        )
    )
    await _sync_asset_value(db, asset_id)


async def _sync_asset_value(db: AsyncSession, asset_id: str):
    """최신 이력을 기준으로 assets.current_value, quantity 동기화"""
    q = select(AssetHistory).where(
        AssetHistory.asset_id == asset_id
    ).order_by(AssetHistory.date.desc()).limit(1)
    result = await db.execute(q)
    latest = result.scalar_one_or_none()
    if not latest:
        return

    asset_q = select(Asset).where(Asset.id == asset_id)
    asset_result = await db.execute(asset_q)
    asset = asset_result.scalar_one_or_none()
    if asset:
        asset.current_value = latest.value or 0
        asset.quantity      = latest.quantity or asset.quantity
        asset.updated_at    = _now()


# ──────────────────────────────────────────────────────────────
# CRUD - Settings
# ──────────────────────────────────────────────────────────────
from sqlalchemy import text

async def get_settings(db: AsyncSession) -> dict:
    result = await db.execute(text("SELECT key, value FROM settings"))
    rows = result.fetchall()
    out = {}
    for key, val in rows:
        try:
            out[key] = float(val) if "." in val else int(val)
        except (ValueError, TypeError):
            out[key] = val
    return out


async def save_settings(db: AsyncSession, data: dict):
    for key, val in data.items():
        await db.execute(
            text("INSERT INTO settings (key, value) VALUES (:k, :v) "
                 "ON CONFLICT(key) DO UPDATE SET value = :v"),
            {"k": key, "v": str(val)},
        )


# ──────────────────────────────────────────────────────────────
# 차트 집계 (Forward Fill)
# ──────────────────────────────────────────────────────────────
def generate_chart_data(
    assets: list[dict],
    period: str = "all",
    group_by: str = "type",
) -> list[dict]:
    """
    이력 데이터를 Forward Fill하여 날짜별 자산 가치 집계.
    부동산은 (current_value - loan - deposit)로 순자산 기준 집계.
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    period_days = {"10y": 3650, "3y": 1095, "1y": 365, "3m": 90, "1m": 30}
    if period in period_days:
        start = today - timedelta(days=period_days[period])
    else:
        start = datetime(2015, 1, 1)

    all_records = []
    for asset in assets:
        # 매각 자산도 포함 (매각일 이후 0으로 처리됨)
        records = _asset_to_records(asset)
        all_records.extend(records)

    if not all_records:
        return []

    df = pd.DataFrame(all_records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates(subset=["asset_id", "date"], keep="last")

    # 피벗 → 날짜 범위 reindex → forward fill
    df_pivot = df.pivot(index="date", columns="asset_id", values="value")
    full_idx  = pd.date_range(start=start, end=today, freq="D")
    df_pivot  = df_pivot.reindex(full_idx).ffill().fillna(0)

    # 언피벗
    df_melt = (
        df_pivot.reset_index()
        .melt(id_vars="index", var_name="asset_id", value_name="value")
        .rename(columns={"index": "date"})
    )

    # 메타데이터 매핑
    meta = {a["id"]: a for a in assets}
    df_melt["label"] = df_melt["asset_id"].map(
        lambda aid: _get_label(meta.get(aid, {}), group_by)
    )
    df_melt["date"] = df_melt["date"].dt.strftime("%Y-%m-%d")

    result = (
        df_melt.groupby(["date", "label"])["value"]
        .sum()
        .reset_index()
        .rename(columns={"label": "label"})
    )
    return result.to_dict(orient="records")


def _asset_to_records(asset: dict) -> list[dict]:
    """
    자산 하나의 이력 포인트를 레코드 리스트로 변환.
    부동산은 부채(대출+보증금) 차감.
    """
    a_id  = asset["id"]
    a_type = asset["type"]
    history = asset.get("history", [])

    # 부동산 부채
    liab = 0.0
    if a_type == "REAL_ESTATE" and asset.get("detail"):
        d = asset["detail"]
        liab = (d.get("loan_amount") or 0) + (d.get("tenant_deposit") or 0)

    records = []

    # (1) 취득일 초기값
    acq_date  = (asset.get("acquisition_date") or "2023-01-01")[:10]
    acq_price = asset.get("acquisition_price") or 0
    qty       = asset.get("quantity") or 0
    init_val  = (acq_price * qty) if a_type in ("STOCK", "PHYSICAL") and qty else acq_price
    records.append({"asset_id": a_id, "date": acq_date, "value": max(0, init_val - liab)})

    # (2) 이력
    for h in history:
        if not h.get("date"):
            continue
        if h.get("value") is not None:
            val = float(h["value"])
        elif h.get("price") is not None and h.get("quantity") is not None:
            val = float(h["price"]) * float(h["quantity"])
        else:
            continue
        records.append({"asset_id": a_id, "date": h["date"][:10], "value": max(0, val - liab)})

    # (3) 현재값 or 매각값
    disp_date  = asset.get("disposal_date")
    disp_price = asset.get("disposal_price") or 0
    if disp_date:
        records.append({"asset_id": a_id, "date": disp_date[:10], "value": float(disp_price)})
        # (4) 매각 이후 0
        after = (datetime.strptime(disp_date[:10], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        records.append({"asset_id": a_id, "date": after, "value": 0.0})
    else:
        cur_val = asset.get("current_value") or 0
        records.append({
            "asset_id": a_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "value": max(0, float(cur_val) - liab),
        })

    return records


def _get_label(asset: dict, group_by: str) -> str:
    if group_by == "name":
        return asset.get("name", "")
    if group_by == "account":
        detail = asset.get("detail") or {}
        return detail.get("account_name") or asset.get("name", "기타")
    # default: type
    return TYPE_LABELS.get(asset.get("type", ""), asset.get("type", ""))
