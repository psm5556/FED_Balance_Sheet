import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 페이지 설정
st.set_page_config(
    page_title="Fed 모니터링 대시보드",
    page_icon="📊",
    layout="wide"
)

# CSS 스타일링
st.markdown("""
<style>
    .dataframe {
        font-size: 16px;
        width: 100%;
    }
    .dataframe th {
        background-color: #2d2d2d;
        color: #ffffff;
        font-weight: bold;
        text-align: left;
        padding: 12px;
    }
    .dataframe td {
        padding: 12px;
        color: #ffffff;
        background-color: #1e1e1e;
    }
    .positive {
        color: #4ade80;
    }
    .negative {
        color: #f87171;
    }
    a {
        color: #64b5f6;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    div[data-testid="stDataFrame"] {
        background-color: #0e1117;
    }
</style>
""", unsafe_allow_html=True)

# FRED API 키
try:
    FRED_API_KEY = st.secrets.get("FRED_API_KEY", "")
except:
    FRED_API_KEY = ""

# ==================== 공통 함수 ====================

@st.cache_data(ttl=1800)  # 30분으로 캐시 시간 단축
def fetch_fred_data(series_id, api_key, limit=10, start_date=None, end_date=None):
    """FRED API에서 데이터 가져오기 - 항상 date 컬럼과 value 컬럼을 가진 DataFrame 반환"""
    if not api_key:
        return None
    
    url = f"https://api.stlouisfed.org/fred/series/observations"
    
    if start_date and end_date:
        params = {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": start_date,
            "observation_end": end_date,
            "sort_order": "desc"  # 최신 데이터 우선
        }
    else:
        # 날짜 범위가 지정되지 않은 경우에도 최신 데이터 확보
        # 분기별 데이터도 고려하여 더 긴 기간 조회 (5년)
        default_end = datetime.now().strftime('%Y-%m-%d')
        default_start = (datetime.now() - timedelta(days=1825)).strftime('%Y-%m-%d')  # 5년으로 확대
        params = {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
            "observation_start": default_start,
            "observation_end": default_end
        }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "observations" in data and len(data["observations"]) > 0:
                df = pd.DataFrame(data["observations"])
                
                # date 컬럼 확인 및 변환
                if "date" not in df.columns:
                    st.error(f"시리즈 {series_id}: 'date' 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {df.columns.tolist()}")
                    return None
                
                # 날짜 변환
                try:
                    df["date"] = pd.to_datetime(df["date"])
                except Exception as e:
                    st.error(f"시리즈 {series_id}: 날짜 변환 오류 - {e}")
                    return None
                
                # value 컬럼 확인 및 변환
                if "value" not in df.columns:
                    st.error(f"시리즈 {series_id}: 'value' 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {df.columns.tolist()}")
                    return None
                
                df["value"] = pd.to_numeric(df["value"], errors="coerce")
                
                # 결측치 제거
                df = df.dropna(subset=['value'])
                
                if len(df) == 0:
                    st.warning(f"시리즈 {series_id}: 유효한 데이터가 없습니다.")
                    return None
                
                # 항상 date 컬럼을 유지하고 정렬 (최신순)
                df = df[['date', 'value']].sort_values('date', ascending=False)
                
                return df
            else:
                st.warning(f"시리즈 {series_id}: 데이터가 비어있습니다.")
                return None
        else:
            st.error(f"시리즈 {series_id}: API 요청 실패 (상태 코드: {response.status_code})")
            return None
    except requests.exceptions.Timeout:
        st.error(f"시리즈 {series_id}: 요청 시간 초과")
        return None
    except Exception as e:
        st.error(f"시리즈 {series_id}: 데이터 가져오기 오류 - {str(e)}")
        return None
    
    return None

# ==================== 대차대조표 관련 ====================

SERIES_INFO = {
    "총자산 (Total Assets)": {
        "id": "WALCL",
        "highlight": True,
        "category": "자산 (Assets)",
        "description": "연준의 전체 자산 규모",
        "liquidity_impact": "증가 시 시장 유동성 ↑",
        "order": 1,
        "show_chart": True
    },
    "연준 보유 증권 (Securities Held)": {
        "id": "WSHOSHO",
        "highlight": False,
        "category": "자산 (Assets)",
        "description": "연준이 보유한 국채 및 MBS",
        "liquidity_impact": "증가 시 시장 유동성 ↑",
        "order": 2,
        "show_chart": False
    },
    "SRF (상설레포)": {
        "id": "RPONTSYD",
        "highlight": True,
        "category": "자산 (Assets)",
        "description": "은행에 제공하는 단기 대출",
        "liquidity_impact": "증가 시 은행 유동성 ↑",
        "order": 3,
        "show_chart": True
    },
    "대출 (Loans)": {
        "id": "WLCFLPCL",
        "highlight": False,
        "category": "자산 (Assets)",
        "description": "연준의 금융기관 대출",
        "liquidity_impact": "증가 시 시장 유동성 ↑",
        "order": 4,
        "show_chart": False
    },
    "  ㄴ Primary Credit": {
        "id": "WLCFLPCL",
        "highlight": True,
        "category": "자산 (Assets)",
        "description": "할인창구 1차 신용대출",
        "liquidity_impact": "증가 시 은행 유동성 ↑",
        "order": 5,
        "show_chart": True
    },
    "  ㄴ Secondary Credit": {
        "id": "WLCFLSCL",
        "highlight": False,
        "category": "자산 (Assets)",
        "description": "할인창구 2차 신용대출",
        "liquidity_impact": "증가 시 은행 유동성 ↑",
        "order": 6,
        "show_chart": False
    },
    "  ㄴ Seasonal Credit": {
        "id": "WLCFLSECL",
        "highlight": False,
        "category": "자산 (Assets)",
        "description": "할인창구 계절성 신용대출",
        "liquidity_impact": "증가 시 은행 유동성 ↑",
        "order": 7,
        "show_chart": False
    },
    "지급준비금 (Reserve Balances)": {
        "id": "WRESBAL",
        "highlight": True,
        "category": "부채 (Liabilities)",
        "description": "은행들이 연준에 예치한 자금",
        "liquidity_impact": "증가 시 은행 유동성 ↑",
        "order": 8,
        "show_chart": True
    },
    "TGA (재무부 일반계정)": {
        "id": "WTREGEN",
        "highlight": True,
        "category": "부채 (Liabilities)",
        "description": "미 재무부의 연준 예금",
        "liquidity_impact": "증가 시 시장 유동성 ↓",
        "order": 9,
        "show_chart": True
    },
    "RRP (역레포)": {
        "id": "RRPONTSYD",
        "highlight": True,
        "category": "부채 (Liabilities)",
        "description": "MMF 등의 초단기 자금 흡수",
        "liquidity_impact": "증가 시 시장 유동성 ↓",
        "order": 10,
        "show_chart": True
    },
    "MMF (Money Market Funds)": {
        "id": "MMMFFAQ027S",
        "highlight": True,
        "category": "부채 (Liabilities)",
        "description": "머니마켓펀드 총 자산 (분기별)",
        "liquidity_impact": "증가 시 현금 보유 선호 ↑",
        "order": 11,
        "show_chart": True,
        "is_quarterly": True
    },
    "Retail MMF": {
        "id": "WRMFNS",
        "highlight": False,
        "category": "부채 (Liabilities)",
        "description": "개인투자자용 머니마켓펀드",
        "liquidity_impact": "증가 시 현금 보유 선호 ↑",
        "order": 12,
        "show_chart": False
    },
    "총부채 (Total Liabilities)": {
        "id": "WALCL",
        "highlight": False,
        "category": "부채 (Liabilities)",
        "description": "연준의 전체 부채 규모",
        "liquidity_impact": "구조 변화가 유동성에 영향",
        "order": 13,
        "show_chart": False
    }
}

