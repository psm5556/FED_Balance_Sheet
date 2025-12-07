import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(
    page_title="Fed Balance Sheet",
    page_icon="📊",
    layout="wide"
)

# 한글 폰트 설정을 위한 CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #1e1e1e;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .metric-card.highlighted {
        border: 2px solid #ffd700;
    }
    .metric-title {
        color: #ffffff;
        font-size: 16px;
        margin-bottom: 10px;
    }
    .metric-value {
        color: #ffffff;
        font-size: 28px;
        font-weight: bold;
    }
    .metric-change {
        font-size: 18px;
        margin-top: 5px;
    }
    .positive {
        color: #4ade80;
    }
    .negative {
        color: #f87171;
    }
</style>
""", unsafe_allow_html=True)

# FRED API 키 (GitHub Secrets에서 가져오기)
FRED_API_KEY = st.secrets.get("FRED_API_KEY", "")

# FRED 데이터 시리즈 ID
SERIES_IDS = {
    "총자산": "WALCL",
    "지급준비금": "WRESBAL",
    "TGA": "WTREGEN",
    "RRP": "RRPONTSYD",
    "연준_보유_증권": "WSHOSHO",
    "SRF": "WLSRF",
    "대출": "WLCFLPCL",
    "MMF": "MMMFFAQ027S",
    "총부채": "WALCL"
}

@st.cache_data(ttl=3600)
def fetch_fred_data(series_id, api_key):
    """FRED API에서 데이터 가져오기"""
    if not api_key:
        return None
    
    url = f"https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 10
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if "observations" in data:
                df = pd.DataFrame(data["observations"])
                df["date"] = pd.to_datetime(df["date"])
                df["value"] = pd.to_numeric(df["value"], errors="coerce")
                return df
    except Exception as e:
        st.error(f"데이터 가져오기 오류: {e}")
    
    return None

def format_number(value):
    """숫자를 $M 단위로 포맷"""
    if pd.isna(value):
        return "N/A"
    return f"{value:,.0f}"

def format_change(change):
    """변화량을 포맷"""
    if pd.isna(change):
        return "N/A"
    
    if change > 0:
        return f'<span class="positive">▲ {abs(change):,.0f}</span>'
    elif change < 0:
        return f'<span class="negative">▼ {abs(change):,.0f}</span>'
    else:
        return f'<span>{change:,.0f}</span>'

def create_metric_card(title, current_value, previous_value, highlighted=False):
    """메트릭 카드 생성"""
    change = current_value - previous_value if not pd.isna(current_value) and not pd.isna(previous_value) else 0
    
    card_class = "metric-card highlighted" if highlighted else "metric-card"
    
    return f"""
    <div class="{card_class}">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{format_number(current_value)}</div>
        <div class="metric-change">{format_change(change)}</div>
    </div>
    """

# 메인 앱
def main():
    st.title("📊 Fed Balance Sheet: Weekly Changes (Unit: $M 주)")
    st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d')}")
    
    # API 키 확인
    if not FRED_API_KEY:
        st.warning("⚠️ FRED API 키가 설정되지 않았습니다. GitHub Secrets에 FRED_API_KEY를 추가해주세요.")
        st.info("FRED API 키는 https://fred.stlouisfed.org/docs/api/api_key.html 에서 무료로 발급받을 수 있습니다.")
        
        # 샘플 데이터 표시
        st.subheader("샘플 데이터 (예시)")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(create_metric_card("총자산 (Total Assets)", 6535781, 6552419), unsafe_allow_html=True)
            st.markdown(create_metric_card("지급준비금 (Reserve Balances)", 2878165, 2897987, highlighted=True), unsafe_allow_html=True)
            st.markdown(create_metric_card("TGA (재무부 일반계정)", 908523, 899678, highlighted=True), unsafe_allow_html=True)
            st.markdown(create_metric_card("RRP (역레포)", 332669, 332399), unsafe_allow_html=True)
        
        with col2:
            st.markdown(create_metric_card("연준 보유 증권 (Securities Held)", 6244751, 6247237), unsafe_allow_html=True)
            st.markdown(create_metric_card("SRF (상설레포)", 1, 14000, highlighted=True), unsafe_allow_html=True)
            st.markdown(create_metric_card("대출 (Loans)", 7915, 7876), unsafe_allow_html=True)
            st.markdown(create_metric_card("MMF (Money Market Funds)", 6489869, 6506556), unsafe_allow_html=True)
        
        return
    
    # 실제 데이터 가져오기
    with st.spinner("데이터를 불러오는 중..."):
        data_dict = {}
        
        for name, series_id in SERIES_IDS.items():
            df = fetch_fred_data(series_id, FRED_API_KEY)
            if df is not None and len(df) >= 2:
                data_dict[name] = {
                    "current": df.iloc[0]["value"],
                    "previous": df.iloc[1]["value"],
                    "date": df.iloc[0]["date"]
                }
    
    if not data_dict:
        st.error("데이터를 불러올 수 없습니다.")
        return
    
    # 레이아웃 구성
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("항목")
        
        if "총자산" in data_dict:
            d = data_dict["총자산"]
            st.markdown(create_metric_card(
                "총자산 (Total Assets)", 
                d["current"], 
                d["previous"]
            ), unsafe_allow_html=True)
        
        if "지급준비금" in data_dict:
            d = data_dict["지급준비금"]
            st.markdown(create_metric_card(
                "지급준비금 (Reserve Balances)", 
                d["current"], 
                d["previous"],
                highlighted=True
            ), unsafe_allow_html=True)
        
        if "TGA" in data_dict:
            d = data_dict["TGA"]
            st.markdown(create_metric_card(
                "TGA (재무부 일반계정)", 
                d["current"], 
                d["previous"],
                highlighted=True
            ), unsafe_allow_html=True)
        
        if "RRP" in data_dict:
            d = data_dict["RRP"]
            st.markdown(create_metric_card(
                "RRP (역레포)", 
                d["current"], 
                d["previous"]
            ), unsafe_allow_html=True)
    
    with col2:
        st.subheader("변경 (Change)")
        
        if "연준_보유_증권" in data_dict:
            d = data_dict["연준_보유_증권"]
            st.markdown(create_metric_card(
                "연준 보유 증권 (Securities Held)", 
                d["current"], 
                d["previous"]
            ), unsafe_allow_html=True)
        
        if "SRF" in data_dict:
            d = data_dict["SRF"]
            st.markdown(create_metric_card(
                "SRF (상설레포)", 
                d["current"], 
                d["previous"],
                highlighted=True
            ), unsafe_allow_html=True)
        
        if "대출" in data_dict:
            d = data_dict["대출"]
            st.markdown(create_metric_card(
                "대출 (Loans)", 
                d["current"], 
                d["previous"]
            ), unsafe_allow_html=True)
        
        if "MMF" in data_dict:
            d = data_dict["MMF"]
            st.markdown(create_metric_card(
                "MMF (Money Market Funds)", 
                d["current"], 
                d["previous"]
            ), unsafe_allow_html=True)
    
    # 추가 정보
    st.markdown("---")
    st.caption("데이터 출처: Federal Reserve Economic Data (FRED)")

if __name__ == "__main__":
    main()
