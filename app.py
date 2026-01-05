# -----------------------------------------------------------------------------------------------------
# Import
# -----------------------------------------------------------------------------------------------------
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import uuid
from datetime import datetime, timedelta
from utils import load_data, save_data

# -----------------------------------------------------------------------------------------------------
# [설정] 페이지 및 스타일
# -----------------------------------------------------------------------------------------------------
st.set_page_config(page_title="My Asset Manager", page_icon="💰", layout="wide")

PASTEL_COLORS = px.colors.qualitative.Pastel 

COLOR_MAP = {
    'REAL_ESTATE': PASTEL_COLORS[2], 
    'STOCK': PASTEL_COLORS[0],       
    'PENSION': PASTEL_COLORS[4],     
    'SAVINGS': PASTEL_COLORS[3],     
    'PHYSICAL': PASTEL_COLORS[5],    
    'ETC': PASTEL_COLORS[1]          
}

TYPE_LABEL_MAP = {
    'REAL_ESTATE': '🏠 부동산',
    'STOCK': '📈 주식',
    'PENSION': '🛡️ 연금',
    'SAVINGS': '💰 예적금/현금',
    'PHYSICAL': '💎 실물자산',
    'ETC': '🎸 기타'
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
    with c1: st.markdown(render_kpi_card_html(f"💰 {asset_name} 자산", format_money(cat_total_asset)), unsafe_allow_html=True)
    with c2: st.markdown(render_kpi_card_html(f"📉 {asset_name} 부채", format_money(cat_total_liab), "#e03131"), unsafe_allow_html=True)
    with c3: st.markdown(render_kpi_card_html(f"💎 {asset_name} 순자산", format_money(cat_net_worth), "#1c7ed6"), unsafe_allow_html=True)
    
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
    a_type = asset.get('type')
    
    asset['currentValue'] = safe_float(asset.get('currentValue'))
    asset['acquisitionPrice'] = safe_float(asset.get('acquisitionPrice'))
    asset['quantity'] = safe_float(asset.get('quantity'))
    asset['disposalPrice'] = safe_float(asset.get('disposalPrice'))
    
    if not asset.get('acquisitionDate'): asset['acquisitionDate'] = ""
    if not asset.get('disposalDate'): asset['disposalDate'] = ""
    
    if a_type == 'REAL_ESTATE':
        asset['isOwned'] = True if 'OWNED' in str(asset.get('detail1', '')).upper() else False
        asset['hasTenant'] = True if 'HAS_TENANT' in str(asset.get('detail2', '')).upper() else False
        asset['tenantDeposit'] = safe_float(asset.get('detail3'))
        asset['address'] = str(asset.get('detail4', ''))
        asset['loanAmount'] = safe_float(asset.get('detail5'))
    
    elif a_type == 'STOCK':
        asset['accountName'] = str(asset.get('detail1', '기타'))
        asset['currency'] = str(asset.get('detail2', 'KRW'))
        if asset['currentValue'] == 0 and asset['quantity'] > 0:
            asset['currentValue'] = asset['quantity'] * asset['acquisitionPrice']

    elif a_type == 'PENSION':
        asset['pensionType'] = str(asset.get('detail1', 'PERSONAL'))
        asset['expectedStartYear'] = safe_int(asset.get('detail2'))
        asset['expectedMonthlyPayout'] = safe_float(asset.get('detail3'))
        asset['expectedEndYear'] = safe_int(asset.get('detail4'))
        asset['annualGrowthRate'] = safe_float(asset.get('detail5', 0))
        
    d5 = str(asset.get('detail5', ''))
    if a_type in ['STOCK', 'SAVINGS'] and (d5 == 'Y' or d5.startswith('PENSION')):
        asset['isPensionLike'] = True
        if d5.startswith('PENSION'):
            try:
                parts = d5.split('_')
                if len(parts) >= 3:
                    asset['expectedStartYear'] = int(parts[1])
                    asset['expectedMonthlyPayout'] = float(parts[2])
            except: pass

    return asset

# -----------------------------------------------------------------------------------------------------
# [핵심 로직] 주식 계좌 잔고 보정
# -----------------------------------------------------------------------------------------------------
def recalculate_account_balance(account_name, target_total=None):
    if not account_name or account_name == "기타": return

    settings = st.session_state.settings
    settings_key = f"ACC_TOTAL_{account_name}"
    
    if target_total is not None:
        settings[settings_key] = target_total
    else:
        if settings_key in settings:
            target_total = safe_float(settings[settings_key])
        else:
            return 

    assets = st.session_state.assets
    stock_assets = [a for a in assets if a['type'] == 'STOCK' and a.get('accountName') == account_name]
    
    adj_asset = next((a for a in stock_assets if a.get('detail5') == 'BALANCE_ADJUSTMENT'), None)
    
    current_sum = 0
    for a in stock_assets:
        if a.get('detail5') != 'BALANCE_ADJUSTMENT':
            current_sum += safe_float(a['currentValue'])
            
    diff = target_total - current_sum
    today = datetime.now().strftime("%Y-%m-%d")
    
    if adj_asset:
        adj_asset['currentValue'] = diff
        h = adj_asset.get('history', [])
        if isinstance(h, str): h = []
        
        existing_h = next((x for x in h if x.get('date') == today), None)
        if existing_h:
            existing_h['value'] = diff 
            existing_h['price'] = diff
            existing_h['quantity'] = 1
        else:
            h.append({"date": today, "value": diff, "price": diff, "quantity": 1})
        h.sort(key=lambda x: x['date'])
        adj_asset['history'] = h
        
    else:
        new_adj = {
            "id": str(uuid.uuid4()),
            "type": "STOCK",
            "name": f"[보정] {account_name}",
            "accountName": account_name,
            "currentValue": diff,
            "acquisitionPrice": 0,
            "quantity": 1,
            "acquisitionDate": today,
            "detail5": "BALANCE_ADJUSTMENT",
            "history": [{"date": today, "value": diff, "price": diff, "quantity": 1}]
        }
        st.session_state.assets.append(new_adj)

# -----------------------------------------------------------------------------------------------------
# [핵심 로직] 차트 데이터 생성 (기간 설정 + 실물자산 단가 적용)
# -----------------------------------------------------------------------------------------------------
def generate_history_df(assets, type_filter=None):
    if not assets: return pd.DataFrame()
    target_assets = [a for a in assets if (type_filter is None or a['type'] == type_filter)]
    if not target_assets: return pd.DataFrame()

    rows = []
    today = datetime.now()
    
    # [수정] 기간 설정 로직 (대시보드/부동산=10년, 나머지=3년)
    # type_filter가 None이면 대시보드
    is_long_term = (type_filter is None) or (type_filter == 'REAL_ESTATE')
    period_years = 10 if is_long_term else 3
        
    START_LIMIT = today - timedelta(days=365 * period_years)
    
    plot_start = START_LIMIT
    plot_end = today
    full_date_range = pd.date_range(start=plot_start, end=plot_end, freq='D')
    
    for a in target_assets:
        try: 
            if a.get('acquisitionDate'):
                acq_date = datetime.strptime(str(a.get('acquisitionDate')), "%Y-%m-%d")
            else:
                acq_date = datetime(2023, 1, 1)
        except: 
            acq_date = datetime(2023, 1, 1)

        disp_date = None
        if a.get('disposalDate'):
            try: disp_date = datetime.strptime(str(a.get('disposalDate')), "%Y-%m-%d")
            except: pass
            
        val_map = {}
        
        # [수정] 실물자산(PHYSICAL)도 주식처럼 수량 기반 계산 지원
        is_qty_based = a['type'] in ['STOCK', 'PHYSICAL']
        
        # (1) 초기값
        init_val = safe_float(a.get('acquisitionPrice', 0))
        if is_qty_based:
            qty = safe_float(a.get('quantity', 0))
            if qty == 0 and a.get('detail5') == 'BALANCE_ADJUSTMENT': qty = 1
            if qty > 0: init_val = init_val * qty

        val_map[acq_date] = init_val
        
        # (2) 히스토리
        hist_str = a.get('history', [])
        history = []
        if isinstance(hist_str, str):
            try: history = json.loads(hist_str)
            except: history = []
        elif isinstance(hist_str, list): history = hist_str
        
        for h in history:
            if 'date' in h:
                try:
                    d = datetime.strptime(h['date'], "%Y-%m-%d")
                    v = 0
                    if 'value' in h: 
                        v = safe_float(h['value'])
                    elif 'price' in h and 'quantity' in h: 
                        v = safe_float(h['price']) * safe_float(h['quantity'])
                    val_map[d] = v
                except: pass
        
        # (3) 현재값
        if not disp_date: val_map[today] = safe_float(a.get('currentValue', 0))
        else: val_map[disp_date] = safe_float(a.get('disposalPrice', 0))

        # (4) Forward Fill
        sorted_dates = sorted(val_map.keys())
        
        for d in full_date_range:
            chart_val = 0
            if d < acq_date: chart_val = 0
            elif disp_date and d.date() > disp_date.date(): chart_val = 0
            else:
                past_events = [sd for sd in sorted_dates if sd <= d]
                if past_events:
                    latest_event_date = past_events[-1]
                    chart_val = val_map[latest_event_date]
                else:
                    chart_val = init_val
                
                if a['type'] == 'REAL_ESTATE':
                    liab = safe_float(a.get('loanAmount', 0)) + safe_float(a.get('tenantDeposit', 0))
                    chart_val = max(0, chart_val - liab)
            
            rows.append({
                'date': d.strftime("%Y-%m-%d"),
                'value': chart_val,
                'name': a['name'],
                'type': a['type'],
                'account': a.get('accountName', '기타')
            })
            
    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------------------------------
# [통합] 자산 상세 렌더러
# -----------------------------------------------------------------------------------------------------
def render_asset_detail(asset):
    a_type       = asset['type']
    is_adj       = (a_type == 'STOCK' and asset.get('detail5') == 'BALANCE_ADJUSTMENT')
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
        if is_qty_based and not is_adj:
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
        if is_adj:
            k1, v1 = "보정 금액", format_money(display_val)
            k2, v2 = "-", "-"
            k3, v3 = "계좌 잔고 보정용", "자동 계산됨"
        else:
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
    # [수정] 상세 화면에서도 type을 넘겨서 기간 설정(3년/10년)을 따르게 함
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
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("데이터가 부족하여 차트를 표시할 수 없습니다.")

    st.markdown("---")

    if is_adj:
        st.info("🔒 이 항목은 계좌 총액에 맞춰 자동으로 계산되는 '잔고 보정' 항목입니다. 수동으로 수정할 수 없습니다.")
    else:
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
                    row['price'   ] = safe_float(h.get('price', 0))
                    row['quantity'] = safe_float(h.get('quantity', 0))
                else:
                    row['value'   ] = safe_float(h.get('value', 0))
                data_list.append(row)
                
            df_edit = pd.DataFrame(data_list)
            if df_edit.empty:
                df_edit = pd.DataFrame({'date': [datetime.now().strftime("%Y-%m-%d")], 'value': [0.0]}) if not is_qty_based else pd.DataFrame({'date': [datetime.now().strftime("%Y-%m-%d")], 'price': [0.0], 'quantity': [0.0]})

            edited_df = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True, key=f"ed_{asset['id']}")
            
            if st.button("이력 저장", key=f"bs_{asset['id']}"):
                st.session_state['expanded_asset_id'] = asset['id']
                st.session_state['expanded_account' ] = asset.get('accountName') # 주식 계좌 뷰를 위해 계좌명도 저장
                
                new_hist = []
                for _, row in edited_df.iterrows():
                    d_str = str(row['date'])[:10]
                    rec = {'date': d_str}
                    if is_qty_based:
                        rec['price'   ] = safe_float(row.get('price'))
                        rec['quantity'] = safe_float(row.get('quantity'))
                    else:
                        rec['value'   ] = safe_float(row.get('value'))
                    new_hist.append(rec)
                
                new_hist.sort(key=lambda x: x['date'])
                asset['history'] = new_hist
                if new_hist:
                    last = new_hist[-1]
                    if is_qty_based:
                        asset['currentValue'] = last['price'] * last['quantity']
                        asset['quantity'    ] = last['quantity']
                    else:
                        asset['currentValue'] = last['value']
                
                if a_type == 'STOCK': recalculate_account_balance(asset.get('accountName'))
                st.success("저장되었습니다. (사이드바 저장하기 필수)")
                st.rerun()

        with c_right:
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
                    h = asset.get('history', [])
                    if isinstance(h, str): 
                        try   : h = json.loads(h)
                        except: h = []
                    elif not isinstance(h, list): h = []
                    
                    if is_qty_based:
                        h.append({"date": d_str, "price": n_p, "quantity": n_q})
                        asset['currentValue'] = n_p * n_q
                        asset['quantity'    ] = n_q
                    else:
                        h.append({"date": d_str, "value": n_v})
                        asset['currentValue'] = n_v
                    
                    h.sort(key=lambda x: x['date'])
                    asset['history'] = h
                    
                    if a_type == 'STOCK': recalculate_account_balance(asset.get('accountName'))
                    st.success("추가됨")
                    st.rerun()

        st.markdown("---")
        with st.expander("🛠️ 속성 수정 (대출, 보증금, 매각 등)"):
            with st.form(f"meta_{asset['id']}"):
                c1, c2 = st.columns(2)
                e_name = c1.text_input("자산명", value=asset['name'])
                e_acq_d = c2.text_input("취득일", value=acq_date)
                c3, c4 = st.columns(2)
                e_acq_p = c3.number_input("취득가", value=acq_price)
                
                e_addr, e_loan, e_dep = "", 0, 0
                if a_type == 'REAL_ESTATE':
                    e_addr = c4.text_input("주소", value=asset.get('address', ''))
                    c5, c6 = st.columns(2)
                    e_loan = c5.number_input("대출금", value=safe_float(asset.get('loanAmount', 0)))
                    e_dep = c6.number_input("보증금", value=safe_float(asset.get('tenantDeposit', 0)))
                
                e_mon_pay = 0
                e_growth = 0
                if a_type == 'PENSION':
                    e_mon_pay = c4.number_input("월 수령액(원)", value=safe_float(asset.get('expectedMonthlyPayout', 0)))
                    e_growth = c3.number_input("매년 증가율(%)", value=safe_float(asset.get('annualGrowthRate', 0)))

                st.caption("매각 처리")
                c_d1, c_d2 = st.columns(2)
                e_disp_d = c_d1.text_input("매각일 (YYYY-MM-DD)", value=disp_date)
                e_disp_p = c_d2.number_input("매각금액", value=disp_price)
                
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

                    st.success("저장됨")
                    st.rerun()

            if not is_adj:
                st.markdown("-`--")
                # 폼(form) 밖에서 버튼을 만들어야 바로 동작합니다.
                col_del_1, col_del_2 = st.columns([4, 1])
                with col_del_2:
                    if st.button("🗑️ 삭제", key=f"del_btn_{asset['id']}", type="primary", help="이 자산을 영구적으로 삭제합니다."):
                        st.session_state['expanded_account'] = asset.get('accountName')                        
                        # 1. 자산 리스트에서 해당 ID를 가진 항목 제외 (삭제)
                        st.session_state.assets = [a for a in st.session_state.assets if a['id'] != asset['id']]
                        
                        # 2. 주식일 경우, 계좌 총액 잔고 재계산 (보정 항목 업데이트)
                        if asset['type'] == 'STOCK':
                            recalculate_account_balance(asset.get('accountName'))
                            
                        st.toast("자산이 삭제되었습니다.")
                        st.rerun()                    