def format_number(value):
    """숫자를 $M 단위로 포맷"""
    if pd.isna(value):
        return "N/A"
    return f"{value:,.0f}"

def format_change(change):
    """변화량을 화살표와 함께 포맷"""
    if pd.isna(change):
        return "N/A"
    
    if change > 0:
        return f"▲ {abs(change):,.0f}"
    elif change < 0:
        return f"▼ {abs(change):,.0f}"
    else:
        return f"{change:,.0f}"

def get_fred_link(series_id):
    """FRED 시리즈 링크 생성"""
    return f"https://fred.stlouisfed.org/series/{series_id}"

def create_balance_sheet_chart(df, title, series_id):
    """대차대조표 차트 생성"""
    if df is None or len(df) == 0:
        return None
    
    # DataFrame을 복사하여 작업
    df_work = df.copy()
    
    # 인덱스가 DatetimeIndex인 경우 리셋
    if isinstance(df_work.index, pd.DatetimeIndex):
        df_work = df_work.reset_index()
        if 'index' in df_work.columns:
            df_work = df_work.rename(columns={'index': 'date'})
    
    # date 컬럼이 있는지 확인
    if 'date' not in df_work.columns:
        # date 컬럼이 없으면 인덱스를 date로 사용
        df_work['date'] = df_work.index
    
    # 정렬 (시간순)
    df_sorted = df_work.sort_values('date')
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_sorted['date'],
        y=df_sorted['value'],
        mode='lines+markers',
        name=title,
        line=dict(color='#64b5f6', width=2),
        marker=dict(size=6, color='#64b5f6'),
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>값: $%{y:,.0f}M<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(
            text=f"{title} - 최근 추이",
            font=dict(size=18, color='white')
        ),
        xaxis=dict(
            title="날짜",
            gridcolor='#2d2d2d',
            color='white'
        ),
        yaxis=dict(
            title="금액 ($M)",
            gridcolor='#2d2d2d',
            color='white'
        ),
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='white'),
        hovermode='x unified',
        height=400
    )
    
    return fig

# ==================== 금리 스프레드 관련 ====================

SPREADS = {
    "SOFR-IORB": {
        "name": "SOFR - IORB",
        "series": ["SOFR", "IORB"],
        "multiplier": 1000,
        "threshold_min": 0,
        "threshold_max": 10,
        "description": "은행간 신뢰도 및 유동성 선호 지표",
        "normal_range": "0 ~ +10bp",
        "interpretation": "양수: 은행간 거래 활발 (정상) / 0에 근접 또는 음수: 은행들이 서로를 포기하고 연준 예치 선호 (신뢰 위기)",
        "signals": {
            "crisis": (float('-inf'), 0, "🚨 은행간 신뢰 붕괴 - 연준 예치 선호"),
            "warning": (0, 2, "⚠️ 은행간 거래 위축 - 주의 필요"),
            "normal": (2, 10, "✅ 정상 - 은행간 거래 활발"),
            "tight": (10, float('inf'), "📈 레포시장 타이트 - 담보 수요 증가")
        }
    },
    "EFFR-IORB": {
        "name": "EFFR - IORB",
        "series": ["EFFR", "IORB"],
        "multiplier": 1000,
        "threshold_min": -10,
        "threshold_max": 10,
        "description": "초단기 자금시장 유동성 지표",
        "normal_range": "-10 ~ +10bp",
        "interpretation": "양수: 준비금 부족/유동성 타이트 / 음수: 초과 준비금/유동성 풍부",
        "signals": {
            "tight": (10, float('inf'), "⚠️ 초단기 유동성 타이트 - 준비금 부족"),
            "normal": (-10, 10, "✅ 정상 범위 (정책 운용 변동 포함)"),
            "loose": (float('-inf'), -10, "💧 초과 준비금 (유동성 풍부)")
        }
    },
    "SOFR-RRP": {
        "name": "SOFR - RRP",
        "series": ["SOFR", "RRPONTSYAWARD"],
        "multiplier": 1000,
        "threshold_min": 0,
        "threshold_max": 10,
        "description": "레포 시장 긴장도 지표",
        "normal_range": "0 ~ +10bp",
        "interpretation": "양수: 정상 / >10bp: 담보 부족/레포시장 긴장 / 음수: 비정상",
        "signals": {
            "stress": (10, float('inf'), "⚠️ 레포시장 스트레스 - 담보 부족"),
            "normal": (0, 10, "✅ 보통 변동"),
            "abnormal": (float('-inf'), 0, "🔍 비정상 - 데이터/정책 확인 필요")
        }
    },
    "DGS3MO-EFFR": {
        "name": "3M Treasury - EFFR",
        "series": ["DGS3MO", "EFFR"],
        "multiplier": 100,
        "threshold_min": -20,
        "threshold_max": 20,
        "description": "단기 금리 기대 및 정책 방향 신호",
        "normal_range": "-20 ~ +20bp",
        "interpretation": "<-20bp: 금리 인하 예상 / 중립: 균형 / >20bp: 금리 인상 기대",
        "signals": {
            "easing": (float('-inf'), -20, "🔽 금리 인하 예상 (완화 기대)"),
            "neutral": (-20, 20, "✅ 중립 (명확한 기대 신호 없음)"),
            "tightening": (20, float('inf'), "🔼 금리 인상 기대 (긴축 신호)")
        }
    },
    "DGS10-DGS2": {
        "name": "10Y - 2Y Yield Curve",
        "series": ["DGS10", "DGS2"],
        "multiplier": 100,
        "threshold_min": 0,
        "threshold_max": 50,
        "description": "경기 사이클 및 경기침체 예측 지표 (2s10s)",
        "normal_range": "0 ~ +50bp",
        "interpretation": "음수(역전): 경기침체 신호 / 0~50bp: 정상 / >50bp: 가파른 성장 기대",
        "signals": {
            "severe_inversion": (float('-inf'), -50, "🚨 강한 침체 리스크 (심층 분석 권장)"),
            "mild_inversion": (-50, 0, "⚠️ 곡선 역전 - 경기침체 경고"),
            "normal": (0, 50, "✅ 정상 (완만한 우상향)"),
            "steep": (50, float('inf'), "📈 가파른 곡선 (강한 성장/인플레 기대)")
        }
    },
    "DGS10-DGS3MO": {
        "name": "10Y - 3M Yield Curve",
        "series": ["DGS10", "DGS3MO"],
        "multiplier": 100,
        "threshold_min": 0,
        "threshold_max": 100,
        "description": "가장 강력한 경기침체 선행 지표",
        "normal_range": "0 ~ +100bp",
        "interpretation": "<-50bp: 매우 강한 침체 신호 / 0~100bp: 정상 / >100bp: 장단기 프리미엄",
        "signals": {
            "strong_recession": (float('-inf'), -50, "🚨 매우 강한 침체 선행 신호"),
            "recession_warning": (-50, 0, "⚠️ 침체 우려 레벨"),
            "normal": (0, 100, "✅ 정상-완만"),
            "steep": (100, float('inf'), "📈 장단기 프리미엄 (성장/인플레 기대)")
        }
    },
    "STLFSI4": {
        "name": "금융 스트레스 인덱스",
        "series": ["STLFSI4"],
        "multiplier": 1,
        "threshold_min": -0.5,
        "threshold_max": 0.5,
        "description": "세인트루이스 연준 금융 스트레스 지표",
        "normal_range": "-0.5 ~ +0.5",
        "interpretation": "0 기준: 평균 스트레스 / 양수: 스트레스 증가 / 음수: 스트레스 감소",
        "signals": {
            "severe_stress": (1.5, float('inf'), "🚨 심각한 금융 스트레스"),
            "elevated_stress": (0.5, 1.5, "⚠️ 높은 스트레스"),
            "normal": (-0.5, 0.5, "✅ 정상 범위"),
            "low_stress": (float('-inf'), -0.5, "💚 낮은 스트레스")
        },
        "is_single_series": True
    }
}

