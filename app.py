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

# FRED 데이터 시리즈 정보 (ID, 링크, 하이라이트 여부)
SERIES_INFO = {
    "총자산 (Total Assets)": {
        "id": "WALCL",
        "highlight": False
    },
    "지급준비금 (Reserve Balances)": {
        "id": "WRESBAL",
        "highlight": True
    },
    "TGA (재무부 일반계정)": {
        "id": "WTREGEN",
        "highlight": True
    },
    "RRP (역레포)": {
        "id": "RRPONTSYD",
        "highlight": False
    },
    "연준 보유 증권 (Securities Held)": {
        "id": "WSHOSHO",
        "highlight": False
    },
    "SRF (상설레포)": {
        "id": "WLSRF",
        "highlight": True
    },
    "대출 (Loans)": {
        "id": "WLCFLPCL",
        "highlight": False
    },
    "MMF (Money Market Funds)": {
        "id": "MMMFFAQ027S",
        "highlight": False
    },
    "총부채 (Total Liabilities)": {
        "id": "WALCL",
        "highlight": False
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
            "항목": [
                "총자산 (Total Assets)",
                "지급준비금 (Reserve Balances)",
                "TGA (재무부 일반계정)",
                "RRP (역레포)",
                "연준 보유 증권 (Securities Held)",
                "SRF (상설레포)",
                "대출 (Loans)",
                "MMF (Money Market Funds)",
                "총부채 (Total Liabilities)"
            ],
            "현재 값": [
                "6,535,781",
                "2,878,165",
                "908,523",
                "332,669",
                "6,244,751",
                "1",
                "7,915",
                "6,489,869",
                "6,535,781"
            ],
            "이전 값": [
                "6,552,419",
                "2,897,987",
                "899,678",
                "332,399",
                "6,247,237",
                "14,000",
                "7,876",
                "6,506,556",
                "6,552,419"
            ],
            "변화": [
                "▼ 16,638",
                "▼ 19,822",
                "▲ 8,845",
                "▲ 270",
                "▼ 2,486",
                "▼ 13,999",
                "▲ 39",
                "▼ 16,687",
                "▼ 16,638"
            ],
            "출처": [
                "🔗 WALCL",
                "🔗 WRESBAL",
                "🔗 WTREGEN",
                "🔗 RRPONTSYD",
                "🔗 WSHOSHO",
                "🔗 WLSRF",
                "🔗 WLCFLPCL",
                "🔗 MMMFFAQ027S",
                "🔗 WALCL"
            ]
        }
        
        df_sample = pd.DataFrame(sample_data)
        
        # 스타일 적용
        def highlight_rows(row):
            if row["항목"] in ["지급준비금 (Reserve Balances)", "TGA (재무부 일반계정)", "SRF (상설레포)"]:
                return ['background-color: #3d3d00; border: 2px solid #ffd700'] * len(row)
            return [''] * len(row)
        
        st.dataframe(
            df_sample,
            hide_index=True,
            use_container_width=True,
            height=400
        )
        
        st.info("💡 위 데이터는 예시입니다. FRED API 키를 설정하면 실시간 데이터를 확인할 수 있습니다.")
        return
    
    # 실제 데이터 가져오기
    with st.spinner("데이터를 불러오는 중..."):
        data_list = []
        
        for name, info in SERIES_INFO.items():
            series_id = info["id"]
            highlight = info["highlight"]
            
            df = fetch_fred_data(series_id, FRED_API_KEY)
            
            if df is not None and len(df) >= 2:
                current_value = df.iloc[0]["value"]
                previous_value = df.iloc[1]["value"]
                change = current_value - previous_value
                date = df.iloc[0]["date"]
                
                data_list.append({
                    "항목": name,
                    "현재 값": format_number(current_value),
                    "이전 값": format_number(previous_value),
                    "변화": format_change(change),
                    "출처": f'<a href="{get_fred_link(series_id)}" target="_blank">🔗 {series_id}</a>',
                    "하이라이트": highlight,
                    "변화_수치": change  # 정렬용
                })
            else:
                data_list.append({
                    "항목": name,
                    "현재 값": "N/A",
                    "이전 값": "N/A",
                    "변화": "N/A",
                    "출처": f'<a href="{get_fred_link(series_id)}" target="_blank">🔗 {series_id}</a>',
                    "하이라이트": highlight,
                    "변화_수치": 0
                })
    
    if not data_list:
        st.error("데이터를 불러올 수 없습니다.")
        return
    
    # DataFrame 생성
    df_display = pd.DataFrame(data_list)
    
    # 테이블 표시
    st.markdown("### 📊 Fed Balance Sheet 데이터")
    
    # HTML 테이블로 표시 (링크 지원)
    html_table = "<table style='width:100%; border-collapse: collapse;'>"
    html_table += "<thead><tr style='background-color: #2d2d2d;'>"
    html_table += "<th style='padding: 12px; text-align: left; color: white;'>항목</th>"
    html_table += "<th style='padding: 12px; text-align: right; color: white;'>현재 값</th>"
    html_table += "<th style='padding: 12px; text-align: right; color: white;'>이전 값</th>"
    html_table += "<th style='padding: 12px; text-align: right; color: white;'>변화</th>"
    html_table += "<th style='padding: 12px; text-align: center; color: white;'>출처</th>"
    html_table += "</tr></thead><tbody>"
    
    for _, row in df_display.iterrows():
        bg_color = "#3d3d00" if row["하이라이트"] else "#1e1e1e"
        border_style = "border: 2px solid #ffd700;" if row["하이라이트"] else ""
        
        # 변화 색상 적용
        change_text = row["변화"]
        if "▲" in change_text:
            change_color = "color: #4ade80;"
        elif "▼" in change_text:
            change_color = "color: #f87171;"
        else:
            change_color = "color: white;"
        
        html_table += f"<tr style='background-color: {bg_color}; {border_style}'>"
        html_table += f"<td style='padding: 12px; color: white;'>{row['항목']}</td>"
        html_table += f"<td style='padding: 12px; text-align: right; color: white;'>{row['현재 값']}</td>"
        html_table += f"<td style='padding: 12px; text-align: right; color: white;'>{row['이전 값']}</td>"
        html_table += f"<td style='padding: 12px; text-align: right; {change_color}'><b>{change_text}</b></td>"
        html_table += f"<td style='padding: 12px; text-align: center;'>{row['출처']}</td>"
        html_table += "</tr>"
    
    html_table += "</tbody></table>"
    
    st.markdown(html_table, unsafe_allow_html=True)
    
    # 추가 정보
    st.markdown("---")
    st.markdown("""
    ### 📌 참고사항
    - **하이라이트 항목**: 지급준비금, TGA, SRF는 주요 모니터링 항목입니다.
    - **데이터 주기**: 주간 단위로 업데이트됩니다.
    - **출처 링크**: 각 항목의 🔗 링크를 클릭하면 FRED 원본 데이터를 확인할 수 있습니다.
    """)
    
    st.caption("데이터 출처: Federal Reserve Economic Data (FRED) - St. Louis Federal Reserve Bank")

if __name__ == "__main__":
    main()