# -----------------------------------------------------------------------------------------------------
# [초기화]
# -----------------------------------------------------------------------------------------------------
if 'assets' not in st.session_state:
    data, config = load_data()
    st.session_state.assets = [parse_asset_details(a) for a in data]
    st.session_state.settings = config

assets = st.session_state.assets
load_css()


# -----------------------------------------------------------------------------------------------------
# [사이드바]
# -----------------------------------------------------------------------------------------------------
with st.sidebar:
    st.title("💼 My Asset Manager")
    st.markdown("---")
    menu_keys = ['REAL_ESTATE', 'STOCK', 'PENSION', 'SAVINGS', 'PHYSICAL', 'ETC']
    menu_labels = [TYPE_LABEL_MAP[k] for k in menu_keys]
    menu_items = ["📊 대시보드"] + menu_labels + ["⚙️ 설정"]
    menu = st.radio("메뉴 이동", menu_items)
    
    st.markdown("---")
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        data, config = load_data()
        st.session_state.assets = [parse_asset_details(a) for a in data]
        st.rerun()

    if st.button("💾 저장하기", type="primary"):
        to_save = []
        for a in st.session_state.assets:
            copy_a = a.copy()
            if a['type'] == 'REAL_ESTATE':
                copy_a['detail1'] = 'OWNED' if a.get('isOwned') else 'RENTED'
                copy_a['detail2'] = 'HAS_TENANT' if a.get('hasTenant') else 'NO_TENANT'
                copy_a['detail3'] = a.get('tenantDeposit')
                copy_a['detail4'] = a.get('address')
                copy_a['detail5'] = a.get('loanAmount')
            elif a['type'] == 'STOCK':
                copy_a['detail1'] = a.get('accountName')
                copy_a['detail2'] = a.get('currency')
            elif a['type'] == 'PENSION':
                copy_a['detail1'] = a.get('pensionType')
                copy_a['detail2'] = a.get('expectedStartYear')
                copy_a['detail3'] = a.get('expectedMonthlyPayout')
                copy_a['detail4'] = a.get('expectedEndYear')
                copy_a['detail5'] = a.get('annualGrowthRate')
            to_save.append(copy_a)
        if save_data(to_save, st.session_state.settings):
            st.success("저장되었습니다.")
        else:
            st.error("저장 실패")