def calculate_spread(spread_info, api_key, start_date, end_date=None):
    """스프레드 계산"""
    if spread_info.get('is_single_series', False):
        series_id = spread_info['series'][0]
        df = fetch_fred_data(series_id, api_key, limit=None, start_date=start_date, end_date=end_date)
        
        if df is None:
            return None, None, None
        
        # date를 인덱스로 설정
        df = df.set_index('date')
        
        df['spread'] = df['value'] * spread_info['multiplier']
        df['ma_4w'] = df['spread'].rolling(window=4, min_periods=1).mean()
        
        latest_value = df['spread'].iloc[0] if len(df) > 0 else None  # 최신값은 첫 행
        
        df_components = df[['value']].copy()
        df_components.columns = [series_id]
        
        return df, latest_value, df_components
    
    series1_id, series2_id = spread_info['series']
    
    df1 = fetch_fred_data(series1_id, api_key, limit=None, start_date=start_date, end_date=end_date)
    df2 = fetch_fred_data(series2_id, api_key, limit=None, start_date=start_date, end_date=end_date)
    
    if df1 is None or df2 is None:
        return None, None, None
    
    # date를 인덱스로 설정
    df1 = df1.set_index('date')
    df2 = df2.set_index('date')
    
    # 두 데이터프레임 병합
    df = df1.join(df2, how='outer', rsuffix='_2')
    df.columns = [series1_id, series2_id]
    df = df.ffill().dropna()
    df = df.sort_index(ascending=False)  # 최신순 정렬
    
    df['spread'] = (df[series1_id] - df[series2_id]) * spread_info['multiplier']
    
    latest_value = df['spread'].iloc[0] if len(df) > 0 else None  # 최신값은 첫 행
    
    return df, latest_value, df[[series1_id, series2_id]]

def get_signal_status(value, signals):
    """신호 기반 상태 판단"""
    for signal_name, (min_val, max_val, message) in signals.items():
        if min_val <= value < max_val:
            return message
    return "📊 데이터 확인 필요"

def create_spread_chart(df, spread_name, spread_info, latest_value):
    """스프레드 차트 생성"""
    # 시간순 정렬을 위해 복사본 생성
    df_sorted = df.sort_index(ascending=True)
    
    fig = go.Figure()
    
    if spread_info.get('is_single_series', False):
        fig.add_trace(go.Scatter(
            x=df_sorted.index,
            y=df_sorted['spread'],
            mode='lines',
            name='STLFSI4',
            line=dict(color='#2E86DE', width=2)
        ))
        
        if 'ma_4w' in df_sorted.columns:
            fig.add_trace(go.Scatter(
                x=df_sorted.index,
                y=df_sorted['ma_4w'],
                mode='lines',
                name='4주 이동평균',
                line=dict(color='#FF6B6B', width=2, dash='dash')
            ))
        
        fig.add_hline(
            y=0,
            line_dash="dash",
            line_color="gray",
            opacity=0.5,
            annotation_text="평균 수준"
        )
    else:
        fig.add_trace(go.Scatter(
            x=df_sorted.index,
            y=df_sorted['spread'],
            mode='lines',
            name='Spread',
            line=dict(color='#2E86DE', width=2)
        ))
    
    if 'signals' in spread_info:
        colors_map = {
            'normal': 'green', 'neutral': 'green', 'mild_inversion': 'orange',
            'recession_warning': 'orange', 'easing': 'lightblue', 'tightening': 'pink',
            'stress': 'red', 'severe_inversion': 'red', 'strong_recession': 'red',
            'tight': 'orange', 'abnormal': 'gray', 'loose': 'lightgreen',
            'steep': 'lightblue', 'severe_stress': 'red', 'elevated_stress': 'orange',
            'low_stress': 'lightgreen', 'crisis': 'red', 'warning': 'orange'
        }
        
        for signal_name, (min_val, max_val, message) in spread_info['signals'].items():
            if min_val != float('-inf') and max_val != float('inf'):
                color = colors_map.get(signal_name, 'gray')
                fig.add_hrect(
                    y0=min_val, y1=max_val, fillcolor=color, opacity=0.1,
                    line_width=0,
                    annotation_text=message.split(' - ')[0] if ' - ' in message else message,
                    annotation_position="left"
                )
    
    y_axis_title = "Index Value" if spread_info.get('is_single_series', False) else "Basis Points (bp)"
    
    fig.update_layout(
        title=f"{spread_name} ({spread_info['normal_range']})",
        xaxis_title="날짜",
        yaxis_title=y_axis_title,
        hovermode='x unified',
        height=400,
        showlegend=True
    )
    
    return fig

def create_components_chart(df_components, series_ids):
    """구성 요소 차트 생성"""
    # 시간순 정렬
    df_sorted = df_components.sort_index(ascending=True)
    
    fig = go.Figure()
    
    colors = ['#EE5A6F', '#4ECDC4']
    for i, series in enumerate(series_ids):
        fig.add_trace(go.Scatter(
            x=df_sorted.index,
            y=df_sorted[series],
            mode='lines',
            name=series,
            line=dict(color=colors[i], width=2)
        ))
    
    fig.update_layout(
        title="구성 요소",
        xaxis_title="날짜",
        yaxis_title="Rate (%)",
        hovermode='x unified',
        height=300,
        showlegend=True
    )
    
    return fig

