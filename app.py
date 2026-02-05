# -----------------------------------------------------------------------------------------------------
# Import
# -----------------------------------------------------------------------------------------------------
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import uuid
import time
from datetime import datetime, timedelta
from utils import load_data, save_data

# -----------------------------------------------------------------------------------------------------
# [설정] 페이지 및 스타일
# -----------------------------------------------------------------------------------------------------
st.set_page_config(page_title="My Asset Manager", page_icon="💰", layout="wide")

PASTEL_COLORS = px.colors.qualitative.Pastel 

COLOR_MAP = {
    'REAL_ESTATE' : PASTEL_COLORS[2], 
    'STOCK'       : PASTEL_COLORS[0],       
    'PENSION'     : PASTEL_COLORS[4],     
    'SAVINGS'     : PASTEL_COLORS[3],     
    'PHYSICAL'    : PASTEL_COLORS[5],    
    'ETC'         : PASTEL_COLORS[1]          
}

TYPE_LABEL_MAP = {
    'REAL_ESTATE' : '🏠 부동산',
    'STOCK'       : '📈 주식',
    'PENSION'     : '🛡️ 연금',
    'SAVINGS'     : '💰 예적금/현금',
    'PHYSICAL'    : '💎 실물자산',
    'ETC'         : '🎸 기타'
}

