import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(
    page_title="Fed Balance Sheet",
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

# FRED API 키 (GitHub Secrets에서 가져오기)
FRED_API_KEY = st.secrets.get("FRED_API_KEY", "")

# FRED 데이터 시리즈 정보 (ID, 링크, 하이라이트 여부, 분류, 설명, 유동성 영향)
SERIES_INFO = {
    "총자산 (Total Assets)": {
        "id": "WALCL",
        "highlight": False,
        "category": "자산 (Assets)",
        "description": "연준의 전체 자산 규모",
        "liquidity_impact": "증가 시 시장 유동성 ↑"
    },
    "연준 보유 증권 (Securities Held)": {
        "id": "WSHOSHO",
        "highlight": False,
        "category": "자산 (Assets)",
        "description": "연준이 보유한 국채 및 MBS",
        "liquidity_impact": "증가 시 시장 유동성 ↑"
    },
    "SRF (상설레포)": {
        "id": "RPONTSYD",
        "highlight": True,
        "category": "자산 (Assets)",
        "description": "은행에 제공하는 단기 대출",
        "liquidity_impact": "증가 시 은행 유동성 ↑"
    },
    "대출 (Loans)": {
        "id": "WLCFLPCL",
        "highlight": False,
        "category": "자산 (Assets)",
        "description": "연준의 금융기관 대출",
        "liquidity_impact": "증가 시 시장 유동성 ↑"
    },
    "  ㄴ Primary Credit": {
        "id": "WLCFLPCL",
        "highlight": False,
        "category": "자산 (Assets)",
        "description": "할인창구 1차 신용대출",
        "liquidity_impact": "증가 시 은행 유동성 ↑"
    },
    "  ㄴ Secondary Credit": {
        "id": "WLCFLSCL",
        "highlight": False,
        "category": "자산 (Assets)",
        "description": "할인창구 2차 신용대출",
        "liquidity_impact": "증가 시 은행 유동성 ↑"
    },
    "  ㄴ Seasonal Credit": {
        "id": "WLCFLSECL",
        "highlight": False,
        "category": "자산 (Assets)",
        "description": "할인창구 계절성 신용대출",
        "liquidity_impact": "증가 시 은행 유동성 ↑"
    },
    "지급준비금 (Reserve Balances)": {
        "id": "WRESBAL",
        "highlight": True,
        "category": "부채 (Liabilities)",
        "description": "은행들이 연준에 예치한 자금",
        "liquidity_impact": "증가 시 은행 유동성 ↑"
    },
    "TGA (재무부 일반계정)": {
        "id": "WTREGEN",
        "highlight": True,
        "category": "부채 (Liabilities)",
        "description": "미 재무부의 연준 예금",
        "liquidity_impact": "증가 시 시장 유동성 ↓"
    },
    "RRP (역레포)": {
        "id": "RRPONTSYD",
        "highlight": False,
        "category": "부채 (Liabilities)",
        "description": "MMF 등의 초단기 자금 흡수",
        "liquidity_impact": "증가 시 시장 유동성 ↓"
    },
    "MMF (Money Market Funds)": {
        "id": "MMMFFAQ027S",
        "highlight": False,
        "category": "부채 (Liabilities)",
        "description": "머니마켓펀드 총 자산",
        "liquidity_impact": "증가 시 현금 보유 선호 ↑"
    },
    "Retail MMF": {
        "id": "WRMFNS",
        "highlight": False,
        "category": "부채 (Liabilities)",
        "description": "개인투자자용 머니마켓펀드",
        "liquidity_impact": "증가 시 현금 보유 선호 ↑"
    },
    "총부채 (Total Liabilities)": {
        "id": "WALCL",
        "highlight": False,
        "category": "부채 (Liabilities)",
        "description": "연준의 전체 부채 규모",
        "liquidity_impact": "구조 변화가 유동성에 영향"
    }
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

# 메인 앱
def main():
    st.title("📊 Fed Balance Sheet: Weekly Changes (Unit: $M 주)")
    st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # API 키 확인
    if not FRED_API_KEY:
        st.warning("⚠️ FRED API 키가 설정되지 않았습니다. GitHub Secrets에 FRED_API_KEY를 추가해주세요.")
        st.info("FRED API 키는 https://fred.stlouisfed.org/docs/api/api_key.html 에서 무료로 발급받을 수 있습니다.")
        
        # 샘플 데이터 표시
        st.subheader("샘플 데이터 (예시)")
        
        sample_data = {
            "분류": [
                "자산",
                "자산",
                "자산",
                "자산",
                "자산",
                "자산",
                "자산",
                "부채",
                "부채",
                "부채",
                "부채",
                "부채",
                "부채"
            ],
            "항목": [
                "총자산 (Total Assets)",
                "연준 보유 증권 (Securities Held)",
                "SRF (상설레포)",
                "대출 (Loans)",
                "  ㄴ Primary Credit",
                "  ㄴ Secondary Credit",
                "  ㄴ Seasonal Credit",
                "지급준비금 (Reserve Balances)",
                "TGA (재무부 일반계정)",
                "RRP (역레포)",
                "MMF (Money Market Funds)",
                "Retail MMF",
                "총부채 (Total Liabilities)"
            ],
            "설명": [
                "연준의 전체 자산 규모",
                "연준이 보유한 국채 및 MBS",
                "은행에 제공하는 단기 대출",
                "연준의 금융기관 대출",
                "할인창구 1차 신용대출",
                "할인창구 2차 신용대출",
                "할인창구 계절성 신용대출",
                "은행들이 연준에 예치한 자금",
                "미 재무부의 연준 예금",
                "MMF 등의 초단기 자금 흡수",
                "머니마켓펀드 총 자산",
                "개인투자자용 머니마켓펀드",
                "연준의 전체 부채 규모"
            ],
            "현재 값": [
                "6,535,781",
                "6,244,751",
                "1",
                "7,915",
                "7,500",
                "200",
                "215",
                "2,878,165",
                "908,523",
                "332,669",
                "6,489,869",
                "2,100,000",
                "6,535,781"
            ],
            "이전 값": [
                "6,552,419",
                "6,247,237",
                "14,000",
                "7,876",
                "7,400",
                "250",
                "226",
                "2,897,987",
                "899,678",
                "332,399",
                "6,506,556",
                "2,095,000",
                "6,552,419"
            ],
            "변화": [
                "▼ 16,638",
                "▼ 2,486",
                "▼ 13,999",
                "▲ 39",
                "▲ 100",
                "▼ 50",
                "▼ 11",
                "▼ 19,822",
                "▲ 8,845",
                "▲ 270",
                "▼ 16,687",
                "▲ 5,000",
                "▼ 16,638"
            ],
            "유동성 영향": [
                "증가 시 시장 유동성 ↑",
                "증가 시 시장 유동성 ↑",
                "증가 시 은행 유동성 ↑",
                "증가 시 시장 유동성 ↑",
                "증가 시 은행 유동성 ↑",
                "증가 시 은행 유동성 ↑",
                "증가 시 은행 유동성 ↑",
                "증가 시 은행 유동성 ↑",
                "증가 시 시장 유동성 ↓",
                "증가 시 시장 유동성 ↓",
                "증가 시 현금 보유 선호 ↑",
                "증가 시 현금 보유 선호 ↑",
                "구조 변화가 유동성에 영향"
            ],
            "출처": [
                "🔗 WALCL",
                "🔗 WSHOSHO",
                "🔗 RPONTSYD",
                "🔗 WLCFLPCL",
                "🔗 WLCFLPCL",
                "🔗 WLCFLSCL",
                "🔗 WLCFLSECL",
                "🔗 WRESBAL",
                "🔗 WTREGEN",
                "🔗 RRPONTSYD",
                "🔗 MMMFFAQ027S",
                "🔗 WRMFNS",
                "🔗 WALCL"
            ]
        }
        
        df_sample = pd.DataFrame(sample_data)
        
        st.dataframe(
            df_sample,
            hide_index=True,
            use_container_width=True,
            height=550
        )
        
        st.info("💡 위 데이터는 예시입니다. FRED API 키를 설정하면 실시간 데이터를 확인할 수 있습니다.")
        return
    
    # 실제 데이터 가져오기
    with st.spinner("데이터를 불러오는 중..."):
        data_list = []
        
        for name, info in SERIES_INFO.items():
            series_id = info["id"]
            highlight = info["highlight"]
            category = info["category"]
            description = info["description"]
            liquidity_impact = info["liquidity_impact"]
            
            df = fetch_fred_data(series_id, FRED_API_KEY)
            
            if df is not None and len(df) >= 2:
                current_value = df.iloc[0]["value"]
                previous_value = df.iloc[1]["value"]
                change = current_value - previous_value
                date = df.iloc[0]["date"]
                
                data_list.append({
                    "분류": category,
                    "항목": name,
                    "설명": description,
                    "현재 값": format_number(current_value),
                    "이전 값": format_number(previous_value),
                    "변화": format_change(change),
                    "유동성 영향": liquidity_impact,
                    "출처": f'<a href="{get_fred_link(series_id)}" target="_blank">🔗 {series_id}</a>',
                    "하이라이트": highlight,
                    "변화_수치": change,  # 정렬용
                    "분류_순서": 0 if "자산" in category else 1  # 자산 먼저, 부채 나중
                })
            else:
                data_list.append({
                    "분류": category,
                    "항목": name,
                    "설명": description,
                    "현재 값": "N/A",
                    "이전 값": "N/A",
                    "변화": "N/A",
                    "유동성 영향": liquidity_impact,
                    "출처": f'<a href="{get_fred_link(series_id)}" target="_blank">🔗 {series_id}</a>',
                    "하이라이트": highlight,
                    "변화_수치": 0,
                    "분류_순서": 0 if "자산" in category else 1
                })
    
    if not data_list:
        st.error("데이터를 불러올 수 없습니다.")
        return
    
    # DataFrame 생성 및 정렬 (자산 먼저, 부채 나중)
    df_display = pd.DataFrame(data_list)
    df_display = df_display.sort_values(by=["분류_순서", "항목"])
    
    # 테이블 표시
    st.markdown("### 📊 Fed Balance Sheet 데이터")
    
    # HTML 테이블로 표시 (링크 지원)
    html_table = "<table style='width:100%; border-collapse: collapse;'>"
    html_table += "<thead><tr style='background-color: #2d2d2d;'>"
    html_table += "<th style='padding: 12px; text-align: left; color: white; width: 8%;'>분류</th>"
    html_table += "<th style='padding: 12px; text-align: left; color: white; width: 18%;'>항목</th>"
    html_table += "<th style='padding: 12px; text-align: left; color: white; width: 15%;'>설명</th>"
    html_table += "<th style='padding: 12px; text-align: right; color: white; width: 12%;'>현재 값</th>"
    html_table += "<th style='padding: 12px; text-align: right; color: white; width: 12%;'>이전 값</th>"
    html_table += "<th style='padding: 12px; text-align: right; color: white; width: 12%;'>변화</th>"
    html_table += "<th style='padding: 12px; text-align: left; color: white; width: 15%;'>유동성 영향</th>"
    html_table += "<th style='padding: 12px; text-align: center; color: white; width: 8%;'>출처</th>"
    html_table += "</tr></thead><tbody>"
    
    current_category = None
    for _, row in df_display.iterrows():
        bg_color = "#3d3d00" if row["하이라이트"] else "#1e1e1e"
        border_style = "border: 2px solid #ffd700;" if row["하이라이트"] else ""
        
        # 세부 항목 스타일링 (들여쓰기)
        indent_style = "padding-left: 30px;" if row["항목"].startswith("  ㄴ") else ""
        
        # 분류가 바뀔 때 구분선 추가
        if current_category != row["분류"]:
            if current_category is not None:
                html_table += "<tr style='height: 10px; background-color: #0e1117;'><td colspan='8'></td></tr>"
            current_category = row["분류"]
        
        # 변화 색상 적용
        change_text = row["변화"]
        if "▲" in change_text:
            change_color = "color: #4ade80;"
        elif "▼" in change_text:
            change_color = "color: #f87171;"
        else:
            change_color = "color: white;"
        
        # 유동성 영향 색상 적용
        liquidity_text = row["유동성 영향"]
        if "↑" in liquidity_text and "유동성" in liquidity_text:
            liquidity_color = "color: #4ade80;"  # 초록색
        elif "↓" in liquidity_text:
            liquidity_color = "color: #f87171;"  # 빨간색
        else:
            liquidity_color = "color: #fbbf24;"  # 노란색
        
        html_table += f"<tr style='background-color: {bg_color}; {border_style}'>"
        html_table += f"<td style='padding: 12px; color: #9ca3af; font-weight: 600; font-size: 13px;'>{row['분류']}</td>"
        html_table += f"<td style='padding: 12px; {indent_style} color: white; font-size: 14px;'>{row['항목']}</td>"
        html_table += f"<td style='padding: 12px; color: #d1d5db; font-size: 13px;'>{row['설명']}</td>"
        html_table += f"<td style='padding: 12px; text-align: right; color: white; font-size: 14px;'>{row['현재 값']}</td>"
        html_table += f"<td style='padding: 12px; text-align: right; color: white; font-size: 14px;'>{row['이전 값']}</td>"
        html_table += f"<td style='padding: 12px; text-align: right; {change_color} font-size: 14px;'><b>{change_text}</b></td>"
        html_table += f"<td style='padding: 12px; {liquidity_color} font-size: 13px;'><b>{liquidity_text}</b></td>"
        html_table += f"<td style='padding: 12px; text-align: center; font-size: 13px;'>{row['출처']}</td>"
        html_table += "</tr>"
    
    html_table += "</tbody></table>"
    
    st.markdown(html_table, unsafe_allow_html=True)
    
    # 추가 정보
    st.markdown("---")
    st.markdown("""
    ### 📌 항목별 상세 설명
    
    #### 💰 자산 항목 (Assets)
    - **총자산**: 연준 대차대조표의 전체 자산 규모. 증가하면 통화량 증가로 시장 유동성이 높아집니다.
    - **연준 보유 증권**: 국채와 주택저당증권(MBS)을 매입하여 시장에 유동성을 공급합니다. 양적완화(QE)의 핵심 지표입니다.
    - **SRF (상설레포)**: 은행이 담보를 제공하고 연준으로부터 단기 자금을 조달하는 시설입니다. 증가하면 은행의 유동성이 개선됩니다.
    - **대출**: 연준이 금융기관에 제공하는 긴급 유동성입니다. 증가하면 금융 시스템의 스트레스를 나타낼 수 있습니다.
      - **Primary Credit**: 재무건전성이 양호한 은행에 제공하는 할인창구 1차 신용대출
      - **Secondary Credit**: 재무상태가 취약한 은행에 제공하는 할인창구 2차 신용대출 (금리가 더 높음)
      - **Seasonal Credit**: 계절적 자금 수요가 있는 소규모 은행에 제공하는 대출
    
    #### 💳 부채 항목 (Liabilities)
    - **지급준비금**: 은행들이 연준에 예치한 초과 준비금입니다. 증가하면 은행의 대출 여력이 높아집니다.
    - **TGA (재무부 일반계정)**: 미 재무부가 연준에 보관하는 현금입니다. 증가하면 시장에서 유동성이 빠져나가 긴축 효과를 냅니다.
    - **RRP (역레포)**: 머니마켓펀드 등이 초단기로 연준에 자금을 예치하는 제도입니다. 증가하면 시장 유동성이 흡수됩니다.
    - **MMF**: 머니마켓펀드의 총 자산 규모입니다. 증가는 투자자들이 안전자산을 선호함을 의미합니다.
    - **Retail MMF**: 개인투자자가 주로 이용하는 머니마켓펀드입니다. 개인의 현금 선호도를 나타냅니다.
    
    ### 💡 유동성 해석 가이드
    
    **시장 유동성 증가 요인 (긍정적)**
    - 연준 보유 증권 ↑ (QE)
    - 지급준비금 ↑
    - 대출 ↑
    - TGA ↓ (재무부 지출)
    - RRP ↓
    
    **시장 유동성 감소 요인 (긴축적)**
    - 연준 보유 증권 ↓ (QT)
    - 지급준비금 ↓
    - TGA ↑ (세금 징수)
    - RRP ↑
    
    ---
    
    ### 🔍 주요 모니터링 포인트
    - **하이라이트 항목** (금색 테두리): 지급준비금, TGA, SRF는 단기 유동성 변화를 파악하는 핵심 지표입니다.
    - **데이터 주기**: 주간 단위로 업데이트됩니다 (매주 목요일 발표).
    - **출처 링크**: 각 항목의 🔗 링크를 클릭하면 FRED 원본 데이터와 차트를 확인할 수 있습니다.
    """)
    
    st.caption("데이터 출처: Federal Reserve Economic Data (FRED) - St. Louis Federal Reserve Bank")

if __name__ == "__main__":
    main()