def get_fear_greed_index():
    """CNN Fear & Greed Index 가져오기"""
    try:
        # 방법 1: CNN API (새 엔드포인트)
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'fear_and_greed' in data:
                score = float(data['fear_and_greed']['score'])
                rating = data['fear_and_greed']['rating']
                
                # 상태에 따른 색상 및 이모지 설정
                if score >= 75:
                    status = "Extreme Greed"
                    color = "#16a34a"
                    emoji = "🤑"
                elif score >= 55:
                    status = "Greed"
                    color = "#22c55e"
                    emoji = "😊"
                elif score >= 45:
                    status = "Neutral"
                    color = "#eab308"
                    emoji = "😐"
                elif score >= 25:
                    status = "Fear"
                    color = "#f97316"
                    emoji = "😨"
                else:
                    status = "Extreme Fear"
                    color = "#dc2626"
                    emoji = "😱"
                
                return {
                    "score": score,
                    "status": status,
                    "rating": rating,
                    "color": color,
                    "emoji": emoji,
                    "source": "CNN API"
                }
    except Exception as e:
        pass
    
    try:
        # 방법 2: Alternative Fear and Greed API
        url = "https://api.alternative.me/fng/?limit=1"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data and len(data['data']) > 0:
                score = float(data['data'][0]['value'])
                
                # 상태 판단
                if score >= 75:
                    status = "Extreme Greed"
                    color = "#16a34a"
                    emoji = "🤑"
                elif score >= 55:
                    status = "Greed"
                    color = "#22c55e"
                    emoji = "😊"
                elif score >= 45:
                    status = "Neutral"
                    color = "#eab308"
                    emoji = "😐"
                elif score >= 25:
                    status = "Fear"
                    color = "#f97316"
                    emoji = "😨"
                else:
                    status = "Extreme Fear"
                    color = "#dc2626"
                    emoji = "😱"
                
                return {
                    "score": score,
                    "status": status,
                    "rating": data['data'][0]['value_classification'],
                    "color": color,
                    "emoji": emoji,
                    "source": "Crypto F&G (참고용)"
                }
    except Exception as e:
        pass
    
    # 방법 3: VIX 기반 계산
    try:
        df_vix = fetch_fred_data("VIXCLS", FRED_API_KEY, limit=1)
        
        if df_vix is not None and len(df_vix) > 0:
            vix_value = float(df_vix.iloc[0]["value"])
            
            # VIX 기반 Fear & Greed 점수 계산 (역관계)
            # VIX가 낮을수록 탐욕, 높을수록 공포
            if vix_value <= 12:
                score = 85
            elif vix_value <= 15:
                score = 75
            elif vix_value <= 20:
                score = 60
            elif vix_value <= 25:
                score = 50
            elif vix_value <= 30:
                score = 40
            elif vix_value <= 35:
                score = 30
            elif vix_value <= 40:
                score = 20
            else:
                score = 10
            
            # 상태 판단
            if score >= 75:
                status = "Extreme Greed"
                color = "#16a34a"
                emoji = "🤑"
            elif score >= 55:
                status = "Greed"
                color = "#22c55e"
                emoji = "😊"
            elif score >= 45:
                status = "Neutral"
                color = "#eab308"
                emoji = "😐"
            elif score >= 25:
                status = "Fear"
                color = "#f97316"
                emoji = "😨"
            else:
                status = "Extreme Fear"
                color = "#dc2626"
                emoji = "😱"
            
            return {
                "score": score,
                "status": status,
                "rating": f"VIX 기반 추정 (VIX: {vix_value:.2f})",
                "color": color,
                "emoji": emoji,
                "source": "VIX 기반 계산"
            }
    except Exception as e:
        st.error(f"모든 Fear & Greed 데이터 소스 실패: {e}")
    
    return None

def get_vix_index():
    """VIX 지수 가져오기"""
    try:
        df_vix = fetch_fred_data("VIXCLS", FRED_API_KEY, limit=1)
        
        if df_vix is not None and len(df_vix) > 0:
            vix_value = float(df_vix.iloc[0]["value"])
            
            # VIX 수준 판단
            if vix_value < 12:
                status = "매우 낮음"
                color = "#16a34a"
                emoji = "😌"
                description = "시장 매우 안정"
            elif vix_value < 20:
                status = "낮음"
                color = "#22c55e"
                emoji = "🙂"
                description = "시장 안정"
            elif vix_value < 30:
                status = "보통"
                color = "#eab308"
                emoji = "😐"
                description = "변동성 증가"
            elif vix_value < 40:
                status = "높음"
                color = "#f97316"
                emoji = "😰"
                description = "시장 불안"
            else:
                status = "매우 높음"
                color = "#dc2626"
                emoji = "🚨"
                description = "극심한 불안"
            
            return {
                "value": vix_value,
                "status": status,
                "color": color,
                "emoji": emoji,
                "description": description
            }
    except Exception as e:
        st.error(f"VIX 데이터 로딩 실패: {e}")
    
    return None

# ==================== 메인 앱 ====================