# -----------------------------------------------------------------------------------------------------
# 1. 대시보드
# -----------------------------------------------------------------------------------------------------
if menu == "📊 대시보드":
    st.title("📊 통합 자산 대시보드")
    total_asset = 0
    total_liab = 0
    for a in assets:
        if a.get('disposalDate'): continue
        val = safe_float(a.get('currentValue'))
        total_asset += val
        if a['type'] == 'REAL_ESTATE':
            total_liab += safe_float(a.get('loanAmount'))
            total_liab += safe_float(a.get('tenantDeposit'))
    net_worth = total_asset - total_liab
    
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(render_kpi_card_html("💰 총 자산", format_money(total_asset)), unsafe_allow_html=True)
    with c2: st.markdown(render_kpi_card_html("📉 총 부채", format_money(total_liab), "#e03131"), unsafe_allow_html=True)
    with c3: st.markdown(render_kpi_card_html("💎 순자산", format_money(net_worth), "#1c7ed6"), unsafe_allow_html=True)
    
    st.divider()
    if assets:
        df_chart = pd.DataFrame(assets)
        df_chart = df_chart[df_chart['disposalDate'].isin([None, ""])]
        if not df_chart.empty:
            st.subheader("📊 자산 비중")
            grp = df_chart.groupby('type')['currentValue'].sum().reset_index()
            grp['label'] = grp['type'].map(TYPE_LABEL_MAP)
            fig_pie = px.pie(grp, values='currentValue', names='label', color='type', color_discrete_map=COLOR_MAP, hole=0.4)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📈 자산 성장 추이 (최근 10년)")
            # 대시보드는 전체(10년) 기준
            df_hist = generate_history_df(assets) 
            if not df_hist.empty:
                df_hist['value_man'] = df_hist['value'] / 10000
                df_area = df_hist.groupby(['date', 'type'])['value_man'].sum().reset_index()
                df_area['label'] = df_area['type'].map(TYPE_LABEL_MAP)
                fig_area = px.area(df_area, x='date', y='value_man', color='label', 
                                   color_discrete_map={v: COLOR_MAP[k] for k, v in TYPE_LABEL_MAP.items()},
                                   labels={'value_man': '가치(만원)'})
                
                # [수정] 대시보드 차트도 가독성 개선
                fig_area.update_layout(
                    hovermode="x unified",
                    xaxis=dict(nticks=20, tickformat="%y.%m.%d")
                )
                st.plotly_chart(fig_area, use_container_width=True)