def load_css():
    st.markdown("""
    <style>
    div.metric-card {
        background-color: #F8F9FA;
        border: 1px solid #E9ECEF;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
        margin-bottom: 10px;
    }
    div.metric-label { font-size: 13px; color: #6C757D; margin-bottom: 4px; }
    div.metric-value { font-size: 20px; font-weight: 700; color: #212529; }
    
    .info-label { font-size: 12px; color: #888; font-weight: 600; }
    .info-value { font-size: 14px; color: #333; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; margin-right: 5px; }
    .badge-blue { background-color: #e0f2fe; color: #0369a1; }
    .badge-green { background-color: #dcfce7; color: #15803d; }
    .badge-gray { background-color: #f1f5f9; color: #475569; }
    .badge-red { background-color: #fee2e2; color: #b91c1c; }
    .badge-orange { background-color: #fff7ed; color: #c2410c; }
    </style>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------------------------------
# [헬퍼 함수]
# -----------------------------------------------------------------------------------------------------
def safe_float(val):
    try:
        if val is None or str(val).strip() == "": return 0.0
        return float(str(val).replace(",", ""))
    except:
        return 0.0

def safe_int(val):
    try:
        if val is None or str(val).strip() == "": return 0
        return int(float(str(val).replace(",", "")))
    except:
        return 0

def format_money(val):
    return f"₩{val:,.0f}"


# -----------------------------------------------------------------------------------------------------
# [추가] 카테고리별 요약 카드 표시 함수
# -----------------------------------------------------------------------------------------------------
def display_category_summary(asset_name, assets_subset):
    if not assets_subset:
        return

    cat_total_asset = 0
    cat_total_liab = 0

    for a in assets_subset:
        # 매각된 자산은 합계에서 제외 (대시보드 로직과 동일)
        if a.get('disposalDate'): continue
        
        val = safe_float(a.get('currentValue'))
        cat_total_asset += val
        
        # 부동산일 경우 부채(대출+보증금) 계산
        if a['type'] == 'REAL_ESTATE':
            cat_total_liab += safe_float(a.get('loanAmount', 0))
            cat_total_liab += safe_float(a.get('tenantDeposit', 0))
            
    cat_net_worth = cat_total_asset - cat_total_liab
    
    # 화면 표시
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(render_kpi_card_html(f"💰 {asset_name} 자산"  , format_money(cat_total_asset)), unsafe_allow_html=True)
    with c2: st.markdown(render_kpi_card_html(f"📉 {asset_name} 부채"  , format_money(cat_total_liab ), "#e03131"), unsafe_allow_html=True)
    with c3: st.markdown(render_kpi_card_html(f"💎 {asset_name} 순자산", format_money(cat_net_worth  ), "#1c7ed6"), unsafe_allow_html=True)
    
    st.markdown("---")


def render_kpi_card_html(label, value, color="#212529", sub=""):
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value" style="color: {color};">{value}</div>
        <div style="font-size:11px; color:#adb5bd;">{sub}</div>
    </div>
    """

def parse_asset_details(asset):
    """자산 데이터 파싱 (SQLite에서 이미 변환된 데이터를 추가 처리)"""
    a_type = asset.get('type')
    
    # 숫자 필드 안전 변환
    asset['currentValue'             ] = safe_float(asset.get('currentValue'))
    asset['acquisitionPrice'         ] = safe_float(asset.get('acquisitionPrice'))
    asset['quantity'                 ] = safe_float(asset.get('quantity'))
    asset['disposalPrice'            ] = safe_float(asset.get('disposalPrice'))
    
    # 날짜 필드 기본값
    if not asset.get('acquisitionDate'): asset['acquisitionDate'] = ""
    if not asset.get('disposalDate'   ): asset['disposalDate'   ] = ""
    
    # 부동산: 숫자 필드 변환
    if a_type == 'REAL_ESTATE':
        asset['tenantDeposit'        ] = safe_float(asset.get('tenantDeposit'))
        asset['loanAmount'           ] = safe_float(asset.get('loanAmount'))
    
    # 주식: currentValue 자동 계산
    elif a_type == 'STOCK':
        if 'account_name' in asset and not asset.get('accountName'):
            asset['accountName'] = asset['account_name']
            
        if asset['currentValue'] == 0 and asset['quantity'] > 0:    
            asset['currentValue'     ] = asset['quantity'] * asset['acquisitionPrice']

    # 연금: 숫자 필드 변환
    elif a_type == 'PENSION':
        asset['expectedStartYear'    ] = safe_int  (asset.get('expectedStartYear'))
        asset['expectedMonthlyPayout'] = safe_float(asset.get('expectedMonthlyPayout'))
        asset['expectedEndYear'      ] = safe_int  (asset.get('expectedEndYear'))
        asset['annualGrowthRate'     ] = safe_float(asset.get('annualGrowthRate', 0))

    return asset

# -----------------------------------------------------------------------------------------------------
# [핵심 로직] 주식 계좌 잔고 보정
# -----------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------
# [핵심 로직] 차트 데이터 생성 (기간 설정 + 실물자산 단가 적용) - CACHED
# -----------------------------------------------------------------------------------------------------
# 캐시 키 생성을 위한 헬퍼: 자산 ID 목록을 튜플로 변환
def _get_asset_cache_key(assets):
    """자산 리스트에서 캐시 키 생성 (ID + 마지막 업데이트 시간)"""
    if not assets:
        return ()
    # 자산 ID와 currentValue를 조합하여 해시 키 생성 (값이 바뀌면 캐시 무효화)
    return tuple(sorted([(a.get('id'), a.get('currentValue')) for a in assets]))


@st.cache_data(ttl=300, show_spinner="차트 데이터 생성 중...")  # 5분 캐시
def _generate_history_df_cached(asset_cache_key, type_filter, assets_json):
    """캐시되는 실제 구현 (JSON에서 자산 리스트 복원)"""
    import json as json_module
    assets = json_module.loads(assets_json)
    return _generate_history_df_impl(assets, type_filter)


def generate_history_df(assets, type_filter=None):
    """캐시 래퍼: 자산 리스트를 직렬화하여 캐시된 함수 호출"""
    if not assets:
        return pd.DataFrame()
    cache_key   = _get_asset_cache_key(assets)
    assets_json = json.dumps(assets, default=str)  # 날짜 등을 문자열로 변환
    return _generate_history_df_cached(cache_key, type_filter, assets_json)


def _generate_history_df_impl(assets, type_filter=None):
    """실제 차트 데이터 생성 로직 (캐시에서 호출됨)"""
    if not assets: return pd.DataFrame()
    
    # 1. 필터링 및 데이터 준비
    target_assets = [a for a in assets if (type_filter is None or a['type'] == type_filter)]
    if not target_assets: return pd.DataFrame()

    # [Fix] 시간 성분 제거 (Mismatch 방지)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    is_long_term = (type_filter is None) or (type_filter == 'REAL_ESTATE')
    period_years = 10 if is_long_term else 3
    start_limit  = today - timedelta(days=365 * period_years)
    
    # 모든 자산의 history를 하나의 리스트로 평탄화 (Flatten)
    all_records = []
    
    for asset in target_assets:
        a_id   = asset['id']
        a_name = asset['name']
        a_type = asset['type']
        a_acc  = asset.get('accountName', '기타')
        
        # (1) 초기값 (취득일)
        acq_date_str     = str(asset.get('acquisitionDate', '2023-01-01'))[:10]
        try: acq_date    = pd.to_datetime(acq_date_str)
        except: acq_date = pd.to_datetime('2023-01-01')
        
        acq_price        = safe_float(asset.get('acquisitionPrice', 0))
        qty              = safe_float(asset.get('quantity', 0))
        is_qty_based     = a_type in ['STOCK', 'PHYSICAL']
        
        if is_qty_based and qty > 0:
            init_val = acq_price * qty
        else:
            init_val = acq_price
            
        all_records.append({
            'asset_id'       : a_id, 
            'date'           : acq_date, 
            'value'          : init_val, 
            'name'           : a_name, 
            'type'           : a_type, 
            'account'        : a_acc, 
            'is_real_estate' : (a_type=='REAL_ESTATE'),
            'loan'           : safe_float(asset.get('loanAmount', 0)) + safe_float(asset.get('tenantDeposit', 0))
        })
        
        # (2) 이력 데이터
        hist_raw = asset.get('history', [])
        # JSON string 처리 (간혹 str로 들어오는 경우 방지)
        if isinstance(hist_raw, str):
            try   : hist_raw = json.loads(hist_raw)
            except: hist_raw = []
            
        for h in hist_raw:
            d_str = h.get('date')
            if not d_str: continue
            
            val = 0
            if h.get('value') is not None:
                val = safe_float(h['value'])
            elif h.get('price') is not None and h.get('quantity') is not None:
                val = safe_float(h['price']) * safe_float(h['quantity'])
            
            all_records.append({
                'asset_id'       : a_id, 
                'date'           : pd.to_datetime(d_str), 
                'value'          : val,
                'name'           : a_name, 
                'type'           : a_type, 
                'account'        : a_acc, 
                'is_real_estate' : (a_type=='REAL_ESTATE'),
                'loan'           : safe_float(asset.get('loanAmount', 0)) + safe_float(asset.get('tenantDeposit', 0))
            })
            
        # (3) 현재가 (또는 매각가)
        disp_date_str = asset.get('disposalDate')
        if disp_date_str:
            last_date = pd.to_datetime(disp_date_str)
            last_val  = safe_float(asset.get('disposalPrice', 0))
        else:
            last_date = pd.to_datetime(today.date())
            last_val  = safe_float(asset.get('currentValue', 0))
            
        all_records.append({
            'asset_id'       : a_id, 
            'date'           : last_date, 
            'value'          : last_val,
            'name'           : a_name, 
            'type'           : a_type, 
            'account'        : a_acc, 
            'is_real_estate' : (a_type=='REAL_ESTATE'),
            'loan'           : safe_float(asset.get('loanAmount', 0)) + safe_float(asset.get('tenantDeposit', 0))
        })
        
        # (4) 매각 이후 0 처리 (매각일 다음날부터)
        if disp_date_str:
            zero_date = last_date + timedelta(days=1)
            all_records.append({
                'asset_id'       : a_id, 
                'date'           : zero_date, 
                'value'          : 0,
                'name'           : a_name, 
                'type'           : a_type, 
                'account'        : a_acc, 
                'is_real_estate' : (a_type=='REAL_ESTATE'),
                'loan'           : 0 # 매각 후 부채도 0 가정
            })

    if not all_records: return pd.DataFrame()


    # 2. DataFrame 변환 및 Resample (Vectorization)
    df_raw   = pd.DataFrame(all_records)
    
    # asset_id 별로 그룹화하여 일별 리샘플링
    # drop_duplicates: 같은 날짜에 여러 기록이 있으면 마지막 것 사용
    df_raw   = df_raw.sort_values('date').drop_duplicates(subset=['asset_id', 'date'], keep='last')
    
    df_pivot = df_raw.pivot(index='date', columns='asset_id', values='value')
    
    # 날짜 범위 생성 (Start ~ Today)
    full_idx = pd.date_range(start=start_limit, end=today, freq='D')
    
    # Reindex & Forward Fill (이전 값 유지) → Fillna(0) (시작 전은 0)
    df_pivot = df_pivot.reindex(full_idx).ffill().fillna(0)
    
    # 메타데이터 매핑용 (asset_id -> info)
    meta_cols = ['name', 'type', 'account', 'is_real_estate', 'loan']
    # 각 자산의 마지막 메타데이터 가져오기 (사실 변하지 않음)
    meta_map = df_raw.drop_duplicates('asset_id')[['asset_id'] + meta_cols].set_index('asset_id')
    
    # Unpivot (Melt) to restore 'long' format for Plotly
    df_melt = df_pivot.reset_index().melt(id_vars='index', var_name='asset_id', value_name='value')
    df_melt.rename(columns={'index': 'date'}, inplace=True)
    
    # 메타데이터 병합
    df_final = df_melt.merge(meta_map, on='asset_id', how='left')
    
    # 부동산 부채 차감
    # (간단화를 위해 부채는 상수라고 가정하고 처리했지만, 여기선 그대로 반영)
    # 벡터 연산: 부동산이면 value - loan, 음수면 0
    mask_re = df_final['is_real_estate'] == True
    df_final.loc[mask_re, 'value'] = df_final.loc[mask_re, 'value'] - df_final.loc[mask_re, 'loan']
    df_final.loc[df_final['value'] < 0, 'value'] = 0
    
    # 날짜 포맷 string으로 변환
    df_final['date'] = df_final['date'].dt.strftime("%Y-%m-%d")
    
    return df_final


# -----------------------------------------------------------------------------------------------------
# [통합] 자산 상세 렌더러
# -----------------------------------------------------------------------------------------------------
def render_asset_detail(asset, precalc_df=None):
    a_type       = asset['type']
    # [수정] 수량 기반 자산 여부 (주식 + 실물)
    is_qty_based = a_type in ['STOCK', 'PHYSICAL']
    
    val          = safe_float(asset['currentValue'])
    acq_price    = safe_float(asset.get('acquisitionPrice', 0))
    acq_date     = asset.get('acquisitionDate', '-')
    
    disp_date    = asset.get('disposalDate')
    disp_price   = safe_float(asset.get('disposalPrice', 0))
    is_sold      = True if disp_date else False
    display_val  = disp_price if is_sold else val
    

    # [1] 기본 정보
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if   a_type == 'REAL_ESTATE': st.markdown(f"<div class='info-label'>위치</div><div class='info-value'>{asset.get('address'    , '-')}</div>", unsafe_allow_html=True)
        elif a_type == 'STOCK':       st.markdown(f"<div class='info-label'>계좌</div><div class='info-value'>{asset.get('accountName', '-')}</div>", unsafe_allow_html=True)
        elif a_type == 'PENSION':     st.markdown(f"<div class='info-label'>유형</div><div class='info-value'>{TYPE_LABEL_MAP.get(a_type, a_type)}</div>", unsafe_allow_html=True)
        else:                         st.markdown(f"<div class='info-label'>유형</div><div class='info-value'>{TYPE_LABEL_MAP.get(a_type, a_type)}</div>", unsafe_allow_html=True)
    
    with col2: st.markdown(f"<div class='info-label'>취득일</div><div class='info-value'>{acq_date}</div>", unsafe_allow_html=True)
    
    with col3:
        if is_qty_based:
            invested = acq_price * safe_float(asset.get('quantity', 0))
            st.markdown(f"<div class='info-label'>투자원금</div><div class='info-value'>{format_money(invested)}</div>", unsafe_allow_html=True)
        else: 
            st.markdown(f"<div class='info-label'>취득가</div><div class='info-value'>{format_money(acq_price)}</div>", unsafe_allow_html=True)
    
    with col4:
        if is_sold: 
            st.markdown(f"<div class='info-label'>매각일</div><div class='info-value' style='color:#e03131;'>{disp_date}</div>", unsafe_allow_html=True)
        else: 
            st.markdown(f"<div class='info-label'>상태</div><div class='info-value'>보유중</div>", unsafe_allow_html=True)

    if a_type == 'REAL_ESTATE':
        st.markdown("")
        c1, c2, c3, c4 = st.columns(4)
        with c1: 
            st.markdown(f"<div class='info-label'>대출금</div><div class='info-value'>{format_money(safe_float(asset.get('loanAmount',0)))}</div>", unsafe_allow_html=True)
        with c2: 
            st.markdown(f"<div class='info-label'>보증금</div><div class='info-value'>{format_money(safe_float(asset.get('tenantDeposit',0)))}</div>", unsafe_allow_html=True)
        with c3: 
            badges = []
            if asset.get('isOwned')  : badges.append('<span class="badge badge-blue">자가</span>')
            else                     : badges.append('<span class="badge badge-gray">임대</span>')
            if asset.get('hasTenant'): badges.append('<span class="badge badge-green">세입자O</span>')

            st.markdown("".join(badges), unsafe_allow_html=True)
    

    if a_type == 'PENSION':
        st.markdown("")
        st.markdown(f"<div class='info-label'>매년 증가율</div><div class='info-value' style='color:#228be6;'>{asset.get('annualGrowthRate', 0)}%</div>", unsafe_allow_html=True)

    st.markdown("---")

    # [2] KPI
    if a_type == 'REAL_ESTATE':
        liab   = safe_float(asset.get('loanAmount', 0)) + safe_float(asset.get('tenantDeposit', 0))
        equity = display_val - liab
        k1, v1 = "현재 시세" if not is_sold else "매각 금액", format_money(display_val)
        k2, v2 = "부채 총계", format_money(liab)
        k3, v3 = "순자산 (Equity)", format_money(equity)

    elif is_qty_based:
        qty      = safe_float(asset.get('quantity', 0))
        invested = acq_price * qty
        pl       = display_val - invested
        roi      = (pl / invested * 100) if invested > 0 else 0
        k1, v1   = "평가 금액", format_money(display_val)
        k2, v2   = "평가 손익", f"{format_money(pl)} ({roi:+.1f}%)"
        k3, v3   = "보유 수량", f"{qty:,.0f}"
    else:
        k1, v1 = "현재 가치", format_money(display_val)
        k2, v2 = "-", "-"
        k3, v3 = "변동액", format_money(display_val - acq_price)

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(render_kpi_card_html(k1, v1), unsafe_allow_html=True)
    with c2: st.markdown(render_kpi_card_html(k2, v2, "#e03131" if a_type=='REAL_ESTATE' else "#212529"), unsafe_allow_html=True)
    with c3: st.markdown(render_kpi_card_html(k3, v3, "#1c7ed6"), unsafe_allow_html=True)

    st.markdown("---")

    # [3] 차트
    st.markdown("##### 📉 가치 변동 추이")
    
    # [수정] Batch Processing 지원
    if precalc_df is not None:
        df_chart = precalc_df[precalc_df['asset_id'] == asset['id']].copy()
    else:
        # Fallback (단건 계산)
        df_chart = generate_history_df([asset], type_filter=a_type)
    
    if not df_chart.empty:
        df_chart['value_man'] = df_chart['value'] / 10000
        fig = px.area(
            df_chart, 
            x                       = 'date', 
            y                       = 'value_man', 
            color_discrete_sequence = [COLOR_MAP.get(a_type, '#888')],
            labels                  = {'value_man': '가치(만원)'}
        )
        
        # [수정] 차트 개선 (Hover Unified + X축 촘촘하게)
        fig.update_layout(
            height                  = 250, 
            margin                  = dict(t=10, b=0, l=0, r=0), 
            xaxis_title             = None, 
            yaxis_title             = None,
            hovermode               = "x unified",
            xaxis                   = dict(nticks=20, tickformat="%y.%m.%d")
        )
        
        # [수정] 주식의 경우, 변동성을 잘 보여주기 위해 Y축 스케일 조정 (0부터 시작하지 않음)
        if a_type == 'STOCK':
             y_vals = df_chart['value_man']
             y_min  = y_vals.min()
             y_max  = y_vals.max()
             gap    = (y_max - y_min) * 0.1
             if gap == 0: gap = y_max * 0.05
             
             # 0 미만으로 내려가지 않도록 하되, 0부터 시작하진 않음
             fig.update_layout(yaxis = dict(range=[max(0, y_min - gap), y_max + gap], tickformat=",.0f"))
             
        st.plotly_chart(fig, use_container_width=True, key=f"chart_{asset['id']}")
    else:
        st.info("데이터가 부족하여 차트를 표시할 수 없습니다.")

    st.markdown("---")

    # [4] 이력 관리 & 수정
    c_left, c_right = st.columns([2, 1])
    with c_left:
        st.markdown("##### 📝 이력 관리")
        
        hist_raw = asset.get('history', [])
        if isinstance(hist_raw, str):
            try   : hist_raw = json.loads(hist_raw)
            except: hist_raw = []
        
        data_list = []
        for h in hist_raw:
            row = {'date': h.get('date', '')}
            if is_qty_based:
                p = safe_float(h.get('price', 0))
                q = safe_float(h.get('quantity', 0))
                v = safe_float(h.get('value', 0))
                
                # [Fix] Legacy data support: if price/qty are 0 but value exists, assume qty=1
                if p == 0 and q == 0 and v > 0:
                    p = v
                    q = 1.0
                
                row['price']    = p
                row['quantity'] = q
            else:
                row['value'   ] = safe_float(h.get('value', 0))
            data_list.append(row)
            
        df_edit = pd.DataFrame(data_list)
        if df_edit.empty:
            df_edit = pd.DataFrame({'date': [datetime.now().strftime("%Y-%m-%d")], 'value': [0.0]}) if not is_qty_based else pd.DataFrame({'date': [datetime.now().strftime("%Y-%m-%d")], 'price': [0.0], 'quantity': [0.0]})
        else:
            # [수정] 날짜 역순 정렬 (최신 데이터가 위로)
            df_edit = df_edit.sort_values('date', ascending=False).reset_index(drop=True)
        
        # [수정] 행 선택 가능하도록 설정
        event = st.dataframe(
            df_edit, 
            on_select           = "rerun", 
            selection_mode      = "single-row", 
            use_container_width = True, 
            hide_index          = True,
            key                 = f"hist_df_{asset['id']}"
        )
        
        selected_row = None
        if event.selection.rows:
            sel_idx      = event.selection.rows[0]
            selected_row = df_edit.iloc[sel_idx]
            # [Fix] 행 선택 시 현재 자산/계좌 상태 유지
            st.session_state['expanded_asset_id'] = asset['id']
            st.session_state['expanded_account' ] = asset.get('accountName')

    with c_right:
        if selected_row is not None:
            # [수정 모드]
            st.markdown("##### ✏️ 데이터 수정")
            st.info(f"선택된 날짜: {selected_row['date']}")
            
            with st.form(f"edit_h_{asset['id']}"):
                e_date = selected_row['date']
                if is_qty_based:
                    e_p = st.number_input(
                        "단가", 
                        value     = safe_float(selected_row.get('price')), 
                        min_value = 0.0
                    )
                    e_q = st.number_input(
                        "수량", 
                        value     = safe_float(selected_row.get('quantity')), 
                        min_value = 0.0
                    )
                    st.caption("ℹ️ 수량을 변경하면 해당 날짜 이후의 모든 데이터에도 변경된 수량이 적용됩니다.")
                else:
                    e_v = st.number_input(
                        "평가액", 
                        value     = safe_float(selected_row.get('value')), 
                        min_value = 0.0
                    )
                    e_p, e_q = 0, 0
                    
                if st.form_submit_button("수정 저장"):
                    st.session_state['expanded_asset_id'] = asset['id']
                    st.session_state['expanded_account' ] = asset.get('accountName')
                    
                    from database import update_history_and_future_quantities, get_connection
                    
                    if is_qty_based:
                        update_history_and_future_quantities(asset['id'], e_date, e_p, e_q)
                    else:
                        with get_connection() as conn:
                            conn.execute("UPDATE asset_history SET value = ? WHERE asset_id = ? AND date = ?", (e_v, asset['id'], e_date))
                    
                    st.success("수정되었습니다.")
                    # [UI Refresh] 데이터 다시 로드
                    st.cache_data.clear()
                    data, config              = load_data()
                    st.session_state.settings = config
                    st.session_state.assets   = [parse_asset_details(a) for a in data]
                    st.rerun()
            
            # [이력 삭제 버튼] - form 밖에서 처리
            st.markdown("---")
            if st.button("🗑️ 이 날짜 삭제", key=f"del_hist_{asset['id']}_{e_date}", type="secondary"):
                from database import get_connection
                with get_connection() as conn:
                    conn.execute("DELETE FROM asset_history WHERE asset_id = ? AND date = ?", (asset['id'], e_date))
                st.toast(f"{e_date} 데이터가 삭제되었습니다.")
                st.cache_data.clear()
                data, config              = load_data()
                st.session_state.settings = config
                st.session_state.assets   = [parse_asset_details(a) for a in data]
                st.rerun()
        
        else:
            # [신규 추가 모드]
            st.markdown("##### ➕ 신규 데이터")
            with st.form(f"add_h_{asset['id']}"):
                n_date = st.date_input("날짜", value=datetime.now())
                if is_qty_based:
                    n_p = st.number_input("단가", min_value=0.0)
                    n_q = st.number_input("수량", min_value=0.0, value=safe_float(asset.get('quantity')))
                else:
                    n_v = st.number_input("평가액", min_value=0.0, value=val)
                    
                if st.form_submit_button("추가"):
                    st.session_state['expanded_asset_id'] = asset['id']
                    st.session_state['expanded_account' ] = asset.get('accountName') 

                    d_str = n_date.strftime("%Y-%m-%d")
                    
                    # [Validation] 매각일 이후에는 이력 추가 불가
                    disp_date_str = asset.get('disposalDate', '')
                    if disp_date_str and d_str > disp_date_str:
                        st.error(f"⚠️ 매각일({disp_date_str}) 이후에는 이력을 추가할 수 없습니다.")
                    else:
                        from database import update_history_and_future_quantities, insert_history
                        
                        if is_qty_based:
                            update_history_and_future_quantities(asset['id'], d_str, n_p, n_q)
                        else:
                            insert_history(asset['id'], {"date": d_str, "value": n_v})
                        
                        st.success("추가됨")
                        # [UI Refresh] 데이터 다시 로드
                        st.cache_data.clear()
                        data, config             = load_data()
                        st.session_state.settings = config
                        st.session_state.assets   = [parse_asset_details(a) for a in data]
                        st.rerun()

    # [속성 수정] 전체 너비로 표시 (c_right 컬럼 밖으로 이동)
    st.markdown("---")
    with st.expander("🛠️ 속성 수정 (대출, 보증금, 매각 등)"):
        with st.form(f"meta_{asset['id']}"):
            c1, c2  = st.columns(2)
            e_name  = c1.text_input("자산명", value=asset['name'], key=f"name_{asset['id']}")
            e_acq_d = c2.text_input("취득일", value=acq_date, key=f"acq_d_{asset['id']}")
            c3, c4  = st.columns(2)
            e_acq_p = c3.number_input("취득가", value=acq_price, key=f"acq_p_{asset['id']}")
            
            e_addr, e_loan, e_dep = "", 0, 0
            if a_type == 'REAL_ESTATE':
                e_addr = c4.text_input("주소", value=asset.get('address', ''), key=f"addr_{asset['id']}")
                c5, c6 = st.columns(2)
                e_loan = c5.number_input("대출금", value=safe_float(asset.get('loanAmount', 0)), key=f"loan_{asset['id']}")
                e_dep  = c6.number_input("보증금", value=safe_float(asset.get('tenantDeposit', 0)), key=f"dep_{asset['id']}")
            
            e_mon_pay = 0
            e_growth  = 0
            if a_type == 'PENSION':
                e_mon_pay = c4.number_input("월 수령액(원)", value=safe_float(asset.get('expectedMonthlyPayout', 0)), key=f"mon_pay_{asset['id']}")
                e_growth  = c3.number_input("매년 증가율(%)", value=safe_float(asset.get('annualGrowthRate', 0)), key=f"growth_{asset['id']}")

            e_ticker = ""
            if a_type == 'STOCK':
                st.caption("자동 업데이트 설정")
                col_t1, col_t2 = st.columns([3, 1])
                curr_ticker = asset.get('ticker') or ""
                
                e_ticker = col_t1.text_input(
                    "Ticker (Yahoo Finance)", 
                    value       = curr_ticker, 
                    placeholder = "예: 005930.KS, TSLA, AAPL"
                )
                
                # 검색 링크 제공 (Form 내부 버튼 사용 불가로 링크만 제공)
                search_query = f"{asset['name']} ticker yahoo finance"
                search_url   = f"https://www.google.com/search?q={search_query}"
                col_t2.markdown(
                    f"<br><a href='{search_url}' target='_blank'>🔍 검색</a>", 
                    unsafe_allow_html=True
                )
            c_d1, c_d2 = st.columns(2)
            e_disp_d   = c_d1.text_input  ("매각일 (YYYY-MM-DD)", value=disp_date, key=f"disp_d_{asset['id']}")
            e_disp_p   = c_d2.number_input("매각금액", value=disp_price, key=f"disp_p_{asset['id']}")
            
            if st.form_submit_button("속성 저장"):
                st.session_state['expanded_asset_id'] = asset['id']
                st.session_state['expanded_account' ] = asset.get('accountName') 

                asset['name'            ] = e_name
                asset['acquisitionDate' ] = e_acq_d
                asset['acquisitionPrice'] = e_acq_p
                asset['disposalDate'    ] = e_disp_d
                asset['disposalPrice'   ] = e_disp_p
                
                if a_type == 'REAL_ESTATE':
                    asset['address'              ] = e_addr
                    asset['loanAmount'           ] = e_loan
                    asset['tenantDeposit'        ] = e_dep
                
                if a_type == 'PENSION':
                    asset['expectedMonthlyPayout'] = e_mon_pay
                    asset['detail5'              ] = e_growth
                    asset['annualGrowthRate'     ] = e_growth
                
                if a_type == 'STOCK':
                    asset['ticker'] = e_ticker
                    # [편의 기능] 동일한 이름을 가진 다른 주식 자산도 Ticker 일괄 적용
                    if e_ticker:
                        sync_cnt = 0
                        for a in st.session_state.assets:
                            if a['type'] == 'STOCK' and a['name'] == asset['name'] and a['id'] != asset['id']:
                                a['ticker'] = e_ticker
                                sync_cnt   += 1
                        if sync_cnt > 0:
                            st.toast(f"ℹ️ 동일한 이름의 자산 {sync_cnt}개에도 Ticker가 적용되었습니다.")

                st.success("저장됨")
                st.rerun()

        st.markdown("---")
        # 폼(form) 밖에서 버튼을 만들어야 바로 동작합니다.
        col_del_1, col_del_2 = st.columns([4, 1])
        with col_del_2:
            if st.button(
                "🗑️ 삭제", 
                key    = f"del_btn_{asset['id']}", 
                type   = "primary", 
                help   = "이 자산을 영구적으로 삭제합니다."
            ):
                st.session_state['expanded_account'] = asset.get('accountName')                        
                # 1. 자산 리스트에서 해당 ID를 가진 항목 제외 (삭제)
                st.session_state.assets = [a for a in st.session_state.assets if a['id'] != asset['id']]
                
                # 2. DB에서도 삭제
                from database import delete_asset
                delete_asset(asset['id'])
                    
                st.toast("자산이 삭제되었습니다.")
                st.rerun()                    


# -----------------------------------------------------------------------------------------------------
# [초기화]
# -----------------------------------------------------------------------------------------------------
if 'assets' not in st.session_state:
    data, config              = load_data()
    st.session_state.assets   = [parse_asset_details(a) for a in data]
    st.session_state.settings = config

assets = st.session_state.assets
load_css()


# -----------------------------------------------------------------------------------------------------
# [사이드바]
# -----------------------------------------------------------------------------------------------------
with st.sidebar:
    st.title("💼 My Asset Manager")
    st.markdown("---")
    menu_keys   = ['REAL_ESTATE', 'STOCK', 'PENSION', 'SAVINGS', 'PHYSICAL', 'ETC']
    menu_labels = [TYPE_LABEL_MAP[k] for k in menu_keys]
    menu_items  = ["📊 대시보드"] + menu_labels + ["⚙️ 설정"]
    menu        = st.radio("메뉴 이동", menu_items)
    
    st.markdown("---")
    st.markdown("---")
    
    # 버튼을 한 줄에 배치하고 너비를 꽉 채움
    col_sb1, col_sb2 = st.columns(2)
    
    with col_sb1:
        if st.button("🔄 새로고침", use_container_width=True):
            st.cache_data.clear()
            data, config              = load_data()
            st.session_state.settings = config
            st.session_state.assets   = [parse_asset_details(a) for a in data]
            st.rerun()

    with col_sb2:
        if st.button("💾 저장하기", type="primary", use_container_width=True):
            # SQLite로 직접 저장 (필드 변환 필요 없음)
            if save_data(st.session_state.assets, st.session_state.settings):
                st.success("저장됨")
            else:
                st.error("실패")

# -----------------------------------------------------------------------------------------------------
# 1. 대시보드
# -----------------------------------------------------------------------------------------------------
if menu == "📊 대시보드":
    st.title("📊 통합 자산 대시보드")
    total_asset = 0
    total_liab  = 0
    for a in assets:
        if a.get('disposalDate'): continue
        val          = safe_float(a.get('currentValue'))
        total_asset += val
        if a['type'] == 'REAL_ESTATE':
            total_liab += safe_float(a.get('loanAmount'))
            total_liab += safe_float(a.get('tenantDeposit'))
    net_worth = total_asset - total_liab
    
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(render_kpi_card_html("💰 총 자산", format_money(total_asset)), unsafe_allow_html=True)
    with c2: st.markdown(render_kpi_card_html("📉 총 부채", format_money(total_liab), "#e03131"), unsafe_allow_html=True)
    with c3: st.markdown(render_kpi_card_html("💎 순자산" , format_money(net_worth), "#1c7ed6"), unsafe_allow_html=True)
    
    st.divider()
    if assets:
        df_chart = pd.DataFrame(assets)
        df_chart = df_chart[df_chart['disposalDate'].isin([None, ""])]

        if not df_chart.empty:
            st.subheader("📊 자산 비중")
            grp          = df_chart.groupby('type')['currentValue'].sum().reset_index()
            grp['label'] = grp['type'].map(TYPE_LABEL_MAP)
            fig_pie      = px.pie(
                grp,
                values             = 'currentValue',
                names              = 'label',
                color              = 'type',
                color_discrete_map = COLOR_MAP,
                hole               = 0.4
            )
            fig_pie.update_traces(
                textposition = 'inside',
                textinfo     = 'percent+label'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📈 자산 성장 추이 (최근 10년)")
            # 대시보드는 전체(10년) 기준
            df_hist = generate_history_df(assets) 
            if not df_hist.empty:
                df_hist['value_man'] = df_hist['value'] / 10000
                df_area = df_hist.groupby(['date', 'type'])['value_man'].sum().reset_index()
                df_area['label'] = df_area['type'].map(TYPE_LABEL_MAP)
                # 날짜별 합계 계산
                df_totals = df_area.groupby('date')['value_man'].sum().to_dict()
                df_area['total'] = df_area['date'].map(df_totals)
                
                fig_area = px.area(
                    df_area,
                    x                  = 'date',
                    y                  = 'value_man',
                    color              = 'label',
                    color_discrete_map = {v: COLOR_MAP[k] for k, v in TYPE_LABEL_MAP.items()},
                    labels             = {'value_man': '가치(만원)'},
                    custom_data        = ['label', 'total']
                )
                
                # 커스텀 hover 템플릿: 항목명 - 금액(만원)
                fig_area.update_traces(
                    hovertemplate = "%{customdata[0]}: %{y:,.0f}(만원)<extra></extra>"
                )
                
                # [수정] 대시보드 차트도 가독성 개선
                fig_area.update_layout(
                    hovermode          = "x unified",
                    xaxis              = dict(nticks=20, tickformat="%y.%m.%d")
                )
                st.plotly_chart(fig_area, use_container_width=True)

# -----------------------------------------------------------------------------------------------------
# 2. 자산별 
# -----------------------------------------------------------------------------------------------------
elif menu in TYPE_LABEL_MAP.values():
    target_type = [k for k, v in TYPE_LABEL_MAP.items() if v == menu][0]
    
    if target_type == 'STOCK':
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.title(menu)
        with col_h2:
            st.markdown('<div style="height: 15px;"></div>', unsafe_allow_html=True)
            if st.button("📈 주가 업데이트", key="btn_stock_upd", type="primary", use_container_width=True):
                with st.spinner("시세 정보를 가져오는 중입니다..."):
                    try:
                        import stock_updater
                        count = stock_updater.update_all_stocks()
                        if count > 0: st.success(f"{count}개 종목 업데이트 완료!")
                        else        : st.warning("업데이트된 종목이 없습니다. (Ticker 설정을 확인하세요)")
                        
                        # [Fix] 데이터 갱신 반영을 위해 캐시 및 세션 초기화
                        st.cache_data.clear()
                        if 'assets' in st.session_state:
                            del st.session_state['assets']
                        
                        time.sleep(1)
                        st.rerun()
                    except ImportError:
                        st.error("yfinance 모듈 미설치")
                    except Exception as e:
                        st.error(f"오류: {e}")

        view_mode = st.radio("보기 모드", ["계좌별 보기", "종목별 보기"], horizontal=True)
    else:
        st.title(menu)
        view_mode = "계좌별 보기"
    
    my_assets = [a for a in assets if a['type'] == target_type]
    
    display_category_summary(menu, my_assets)

    if my_assets:
        # [수정] 상단 차트도 자산 유형별 기간(3년/10년) 적용

        # [Refactoring] 차트 데이터 일괄 생성 및 필터링 (Global Filter)
        full_chart_data = generate_history_df(my_assets, target_type)
        
        # [UI Improvement] 차트 기간 선택 (Global) - Advanced
        start_date = None
        end_date   = None
        limit_date = None
        
        if target_type == 'STOCK' and not full_chart_data.empty:
            # 1. State 초기화
            if 'chart_period_preset' not in st.session_state:
                st.session_state['chart_period_preset'] = '전체'
            
            # 2. 날짜 계산 헬퍼
            today = datetime.now().date()
            base_start = datetime(2023, 1, 1).date()
            
            def get_preset_range(preset):
                if preset == '전체':
                    return base_start, today
                elif preset == '최근 1년':
                    return today - timedelta(days=365), today
                elif preset == '최근 3개월':
                    return today - timedelta(days=90), today
                elif preset == '최근 1개월':
                    return today - timedelta(days=30), today
                return base_start, today

            # 3. 프리셋 변경 시 처리 (Callback)
            def on_preset_change():
                sel = st.session_state['chart_period_preset']
                s, e = get_preset_range(sel)
                st.session_state['chart_start_date'] = s
                st.session_state['chart_end_date']   = e

            # 4. UI 렌더링
            # 상단: 프리셋 선택 / 하단: Date Picker (From - To)
            # [수정] 전체 너비의 1/3을 차지하도록 비율 조정 (Inputs: 3.2 / Sum: ~9.7 => ~33%)
            c_p1, c_p2, c_p3, _ = st.columns([1.2, 1, 1, 6.5])
            
            with c_p1:
                st.selectbox(
                    "기간 설정", 
                    options=['전체', '최근 1년', '최근 3개월', '최근 1개월'], 
                    key='chart_period_preset',
                    on_change=on_preset_change,
                    label_visibility="collapsed"
                )
            
            # 초기값 동기화 (세션에 없으면 프리셋 기준 설정)
            if 'chart_start_date' not in st.session_state:
                s, e = get_preset_range(st.session_state['chart_period_preset'])
                st.session_state['chart_start_date'] = s
                st.session_state['chart_end_date']   = e
            
            with c_p2:
                d_start = st.date_input(
                    "From", 
                    value=st.session_state['chart_start_date'],
                    key='chart_start_date',
                    label_visibility="collapsed"
                )
            with c_p3:
                d_end = st.date_input(
                    "To", 
                    value=st.session_state['chart_end_date'],
                    key='chart_end_date',
                    label_visibility="collapsed"
                )
            
            # [Filter Appling]
            # 문자열 비교를 위해 변환
            s_str = d_start.strftime("%Y-%m-%d")
            e_str = d_end.strftime("%Y-%m-%d")
            
            full_chart_data = full_chart_data[
                (full_chart_data['date'] >= s_str) & 
                (full_chart_data['date'] <= e_str)
            ]
            
            # 30일(1개월) 로직 등 기존 로직 호환성을 위해 limit_date 플래그 설정
            # (Y축 스케일 조정 로직 트리거용: 전체가 아니면 조정)
            limit_date = True if st.session_state['chart_period_preset'] != '전체' else None
            
            # 만약 사용자가 날짜를 수동으로 바꿨다면 프리셋과 다를 수 있음 -> 별도 처리 안해도 됨 (값 우선)

        # 상단 차트용 데이터 (이미 필터링됨)
        df_hist = full_chart_data
        
        if not df_hist.empty:
            df_hist['value_man'] = df_hist['value'] / 10000
            
            # [수정] 모든 기간에 대해 동일한 Area Chart 적용 (기간 필터만 다름)
            if target_type == 'STOCK' and view_mode == "계좌별 보기":
                df_chart_grp = df_hist.groupby(['date', 'account'])['value_man'].sum().reset_index()
                # 날짜별 합계 계산
                df_totals = df_chart_grp.groupby('date')['value_man'].sum().to_dict()
                df_chart_grp['total'] = df_chart_grp['date'].map(df_totals)
                
                fig = px.area(
                    df_chart_grp, 
                    x                       = 'date', 
                    y                       = 'value_man', 
                    color                   = 'account', 
                    color_discrete_sequence = PASTEL_COLORS, 
                    labels                  = {'value_man': '가치(만원)'},
                    custom_data             = ['account', 'total']
                )
                # 커스텀 hover 템플릿: 항목명 - 금액(만원)
                fig.update_traces(
                    hovertemplate = "%{customdata[0]}: %{y:,.0f}(만원)<extra></extra>"
                )
            else:
                df_chart_grp = df_hist.groupby(['date', 'name'])['value_man'].sum().reset_index()
                # 날짜별 합계 계산
                df_totals = df_chart_grp.groupby('date')['value_man'].sum().to_dict()
                df_chart_grp['total'] = df_chart_grp['date'].map(df_totals)
                
                fig = px.area(
                    df_chart_grp, 
                    x                       = 'date', 
                    y                       = 'value_man', 
                    color                   = 'name', 
                    color_discrete_sequence = PASTEL_COLORS, 
                    labels                  = {'value_man': '가치(만원)'},
                    custom_data             = ['name', 'total']
                )
                # 커스텀 hover 템플릿: 항목명 - 금액(만원)
                fig.update_traces(
                    hovertemplate = "%{customdata[0]}: %{y:,.0f}(만원)<extra></extra>"
                )
            
            fig.update_layout(
                height             = 300, 
                margin             = dict(t=0, b=0, l=0, r=0),
                hovermode          = "x unified",
                xaxis              = dict(nticks=20, tickformat="%y.%m.%d")
            )
            # 30일 보기일 경우 (Y축 0부터 시작 유지 - 별도 처리 없음)
            if limit_date:
                # [수정] 메인 차트는 0부터 시작하도록 강제 (Gap 로직 제거)
                pass

            st.plotly_chart(fig, use_container_width=True)

    if target_type == 'PENSION':
        linked = [a for a in assets if a.get('isPensionLike')]
        all_p = my_assets + linked
        if all_p:
            st.divider()
            st.subheader("📊 노후 월 수령액 시뮬레이션")
            age = st.session_state.settings.get('current_age', 40)
            yr = datetime.now().year
            data = []
            for y in range(yr, yr+60):
                curr_age = age + (y - yr)
                row = {'age': f"{curr_age}세", 'total': 0}
                for p in all_p:
                    s    = safe_int(p.get('expectedStartYear')) or 2060
                    e    = safe_int(p.get('expectedEndYear')) or 9999
                    m    = safe_float(p.get('expectedMonthlyPayout'))
                    rate = safe_float(p.get('annualGrowthRate', 0)) / 100.0
                    
                    if s <= y <= e:
                        elapsed        = max(0, y - s)
                        adjusted_m     = m * ((1 + rate) ** elapsed)
                        val_man        = adjusted_m / 10000 
                        row[p['name']] = val_man
                        row['total']  += val_man
                data.append(row)
            df_sim = pd.DataFrame(data)
            fig_sim = px.bar(
                df_sim, 
                x                       = 'age', 
                y                       = [c for c in df_sim.columns if c not in ['age','total']], 
                labels                  = {'value':'월수령액(만원)'}, 
                color_discrete_sequence = PASTEL_COLORS
            )
            fig_sim.update_layout(
                barmode                 = 'stack', 
                height                  = 300,
                hovermode               = "x unified"
            )
            st.plotly_chart(fig_sim, use_container_width=True)

    with st.expander(f"➕ 신규 {menu.split()[1]} 추가"):
        with st.form("add_new"):
            c1, c2 = st.columns(2)
            n_name = c1.text_input("자산명")
            
            # [수정] 실물자산/주식은 수량/단가 입력
            if target_type in ['STOCK', 'PHYSICAL']:
                n_qty   = c2.number_input("수량", min_value=0.0)
                n_price = c2.number_input("단가", min_value=0.0)
                n_val   = n_qty * n_price
            else:
                n_val   = c2.number_input("현재가치/취득가", min_value=0)
                n_qty   = 0
                n_price = 0
                
            n_date = st.date_input("취득일").strftime("%Y-%m-%d")
            
            n_acc      = ""
            n_ticker   = ""
            n_currency = "KRW"
            
            if target_type == 'STOCK':
                col_acc, col_curr = st.columns([2, 1])
                n_acc      = col_acc.text_input("계좌명")
                n_currency = col_curr.selectbox("통화", ["KRW", "USD", "JPY"], index=0)
                n_ticker   = st.text_input("Ticker (자동 업데이트용)", help="예: TSLA, AAPL, 005930.KS")
            
            if st.form_submit_button("추가"):
                new_id = str(uuid.uuid4())
                st.session_state['expanded_asset_id'] = new_id
                st.session_state['expanded_account' ] = n_acc

                new_asset = {
                    "id"               : new_id, 
                    "type"             : target_type, 
                    "name"             : n_name, 
                    "currentValue"     : n_val, 
                    "acquisitionPrice" : n_val if n_price==0 else n_price, 
                    "acquisitionDate"  : n_date, 
                    "accountName"      : n_acc,
                    "account_name"     : n_acc,  # DB 삽입용 (database.py가 account_name을 기대함)
                    "quantity"         : n_qty,
                    "ticker"           : n_ticker,
                    "currency"         : n_currency,
                    "history"          : [{"date":n_date, "value":n_val, "price":n_price, "quantity":n_qty}]
                }
                
                # [Fix] DB 저장 누락 수정
                from database import insert_asset
                insert_asset(new_asset)
                
                # 세션 반영
                st.session_state.assets.append(new_asset)
                
                st.success("추가되었습니다.")
                st.cache_data.clear() # 캐시 초기화
                st.rerun()

    st.divider()

    if target_type == 'STOCK' and view_mode == "계좌별 보기":
        # full_chart_data is already calculated and filtered above

        accounts = list(set([a.get('accountName', '기타') for a in my_assets]))
        
        # [1단계] 모든 계좌 버튼을 먼저 표시 (빠른 로딩)
        st.markdown("##### 📂 계좌 선택")
        
        # 계좌별 요약 정보 미리 계산
        account_summaries = {}
        for acc in accounts:
            acc_assets = [a for a in my_assets if a.get('accountName') == acc]
            total_with_adj = sum([safe_float(a['currentValue']) for a in acc_assets])
            current_target = st.session_state.settings.get(f"ACC_TOTAL_{acc}", total_with_adj)
            
            total_invested = 0
            for a in acc_assets:
                qty = safe_float(a.get('quantity', 0))
                prc = safe_float(a.get('acquisitionPrice', 0))
                total_invested += (qty * prc)
            
            acc_pl  = total_with_adj - total_invested
            acc_roi = (acc_pl / total_invested * 100) if total_invested > 0 else 0
            pl_sign = "-" if acc_pl < 0 else "+"
            
            account_summaries[acc] = {
                'assets': acc_assets,
                'total': total_with_adj,
                'current_target': current_target,
                'pl': acc_pl,
                'roi': acc_roi,
                'pl_sign': pl_sign,
                'count': len(acc_assets)
            }
        
        # 버튼 그리드 (2열) - 파스텔 색상 적용
        pastel_btn_colors = ['#a8dadc', '#f1faee', '#ffd6a5', '#caffbf', '#bdb2ff', '#ffc6ff']
        
        cols = st.columns(2)
        for idx, acc in enumerate(accounts):
            info = account_summaries[acc]
            is_selected = (acc == st.session_state.get('expanded_account'))
            
            # 선택 여부에 따른 색상
            base_color = pastel_btn_colors[idx % len(pastel_btn_colors)]
            
            with cols[idx % 2]:
                # 선택된 것은 진한 색, 아니면 파스텔
                if is_selected:
                    btn_style = f"background-color: #4c6ef5; color: white; border: none;"
                else:
                    btn_style = f"background-color: {base_color}; color: #333; border: none;"
                
                btn_label = f"📂 {acc} ___ {format_money(info['total'])} | {info['pl_sign']}{format_money(abs(info['pl']))} ({info['roi']:+.1f}%)"
                
                # 스타일링된 버튼 (HTML)
                st.markdown(f'''
                    <style>
                    div[data-testid="stButton"] > button[key="acc_btn_{acc}"] {{
                        {btn_style}
                    }}
                    </style>
                ''', unsafe_allow_html=True)
                
                btn_type = "primary" if is_selected else "secondary"
                if st.button(btn_label, key=f"acc_btn_{acc}", use_container_width=True, type=btn_type):
                    if is_selected:
                        st.session_state['expanded_account'] = None
                    else:
                        st.session_state['expanded_account'] = acc
                    st.rerun()
        
        st.markdown("---")
        
        # [2단계] 선택된 계좌의 상세 내용만 렌더링
        selected_acc = st.session_state.get('expanded_account')
        if selected_acc and selected_acc in account_summaries:
            info = account_summaries[selected_acc]
            acc_assets = info['assets']
            
            st.markdown(f"##### 📂 {selected_acc} 상세")
            
            # [추가] 계좌 KPI (복구됨)
            k1, v1 = "총 평가액", format_money(info['total'])
            k2, v2 = "투자 원금", format_money(info['total'] - info['pl'])
            k3, v3 = "평가 손익", f"{info['pl_sign']}{format_money(abs(info['pl']))} ({info['roi']:+.1f}%)"
            
            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(render_kpi_card_html(k1, v1), unsafe_allow_html=True)
            with c2: st.markdown(render_kpi_card_html(k2, v2), unsafe_allow_html=True)
            with c3: st.markdown(render_kpi_card_html(k3, v3, "#e03131" if info['pl'] < 0 else "#2f9e44"), unsafe_allow_html=True)
            
            st.markdown("---")
            
            # [추가] 계좌별 차트
            df_acc_chart = full_chart_data[full_chart_data['account'] == selected_acc].copy() if 'account' in full_chart_data.columns else pd.DataFrame()
            if not df_acc_chart.empty:
                df_acc_chart['value_man'] = df_acc_chart['value'] / 10000
                df_acc_grp = df_acc_chart.groupby('date')['value_man'].sum().reset_index()
                
                # [수정] 계좌 차트도 0부터 시작하도록 강제 (Range 설정 제거)
                
                fig_acc = px.area(
                    df_acc_grp, 
                    x                       = 'date', 
                    y                       = 'value_man',
                    color_discrete_sequence = ['#4c6ef5'],
                    labels                  = {'value_man': '평가액(만원)'}
                )
                fig_acc.update_layout(
                    height    = 200,
                    margin    = dict(t=0, b=0, l=0, r=0),
                    hovermode = "x unified",
                    xaxis     = dict(nticks=10, tickformat="%y.%m.%d")
                )
                
                # Y축 Range 설정 제거
                st.plotly_chart(fig_acc, use_container_width=True, key=f"acc_chart_{selected_acc}")
            
            # [추가] 계좌별 차트 (잔고 보정 폼 제거됨)
            
            st.markdown("---")
            
            # 종목 목록
            for a in acc_assets:
                val = safe_float(a['currentValue'])
                qty = safe_float(a.get('quantity', 0))
                acq = safe_float(a.get('acquisitionPrice', 0))
                
                # 수익률 계산
                invested = acq * qty
                pl       = val - invested
                roi      = (pl / invested * 100) if invested > 0 else 0
                pl_sign  = "+" if pl > 0 else "" if pl == 0 else "-"
                
                label = f"{a['name']}"
                if qty > 0:
                    label += f" ({qty:,.0f}주)"
                
                label += f" ___ {format_money(val)} | {pl_sign}{format_money(abs(pl))} ({roi:+.1f}%)"
                
                if a.get('disposalDate'): label += " (🔴매각)"

                is_asset_open = (a['id'] == st.session_state.get('expanded_asset_id'))
                with st.expander(label, expanded=is_asset_open):
                    render_asset_detail(a, precalc_df=full_chart_data)
        else:
            st.info("👆 위에서 계좌를 선택하세요.")
    else:
        # 종목별 보기 (Stock View Only)
        if target_type == 'STOCK':
             # full_chart_data is already calculated and filtered above
             
             for a in my_assets:
                val = safe_float(a['currentValue'])
                qty = safe_float(a.get('quantity', 0))
                acq = safe_float(a.get('acquisitionPrice', 0))
                
                # 수익률 계산
                invested = acq * qty
                pl       = val - invested
                roi      = (pl / invested * 100) if invested > 0 else 0
                pl_sign  = "+" if pl > 0 else "" if pl == 0 else "-"
                
                label = f"{a['name']}"
                if qty > 0:
                    label += f" ({qty:,.0f}주)"
                
                label += f" ___ {format_money(val)} | {pl_sign}{format_money(abs(pl))} ({roi:+.1f}%)"
                
                if a.get('disposalDate'): label += " (🔴매각)"
                
                with st.expander(label):
                    render_asset_detail(a, precalc_df=full_chart_data)
        else:
            # Other types (Real Estate, Pension, etc) - 배치 처리 적용
            full_chart_data = generate_history_df(my_assets, target_type)
            
            for a in my_assets:
                val = safe_float(a['currentValue'])
                badges = []
                if a.get('disposalDate'): badges.append('<span class="badge badge-red">매각됨</span>')
                
                with st.expander(f"{a['name']} {format_money(val)}"):
                    if badges: st.markdown(" ".join(badges), unsafe_allow_html=True)
                    render_asset_detail(a, precalc_df=full_chart_data)



# -----------------------------------------------------------------------------------------------------
# 설정
# -----------------------------------------------------------------------------------------------------
elif menu == "⚙️ 설정":
    st.title("⚙️ 설정")
    with st.form("settings_form"):
        st.subheader("기본 설정")
        current_age    = st.number_input("현재 나이", value=int(st.session_state.settings.get('current_age', 40)))
        retirement_age = st.number_input("은퇴 목표 나이", value=int(st.session_state.settings.get('retirement_age', 60)))
        if st.form_submit_button("설정 적용"):
            st.session_state.settings['current_age']    = current_age
            st.session_state.settings['retirement_age'] = retirement_age
            st.success("설정이 적용되었습니다. (구글 시트에 반영하려면 사이드바의 '저장하기'를 눌러주세요)")
            st.rerun()
    st.info("💡 설정 값은 앱의 은퇴 시뮬레이션 등에 사용됩니다.")