def main():
    st.title("📊 Fed 모니터링 통합 대시보드")
    
    # 캐시 초기화 버튼 추가
    col1, col2 = st.columns([6, 1])
    with col1:
        st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    with col2:
        if st.button("🔄 새로고침"):
            st.cache_data.clear()
            st.rerun()
    
    # API 키 확인
    if not FRED_API_KEY:
        st.warning("⚠️ FRED API 키가 설정되지 않았습니다. GitHub Secrets 또는 Streamlit Secrets에 FRED_API_KEY를 추가해주세요.")
        st.info("""
        **FRED API 키 발급:**
        https://fred.stlouisfed.org/docs/api/api_key.html 에서 무료로 발급받을 수 있습니다.
        
        **Streamlit Cloud Secrets 설정:**
        1. Streamlit Cloud 대시보드에서 앱 선택
        2. Settings → Secrets 메뉴 클릭
        3. `FRED_API_KEY = "your_api_key_here"` 형식으로 입력
        """)
        return
    
    # 메인 탭 생성
    tab1, tab2 = st.tabs(["💰 Fed Balance Sheet", "📈 금리 스프레드"])
    
    # ==================== Tab 1: Fed Balance Sheet ====================
    with tab1:
        st.header("Fed Balance Sheet: Weekly Changes (Unit: $M)")
        
        # 사이드바 설정 (Balance Sheet용)
        with st.sidebar:
            st.markdown("### 📅 조회 기간 설정 (Balance Sheet)")
            
            bs_date_mode = st.radio(
                "기간 선택 방식",
                ["빠른 선택", "직접 입력"],
                index=0,
                key="bs_date_mode"
            )
            
            if bs_date_mode == "빠른 선택":
                bs_period = st.selectbox(
                    "조회 기간",
                    ["1개월", "3개월", "6개월", "1년", "2년", "5년"],
                    index=3,
                    key="bs_period"
                )
                
                bs_period_map = {
                    "1개월": 30, "3개월": 90, "6개월": 180, 
                    "1년": 365, "2년": 730, "5년": 1825
                }
                
                bs_days = bs_period_map[bs_period]
                bs_start_date = (datetime.now() - timedelta(days=bs_days)).strftime('%Y-%m-%d')
                bs_end_date = datetime.now().strftime('%Y-%m-%d')
                
            else:
                col1, col2 = st.columns(2)
                
                with col1:
                    bs_start_date_input = st.date_input(
                        "시작 날짜",
                        value=datetime.now() - timedelta(days=365),
                        max_value=datetime.now(),
                        key="bs_start"
                    )
                
                with col2:
                    bs_end_date_input = st.date_input(
                        "종료 날짜",
                        value=datetime.now(),
                        max_value=datetime.now(),
                        key="bs_end"
                    )
                
                bs_start_date = bs_start_date_input.strftime('%Y-%m-%d')
                bs_end_date = bs_end_date_input.strftime('%Y-%m-%d')
        
        # 조회 기간 표시
        st.info(f"📅 **조회 기간**: {bs_start_date} ~ {bs_end_date}")
        
        with st.spinner("데이터를 불러오는 중..."):
            data_list = []
            chart_data = {}
            
            for name, info in SERIES_INFO.items():
                series_id = info["id"]
                highlight = info["highlight"]
                category = info["category"]
                description = info["description"]
                liquidity_impact = info["liquidity_impact"]
                order = info["order"]
                show_chart = info.get("show_chart", False)
                is_quarterly = info.get("is_quarterly", False)
                
                # 표용 데이터 - 최신 10개 데이터 가져오기
                df = fetch_fred_data(series_id, FRED_API_KEY, limit=10)
                
                if show_chart:
                    # 차트용 데이터는 설정된 조회기간 사용
                    df_chart = fetch_fred_data(series_id, FRED_API_KEY, limit=None, 
                                               start_date=bs_start_date, end_date=bs_end_date)
                    chart_data[name] = {"df": df_chart, "series_id": series_id}
                
                if df is not None and len(df) >= 2:
                    # 최신 데이터가 첫 번째 행
                    current_value = df.iloc[0]["value"]
                    previous_value = df.iloc[1]["value"]
                    change = current_value - previous_value
                    current_date = df.iloc[0]["date"]
                    previous_date = df.iloc[1]["date"]
                    
                    # 분기별 데이터 표시
                    display_name = name
                    if is_quarterly:
                        display_name = f"{name} 🔶"
                        current_date_str = current_date.strftime('%Y-Q%q')
                        previous_date_str = previous_date.strftime('%Y-Q%q')
                        # 분기 표시를 위한 계산
                        current_quarter = (current_date.month - 1) // 3 + 1
                        previous_quarter = (previous_date.month - 1) // 3 + 1
                        current_date_str = f"{current_date.year}-Q{current_quarter}"
                        previous_date_str = f"{previous_date.year}-Q{previous_quarter}"
                    else:
                        current_date_str = current_date.strftime('%Y-%m-%d')
                        previous_date_str = previous_date.strftime('%Y-%m-%d')
                    
                    data_list.append({
                        "분류": category,
                        "항목": display_name,
                        "설명": description,
                        "현재 값": format_number(current_value),
                        "이전 값": format_number(previous_value),
                        "변화": format_change(change),
                        "유동성 영향": liquidity_impact,
                        "출처": f'<a href="{get_fred_link(series_id)}" target="_blank">🔗 {series_id}</a>',
                        "하이라이트": highlight,
                        "변화_수치": change,
                        "순서": order,
                        "현재_날짜": current_date_str,
                        "이전_날짜": previous_date_str
                    })
                else:
                    display_name = name
                    if is_quarterly:
                        display_name = f"{name} 🔶"
                    
                    data_list.append({
                        "분류": category,
                        "항목": display_name,
                        "설명": description,
                        "현재 값": "N/A",
                        "이전 값": "N/A",
                        "변화": "N/A",
                        "유동성 영향": liquidity_impact,
                        "출처": f'<a href="{get_fred_link(series_id)}" target="_blank">🔗 {series_id}</a>',
                        "하이라이트": highlight,
                        "변화_수치": 0,
                        "순서": order,
                        "현재_날짜": "N/A",
                        "이전_날짜": "N/A"
                    })
        
        if data_list:
            df_display = pd.DataFrame(data_list)
            df_display = df_display.sort_values(by=["순서"])
            
            # 데이터 업데이트 안내
            if "현재_날짜" in df_display.columns and df_display["현재_날짜"].iloc[0] != "N/A":
                st.info(f"ℹ️ **데이터 기준**: 대부분의 항목이 {df_display['현재_날짜'].iloc[0]} 기준으로 업데이트되었습니다. (각 항목의 정확한 날짜는 표의 날짜 칼럼 참조)")
            
            st.markdown("### 📊 Fed Balance Sheet 데이터")
            st.caption("🔶 = 분기별 업데이트 항목 (다른 항목은 주간 업데이트)")
            
            # HTML 테이블
            html_table = "<table style='width:100%; border-collapse: collapse;'>"
            html_table += "<thead><tr style='background-color: #2d2d2d;'>"
            html_table += "<th style='padding: 12px; text-align: left; color: white; width: 6%;'>분류</th>"
            html_table += "<th style='padding: 12px; text-align: left; color: white; width: 14%;'>항목</th>"
            html_table += "<th style='padding: 12px; text-align: left; color: white; width: 12%;'>설명</th>"
            html_table += "<th style='padding: 12px; text-align: center; color: white; width: 8%;'>현재 날짜</th>"
            html_table += "<th style='padding: 12px; text-align: right; color: white; width: 10%;'>현재 값</th>"
            html_table += "<th style='padding: 12px; text-align: center; color: white; width: 8%;'>이전 날짜</th>"
            html_table += "<th style='padding: 12px; text-align: right; color: white; width: 10%;'>이전 값</th>"
            html_table += "<th style='padding: 12px; text-align: right; color: white; width: 10%;'>변화</th>"
            html_table += "<th style='padding: 12px; text-align: left; color: white; width: 14%;'>유동성 영향</th>"
            html_table += "<th style='padding: 12px; text-align: center; color: white; width: 8%;'>출처</th>"
            html_table += "</tr></thead><tbody>"
            
            current_category = None
            for _, row in df_display.iterrows():
                bg_color = "#3d3d00" if row["하이라이트"] else "#1e1e1e"
                border_style = "border: 2px solid #ffd700;" if row["하이라이트"] else ""
                indent_style = "padding-left: 30px;" if row["항목"].startswith("  ㄴ") else ""
                
                if current_category != row["분류"]:
                    if current_category is not None:
                        html_table += "<tr style='height: 10px; background-color: #0e1117;'><td colspan='10'></td></tr>"
                    current_category = row["분류"]
                
                change_text = row["변화"]
                if "▲" in change_text:
                    change_color = "color: #4ade80;"
                elif "▼" in change_text:
                    change_color = "color: #f87171;"
                else:
                    change_color = "color: white;"
                
                liquidity_text = row["유동성 영향"]
                if "↑" in liquidity_text and "유동성" in liquidity_text:
                    liquidity_color = "color: #4ade80;"
                elif "↓" in liquidity_text:
                    liquidity_color = "color: #f87171;"
                else:
                    liquidity_color = "color: #fbbf24;"
                
                html_table += f"<tr style='background-color: {bg_color}; {border_style}'>"
                html_table += f"<td style='padding: 12px; color: #9ca3af; font-weight: 600; font-size: 13px;'>{row['분류']}</td>"
                html_table += f"<td style='padding: 12px; {indent_style} color: white; font-size: 14px;'>{row['항목']}</td>"
                html_table += f"<td style='padding: 12px; color: #d1d5db; font-size: 13px;'>{row['설명']}</td>"
                html_table += f"<td style='padding: 12px; text-align: center; color: #60a5fa; font-size: 12px;'>{row['현재_날짜']}</td>"
                html_table += f"<td style='padding: 12px; text-align: right; color: white; font-size: 14px;'>{row['현재 값']}</td>"
                html_table += f"<td style='padding: 12px; text-align: center; color: #9ca3af; font-size: 12px;'>{row['이전_날짜']}</td>"
                html_table += f"<td style='padding: 12px; text-align: right; color: white; font-size: 14px;'>{row['이전 값']}</td>"
                html_table += f"<td style='padding: 12px; text-align: right; {change_color} font-size: 14px;'><b>{change_text}</b></td>"
                html_table += f"<td style='padding: 12px; {liquidity_color} font-size: 13px;'><b>{liquidity_text}</b></td>"
                html_table += f"<td style='padding: 12px; text-align: center; font-size: 13px;'>{row['출처']}</td>"
                html_table += "</tr>"
            
            html_table += "</tbody></table>"
            st.markdown(html_table, unsafe_allow_html=True)
            
            # 차트 섹션
            st.markdown("---")
            st.markdown(f"### 📈 주요 항목 추이 ({bs_start_date} ~ {bs_end_date})")
            
            chart_names = list(chart_data.keys())
            for i in range(0, len(chart_names), 2):
                cols = st.columns(2)
                
                for j, col in enumerate(cols):
                    if i + j < len(chart_names):
                        name = chart_names[i + j]
                        data = chart_data[name]
                        
                        with col:
                            fig = create_balance_sheet_chart(data["df"], name, data["series_id"])
                            if fig:
                                st.plotly_chart(fig, use_container_width=True)
            
            # 추가 정보
            st.markdown("---")
            with st.expander("📌 항목별 상세 설명 보기"):
                st.markdown("""
                #### 💰 자산 항목 (Assets)
                - **총자산**: 연준 대차대조표의 전체 자산 규모. 증가하면 통화량 증가로 시장 유동성이 높아집니다.
                - **연준 보유 증권**: 국채와 주택저당증권(MBS)을 매입하여 시장에 유동성을 공급합니다. 양적완화(QE)의 핵심 지표입니다.
                - **SRF (상설레포)**: 은행이 담보를 제공하고 연준으로부터 단기 자금을 조달하는 시설입니다.
                - **대출**: 연준이 금융기관에 제공하는 긴급 유동성입니다.
                
                #### 💳 부채 항목 (Liabilities)
                - **지급준비금**: 은행들이 연준에 예치한 초과 준비금입니다.
                - **TGA (재무부 일반계정)**: 미 재무부가 연준에 보관하는 현금입니다.
                - **RRP (역레포)**: 머니마켓펀드 등이 초단기로 연준에 자금을 예치하는 제도입니다.
                - **MMF (Money Market Funds)**: 머니마켓펀드의 총 자산 규모입니다. *분기별 업데이트 데이터*로 다른 항목과 업데이트 주기가 다릅니다.
                - **Retail MMF**: 개인투자자용 머니마켓펀드입니다.
                
                **참고**: MMF는 Fed의 직접적인 부채는 아니지만, RRP의 주요 참여자이므로 시장 유동성을 파악하는 중요한 지표입니다.
                """)
        
        st.caption("데이터 출처: Federal Reserve Economic Data (FRED)")
    
    # ==================== Tab 2: 금리 스프레드 ====================
    with tab2:
        st.header("금리 스프레드 모니터링")
        
        # 사이드바 설정 (탭 안에서)
        with st.sidebar:
            st.markdown("### 📅 조회 기간 설정")
            
            date_mode = st.radio(
                "기간 선택 방식",
                ["빠른 선택", "직접 입력"],
                index=0,
                key="spread_date_mode"
            )
            
            if date_mode == "빠른 선택":
                period = st.selectbox(
                    "조회 기간",
                    ["1개월", "3개월", "6개월", "1년", "2년", "5년", "10년", "전체"],
                    index=3,
                    key="spread_period"
                )
                
                period_map = {
                    "1개월": 30, "3개월": 90, "6개월": 180, "1년": 365,
                    "2년": 730, "5년": 1825, "10년": 3650, "전체": 365 * 20
                }
                
                start_date = (datetime.now() - timedelta(days=period_map[period])).strftime('%Y-%m-%d')
                end_date = datetime.now().strftime('%Y-%m-%d')
                
            else:
                col1, col2 = st.columns(2)
                
                with col1:
                    start_date_input = st.date_input(
                        "시작 날짜",
                        value=datetime.now() - timedelta(days=365),
                        max_value=datetime.now(),
                        key="spread_start"
                    )
                
                with col2:
                    end_date_input = st.date_input(
                        "종료 날짜",
                        value=datetime.now(),
                        max_value=datetime.now(),
                        key="spread_end"
                    )
                
                start_date = start_date_input.strftime('%Y-%m-%d')
                end_date = end_date_input.strftime('%Y-%m-%d')
            st.markdown("---")
            st.markdown("### 📊 스프레드 정보")
            st.markdown("""
            **주요 스프레드:**
            
            **1. SOFR - IORB**: 은행간 신뢰도  
            - SOFR: 은행 간 초단기 자금 거래 금리 → 상대방 신용을 전제로 함  
            - IORB: 은행이 준비금을 연준에 예치하면 받는 금리 → 무위험·상대방 리스크 없음
            
            **2. EFFR - IORB**: 연준 금리 통제력  
            - EFFR: 은행 간 초단기 무담보 자금 거래 금리 → 시장에서 형성되는 정책금리  
            - IORB: 은행이 준비금을 연준에 예치하면 받는 금리 → 은행이 선택할 수 있는 무위험 금리 하한  
            - → EFFR이 IORB에 얼마나 근접하는지로 연준의 floor system 작동 여부를 판단  
            - → 괴리 확대 시: 제도적 마찰 또는 단기 유동성 불균형 신호
            
            **3. SOFR - RRP**: 민간 담보시장 vs 연준 유동성 흡수  
            - SOFR: 국채 담보 기반 초단기 자금 거래 금리 → 민간 담보부 시장 수급 반영  
            - RRP: MMF 등 비은행이 연준에 자금을 맡기고 받는 금리 → 사실상의 금리 하한  
            - → 스프레드는 민간 시장에서 위험을 감수하고 거래할 유인을 의미  
            - → 축소/근접: 유동성 과잉, 민간 대출 기회 부족  
            - → 확대: 담보 수요 증가, 레버리지 활동 회복
            
            **4. 3M TB - EFFR**: 단기 금리 기대  
            - 3M T-Bill: 3개월 만기 무위험 국채 금리 → 향후 단기 정책금리 기대 반영  
            - EFFR: 현재의 초단기 정책 기준 금리  
            - → 시장이 앞으로 3개월간 금리 경로를 어떻게 보는지를 보여줌  
            - → (+): 금리 인상 기대  
            - → (−): 금리 인하 기대 또는 안전자산 수요 급증
            
            **5. 10Y - 2Y**: 경기 사이클 신호 (전통적 침체 지표)  
            - 10Y: 장기 성장·물가·중립금리 기대 반영  
            - 2Y: 향후 정책금리 경로에 민감  
            - → 장단기 금리차로 경기 확장 vs 침체 기대를 판단  
            - → 역전(음수): 향후 경기 둔화·침체 가능성 신호
            
            **6. 10Y - 3M**: 정책 신뢰 기반 침체 지표  
            - 10Y: 장기 경제 전망  
            - 3M: 현재 정책금리 수준에 거의 직결  
            - → 연준이 중시하는 가장 '정책 친화적' 수익률 곡선 지표  
            - → 지속적 역전 시: 통화긴축이 실물경제를 제약할 가능성 큼
            
            **7. STLFSI4**: 금융 스트레스 종합 지표  
            - STLFSI4: 세인트루이스 연은 금융 스트레스 지수  
              (금리 스프레드, 변동성, 신용시장 지표 등을 종합)  
            - → 금융시스템 전반의 긴장도·불안 수준을 수치화  
            - → 0 이상: 평균 이상의 스트레스  
            - → 급등 구간: 금융위기·유동성 경색 국면과 높은 상관
            """)
        
        # 조회 기간 표시
        st.info(f"📅 **조회 기간**: {start_date} ~ {end_date}")
        
        # Fear & Greed 및 VIX 지수
        st.markdown("---")
        st.subheader("🎭 시장 심리 지표")
        
        indicator_cols = st.columns(2)
        
        with indicator_cols[0]:
            with st.spinner('Fear & Greed 지수 로딩 중...'):
                fg_data = get_fear_greed_index()
                
                if fg_data:
                    # Fear & Greed 게이지 차트
                    fig_fg = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=fg_data["score"],
                        domain={'x': [0, 1], 'y': [0, 1]},
                        title={'text': f"{fg_data['emoji']} Fear & Greed Index", 'font': {'size': 18, 'color': '#83858C'}},
                        number={'suffix': "", 'font': {'size': 40, 'color': '#83858C', 'family': 'Arial Black'}},
                        gauge={
                            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#83858C"},
                            'bar': {'color': fg_data["color"], 'thickness': 0.75},
                            'bgcolor': "white",
                            'borderwidth': 2,
                            'bordercolor': "gray",
                            'steps': [
                                {'range': [0, 25], 'color': '#fecaca'},      # Extreme Fear (연한 빨강)
                                {'range': [25, 45], 'color': '#fed7aa'},     # Fear (연한 주황)
                                {'range': [45, 55], 'color': '#fef08a'},     # Neutral (연한 노랑)
                                {'range': [55, 75], 'color': '#bbf7d0'},     # Greed (연한 초록)
                                {'range': [75, 100], 'color': '#86efac'}     # Extreme Greed (초록)
                            ],
                            'threshold': {
                                'line': {'color': "black", 'width': 4},
                                'thickness': 0.75,
                                'value': fg_data["score"]
                            }
                        }
                    ))
                    
                    fig_fg.update_layout(
                        height=300,
                        margin=dict(l=20, r=20, t=80, b=20),
                        paper_bgcolor="rgba(0,0,0,0)",
                        font={'color': "#83858C", 'family': "Arial"}
                    )
                    
                    st.plotly_chart(fig_fg, use_container_width=True)
                    
                    # 상태 표시
                    st.markdown(f"""
                    <div style='text-align: center; padding: 15px; background-color: {fg_data['color']}20; 
                                border-radius: 10px; border: 2px solid {fg_data['color']};'>
                        <h3 style='color: {fg_data['color']}; margin: 0;'>{fg_data['emoji']} {fg_data['status']}</h3>
                        <p style='color: #83858C; margin: 5px 0 0 0; font-size: 14px;'>
                            Score: <span style='color: black; background-color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold;'>{fg_data['score']:.1f}/100</span>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 범위 설명
                    st.caption("""
                    **해석 가이드:**
                    - 0-25: Extreme Fear 😱 (공포 극대)
                    - 25-45: Fear 😨 (공포)
                    - 45-55: Neutral 😐 (중립)
                    - 55-75: Greed 😊 (탐욕)
                    - 75-100: Extreme Greed 🤑 (탐욕 극대)
                    """)
                else:
                    st.error("Fear & Greed 데이터를 불러올 수 없습니다.")
        
        with indicator_cols[1]:
            with st.spinner('VIX 지수 로딩 중...'):
                vix_data = get_vix_index()
                
                if vix_data:
                    # VIX 게이지 차트
                    fig_vix = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=vix_data["value"],
                        domain={'x': [0, 1], 'y': [0, 1]},
                        title={'text': f"{vix_data['emoji']} VIX Index", 'font': {'size': 18, 'color': '#83858C'}},
                        number={'font': {'size': 40, 'color': '#83858C', 'family': 'Arial Black'}},
                        gauge={
                            'axis': {'range': [0, 80], 'tickwidth': 1, 'tickcolor': "#83858C"},
                            'bgcolor': "white",
                            'borderwidth': 2,
                            'bordercolor': "gray",
                            'steps': [
                                {'range': [0, 12], 'color': '#86efac'},      # 매우 낮음 (초록)
                                {'range': [12, 20], 'color': '#bbf7d0'},     # 낮음 (연한 초록)
                                {'range': [20, 30], 'color': '#fef08a'},     # 보통 (노랑)
                                {'range': [30, 40], 'color': '#fed7aa'},     # 높음 (주황)
                                {'range': [40, 80], 'color': '#fecaca'}      # 매우 높음 (빨강)
                            ],
                            'threshold': {
                                'line': {'color': "black", 'width': 4},
                                'thickness': 0.75,
                                'value': vix_data["value"]
                            }
                        }
                    ))
                    
                    fig_vix.update_layout(
                        height=300,
                        margin=dict(l=20, r=20, t=80, b=20),
                        paper_bgcolor="rgba(0,0,0,0)",
                        font={'color': "#83858C", 'family': "Arial"}
                    )
                    
                    st.plotly_chart(fig_vix, use_container_width=True)
                    
                    # 상태 표시
                    st.markdown(f"""
                    <div style='text-align: center; padding: 15px; background-color: {vix_data['color']}20; 
                                border-radius: 10px; border: 2px solid {vix_data['color']};'>
                        <h3 style='color: {vix_data['color']}; margin: 0;'>{vix_data['emoji']} {vix_data['status']}</h3>
                        <p style='color: #83858C; margin: 5px 0 0 0; font-size: 14px;'>
                            VIX: <span style='color: black; background-color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold;'>{vix_data['value']:.2f}</span> | {vix_data['description']}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 범위 설명
                    st.caption("""
                    **VIX 수준:**
                    - <12: 매우 낮음 😌 (안정)
                    - 12-20: 낮음 🙂 (보통)
                    - 20-30: 보통 😐 (변동성)
                    - 30-40: 높음 😰 (불안)
                    - >40: 매우 높음 🚨 (공포)
                    """)
                else:
                    st.error("VIX 데이터를 불러올 수 없습니다.")
        
        st.markdown("---")
        
        # 현재 상태 요약
        st.subheader("📍 현재 상태")
        
        summary_cols = st.columns(7)
        
        for idx, (key, spread_info) in enumerate(SPREADS.items()):
            with summary_cols[idx]:
                with st.spinner(f'{spread_info["name"]} 로딩 중...'):
                    df_spread, latest_value, df_components = calculate_spread(
                        spread_info, FRED_API_KEY, start_date, end_date
                    )
                    
                    if latest_value is not None:
                        if 'signals' in spread_info:
                            status_msg = get_signal_status(latest_value, spread_info['signals'])
                        else:
                            in_range = spread_info['threshold_min'] <= latest_value <= spread_info['threshold_max']
                            status_msg = "✅ 정상" if in_range else "⚠️ 주의"
                        
                        value_unit = "" if spread_info.get('is_single_series', False) else "bp"
                        
                        st.metric(
                            label=spread_info['name'],
                            value=f"{latest_value:.2f}{value_unit}",
                            delta=status_msg.split(' - ')[0] if ' - ' in status_msg else status_msg
                        )
                        st.caption(spread_info['description'])
        
        # 연준 정책금리 프레임워크
        st.markdown("---")
        st.subheader("🎯 연준 정책금리 프레임워크")
        
        with st.spinner('데이터 로딩 중...'):
            policy_series = {
                'SOFR': '담보부 익일물 금리',
                'RRPONTSYAWARD': 'ON RRP (하한)',
                'IORB': '준비금 이자율',
                'EFFR': '연방기금 실효금리',
                'DFEDTARL': 'FF 목표 하한',
                'DFEDTARU': 'FF 목표 상한'
            }
            
            policy_data = {}
            for series_id in policy_series.keys():
                df = fetch_fred_data(series_id, FRED_API_KEY, limit=None, start_date=start_date, end_date=end_date)
                if df is not None:
                    policy_data[series_id] = df
            
            if len(policy_data) > 0:
                combined_df = pd.DataFrame()
                for series_id, df in policy_data.items():
                    # date를 인덱스로 설정
                    df_indexed = df.set_index('date')
                    combined_df[series_id] = df_indexed['value']
                
                combined_df = combined_df.ffill().dropna()
                combined_df = combined_df.sort_index(ascending=True)  # 시간순 정렬
                
                fig = go.Figure()
                
                if 'DFEDTARL' in combined_df.columns and 'DFEDTARU' in combined_df.columns:
                    fig.add_trace(go.Scatter(
                        x=combined_df.index, y=combined_df['DFEDTARU'],
                        mode='lines', name='FF 목표 상한',
                        line=dict(color='rgba(200,200,200,0.3)', width=1, dash='dash')
                    ))
                    fig.add_trace(go.Scatter(
                        x=combined_df.index, y=combined_df['DFEDTARL'],
                        mode='lines', name='FF 목표 하한',
                        line=dict(color='rgba(200,200,200,0.3)', width=1, dash='dash'),
                        fill='tonexty', fillcolor='rgba(200,200,200,0.1)'
                    ))
                
                colors = {
                    'SOFR': '#FF6B6B', 'RRPONTSYAWARD': '#4ECDC4',
                    'IORB': '#95E1D3', 'EFFR': '#F38181'
                }
                
                for series_id, label in policy_series.items():
                    if series_id in combined_df.columns and series_id not in ['DFEDTARL', 'DFEDTARU']:
                        fig.add_trace(go.Scatter(
                            x=combined_df.index, y=combined_df[series_id],
                            mode='lines', name=f'{series_id} ({label})',
                            line=dict(color=colors.get(series_id, '#999999'), width=2)
                        ))
                
                fig.update_layout(
                    title="연준 정책금리 프레임워크 및 시장 금리",
                    xaxis_title="날짜", yaxis_title="금리 (%)",
                    hovermode='x unified', height=500,
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.info("""
                    **금리 조절 메커니즘:**
                    - 목표 범위: FOMC 설정
                    - IORB: 상한 역할
                    - ON RRP: 하한 역할
                    - EFFR: 실제 시장금리
                    """)
                
                with col2:
                    if len(combined_df) > 0:
                        latest = combined_df.iloc[-1]  # 최신 데이터는 마지막 행
                        st.success(f"""
                        **최신 금리 (%):**
                        - SOFR: {latest.get('SOFR', 0):.2f}%
                        - EFFR: {latest.get('EFFR', 0):.2f}%
                        - IORB: {latest.get('IORB', 0):.2f}%
                        - ON RRP: {latest.get('RRPONTSYAWARD', 0):.2f}%
                        """)
        
        # 상세 차트
        st.markdown("---")
        st.subheader("📈 상세 차트")
        
        spread_tabs = st.tabs([spread_info['name'] for spread_info in SPREADS.values()])
        
        for idx, (key, spread_info) in enumerate(SPREADS.items()):
            with spread_tabs[idx]:
                with st.spinner('데이터 로딩 중...'):
                    df_spread, latest_value, df_components = calculate_spread(
                        spread_info, FRED_API_KEY, start_date, end_date
                    )
                    
                    if df_spread is not None:
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            stat_cols = st.columns(4)
                            value_unit = "" if spread_info.get('is_single_series', False) else "bp"
                            
                            with stat_cols[0]:
                                st.metric("현재 값", f"{latest_value:.2f}{value_unit}")
                            with stat_cols[1]:
                                st.metric("평균", f"{df_spread['spread'].mean():.2f}{value_unit}")
                            with stat_cols[2]:
                                st.metric("최대", f"{df_spread['spread'].max():.2f}{value_unit}")
                            with stat_cols[3]:
                                st.metric("최소", f"{df_spread['spread'].min():.2f}{value_unit}")
                        
                        with col2:
                            if 'signals' in spread_info:
                                current_signal = get_signal_status(latest_value, spread_info['signals'])
                                signal_lines = ["**현재 신호:**", current_signal, ""]
                            else:
                                signal_lines = []
                            
                            info_text = "\n".join(signal_lines + [
                                f"**정상 범위:** {spread_info['normal_range']}",
                                "", f"**의미:** {spread_info['description']}",
                                "", f"**해석:** {spread_info['interpretation']}"
                            ])
                            
                            st.info(info_text)
                        
                        st.plotly_chart(
                            create_spread_chart(df_spread, spread_info['name'], spread_info, latest_value),
                            use_container_width=True
                        )
                        
                        if not spread_info.get('is_single_series', False) and df_components is not None:
                            with st.expander("구성 요소 보기"):
                                st.plotly_chart(
                                    create_components_chart(df_components, spread_info['series']),
                                    use_container_width=True
                                )
                                
                                latest_components = df_components.iloc[0]  # 최신값은 첫 행
                                st.dataframe(
                                    pd.DataFrame({
                                        '지표': spread_info['series'],
                                        '현재 값 (%)': [f"{val:.4f}" for val in latest_components.values]
                                    }),
                                    hide_index=True
                                )
                    else:
                        st.error("데이터를 불러올 수 없습니다.")
        
        st.caption(f"데이터 출처: Federal Reserve Economic Data (FRED)")

if __name__ == "__main__":
    main()