# -----------------------------------------------------------------------------------------------------
# 2. 자산별 
# -----------------------------------------------------------------------------------------------------
elif menu in TYPE_LABEL_MAP.values():
    target_type = [k for k, v in TYPE_LABEL_MAP.items() if v == menu][0]
    st.title(menu)
    
    view_mode = "계좌별 보기"
    if target_type == 'STOCK':
        view_mode = st.radio("보기 모드", ["계좌별 보기", "종목별 보기"], horizontal=True)
    
    my_assets = [a for a in assets if a['type'] == target_type]
    
    display_category_summary(menu, my_assets)

    if my_assets:
        # [수정] 상단 차트도 자산 유형별 기간(3년/10년) 적용
        df_hist = generate_history_df(my_assets, target_type)
        if not df_hist.empty:
            df_hist['value_man'] = df_hist['value'] / 10000
            
            if target_type == 'STOCK' and view_mode == "계좌별 보기":
                df_chart_grp = df_hist.groupby(['date', 'account'])['value_man'].sum().reset_index()
                fig = px.area(df_chart_grp, x='date', y='value_man', color='account', 
                              color_discrete_sequence=PASTEL_COLORS, labels={'value_man': '가치(만원)'})
            else:
                fig = px.area(df_hist, x='date', y='value_man', color='name', 
                              color_discrete_sequence=PASTEL_COLORS, labels={'value_man': '가치(만원)'})
                
            fig.update_layout(
                height=300, 
                margin=dict(t=0, b=0, l=0, r=0),
                hovermode="x unified",
                xaxis=dict(nticks=20, tickformat="%y.%m.%d")
            )
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
                    s = safe_int(p.get('expectedStartYear')) or 2060
                    e = safe_int(p.get('expectedEndYear')) or 9999
                    m = safe_float(p.get('expectedMonthlyPayout'))
                    rate = safe_float(p.get('annualGrowthRate', 0)) / 100.0
                    
                    if s <= y <= e:
                        elapsed = max(0, y - s)
                        adjusted_m = m * ((1 + rate) ** elapsed)
                        val_man = adjusted_m / 10000 
                        row[p['name']] = val_man
                        row['total'] += val_man
                data.append(row)
            df_sim = pd.DataFrame(data)
            fig_sim = px.bar(df_sim, x='age', y=[c for c in df_sim.columns if c not in ['age','total']], 
                             labels={'value':'월수령액(만원)'}, color_discrete_sequence=PASTEL_COLORS)
            fig_sim.update_layout(
                barmode='stack', 
                height=300,
                hovermode="x unified"
            )
            st.plotly_chart(fig_sim, use_container_width=True)

    with st.expander(f"➕ 신규 {menu.split()[1]} 추가"):
        with st.form("add_new"):
            c1, c2 = st.columns(2)
            n_name = c1.text_input("자산명")
            
            # [수정] 실물자산/주식은 수량/단가 입력
            if target_type in ['STOCK', 'PHYSICAL']:
                n_qty = c2.number_input("수량", min_value=0.0)
                n_price = st.number_input("단가", min_value=0.0)
                n_val = n_qty * n_price
            else:
                n_val = c2.number_input("현재가치/취득가", min_value=0)
                n_qty = 0
                n_price = 0
                
            n_date = st.date_input("취득일").strftime("%Y-%m-%d")
            
            n_acc = ""
            if target_type == 'STOCK':
                n_acc = st.text_input("계좌명")
            
            if st.form_submit_button("추가"):
                st.session_state['expanded_asset_id'] = asset['id']
                st.session_state['expanded_account'] = asset.get('accountName')

                new_a = {"id":str(uuid.uuid4()), "type":target_type, "name":n_name, "currentValue":n_val, 
                         "acquisitionPrice":n_val if n_price==0 else n_price, "acquisitionDate":n_date, "accountName":n_acc,
                         "quantity": n_qty,
                         "history":[{"date":n_date, "value":n_val, "price":n_price, "quantity":n_qty}]}
                st.session_state.assets.append(new_a)
                st.success("추가되었습니다.")
                st.rerun()

    st.divider()

    if target_type == 'STOCK' and view_mode == "계좌별 보기":
        accounts = list(set([a.get('accountName', '기타') for a in my_assets]))
        for acc in accounts:
            acc_assets = [a for a in my_assets if a.get('accountName') == acc]
            
            pure_stock_sum = sum([safe_float(a['currentValue']) for a in acc_assets if a.get('detail5') != 'BALANCE_ADJUSTMENT'])
            total_with_adj = sum([safe_float(a['currentValue']) for a in acc_assets])
            current_target = st.session_state.settings.get(f"ACC_TOTAL_{acc}", total_with_adj)

            is_acc_open    = (acc == st.session_state.get('expanded_account'))            

            with st.expander(f"📂 {acc} (현재 총액: {format_money(total_with_adj)})", expanded=is_acc_open):
                with st.form(f"acc_bal_{acc}"):
                    c1, c2    = st.columns([3, 1])
                    new_total = c1.number_input(f"'{acc}' 실제 계좌 총 평가액 입력", value=float(current_target))

                    if c2.form_submit_button("잔고 보정 실행"):
                        recalculate_account_balance(acc, new_total)
                        st.success("보정 완료")
                        st.rerun()
                
                st.markdown("---")
                for a in acc_assets:
                    is_adj = (a.get('detail5') == 'BALANCE_ADJUSTMENT')
                    prefix = "🔧 " if is_adj else ""

                    is_asset_open = (a['id'] == st.session_state.get('expanded_asset_id'))
                    with st.expander(f"{prefix}{a['name']} {format_money(safe_float(a['currentValue']))}", expanded=is_asset_open):
                        if is_adj: st.info("🔒 자동 계산된 보정 항목입니다.")
                        else     : render_asset_detail(a)
    else:
        for a in my_assets:
            val = safe_float(a['currentValue'])
            badges = []
            if a.get('disposalDate'): badges.append('<span class="badge badge-red">매각됨</span>')
            
            with st.expander(f"{a['name']} {format_money(val)}"):
                if badges: st.markdown(" ".join(badges), unsafe_allow_html=True)
                render_asset_detail(a)


# -----------------------------------------------------------------------------------------------------
# 설정
# -----------------------------------------------------------------------------------------------------
elif menu == "⚙️ 설정":
    st.title("⚙️ 설정")
    with st.form("settings_form"):
        st.subheader("기본 설정")
        current_age = st.number_input("현재 나이", value=int(st.session_state.settings.get('current_age', 40)))
        retirement_age = st.number_input("은퇴 목표 나이", value=int(st.session_state.settings.get('retirement_age', 60)))
        if st.form_submit_button("설정 적용"):
            st.session_state.settings['current_age'] = current_age
            st.session_state.settings['retirement_age'] = retirement_age
            st.success("설정이 적용되었습니다. (구글 시트에 반영하려면 사이드바의 '저장하기'를 눌러주세요)")
            st.rerun()
    st.info("💡 설정 값은 앱의 은퇴 시뮬레이션 등에 사용됩니다.")

