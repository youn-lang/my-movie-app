import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ---------------------------------------------------------
# 1. 페이지 기본 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="일별 박스오피스",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 일별 박스오피스 분석 대시보드")
st.caption("KOBIS 영화관입장권통합전산망의 일별 박스오피스 데이터를 조회합니다.")


# ---------------------------------------------------------
# 2. 한국 시간 기준 날짜 계산
# ---------------------------------------------------------
# Streamlit Cloud 서버는 해외 시간대를 사용할 수 있으므로
# 반드시 Asia/Seoul 기준으로 오늘과 어제를 계산합니다.
seoul_now = datetime.now(ZoneInfo("Asia/Seoul"))
today = seoul_now.date()
yesterday = today - timedelta(days=1)

# 오늘 자료는 아직 집계되지 않았을 수 있으므로,
# 달력에서 선택 가능한 가장 늦은 날짜는 어제입니다.
selected_date = st.date_input(
    "조회 날짜",
    value=yesterday,
    max_value=yesterday,
    help="오늘 데이터는 집계 전일 수 있으므로 어제까지만 선택할 수 있습니다.",
)

target_dt = selected_date.strftime("%Y%m%d")
display_date = selected_date.strftime("%Y년 %m월 %d일")

st.subheader(f"📅 {display_date} 박스오피스")


# ---------------------------------------------------------
# 3. 비밀 금고에서 KOBIS 인증키 불러오기
# ---------------------------------------------------------
try:
    kobis_key = st.secrets["KOBIS_KEY"]
except KeyError:
    st.error(
        "KOBIS 인증키가 없습니다. "
        "Streamlit Cloud의 Secrets에 `KOBIS_KEY`를 등록해 주세요."
    )
    st.stop()


# ---------------------------------------------------------
# 4. KOBIS API 호출 함수
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def load_boxoffice_data(api_key: str, date_text: str) -> pd.DataFrame:
    """
    KOBIS 일별 박스오피스 API를 호출하고,
    분석에 필요한 값들을 정리해 반환합니다.
    """

    api_url = (
        "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
        "boxoffice/searchDailyBoxOfficeList.json"
    )

    params = {
        "key": api_key,
        "targetDt": date_text,
    }

    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()

    except requests.exceptions.Timeout as error:
        raise RuntimeError(
            "KOBIS 서버의 응답이 늦습니다. 잠시 후 다시 시도해 주세요."
        ) from error

    except requests.exceptions.ConnectionError as error:
        raise RuntimeError(
            "KOBIS 서버에 연결할 수 없습니다. 인터넷 연결 상태를 확인해 주세요."
        ) from error

    except requests.exceptions.HTTPError as error:
        raise RuntimeError(
            f"KOBIS API 요청이 실패했습니다. HTTP 상태 코드: {response.status_code}"
        ) from error

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            "KOBIS API 요청 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
        ) from error

    try:
        data = response.json()
    except ValueError as error:
        raise RuntimeError(
            "KOBIS 서버가 올바른 JSON 형식으로 응답하지 않았습니다."
        ) from error

    # 인증키 오류 등은 faultInfo에 담겨 올 수 있습니다.
    if "faultInfo" in data:
        fault_info = data["faultInfo"]
        error_code = fault_info.get("errorCode", "코드 없음")
        message = fault_info.get("message", "알 수 없는 오류")

        raise RuntimeError(
            f"KOBIS API 오류가 발생했습니다. "
            f"오류 코드: {error_code} / 안내: {message}"
        )

    try:
        movie_list = data["boxOfficeResult"]["dailyBoxOfficeList"]
    except (KeyError, TypeError) as error:
        raise RuntimeError(
            "KOBIS 응답 구조가 예상과 다릅니다."
        ) from error

    if not movie_list:
        raise RuntimeError(
            "선택한 날짜의 박스오피스 데이터가 없습니다."
        )

    df = pd.DataFrame(movie_list)

    # rankInten은 전날 대비 순위 증감입니다.
    required_columns = [
        "rank",
        "rankInten",
        "movieNm",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise RuntimeError(
            "응답에서 필요한 열을 찾지 못했습니다: "
            + ", ".join(missing_columns)
        )

    df = df[required_columns].copy()

    # 숫자 값은 문자열로 오므로 숫자형으로 변환합니다.
    numeric_columns = [
        "rank",
        "rankInten",
        "audiCnt",
        "audiAcc",
        "scrnCnt",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df[numeric_columns] = df[numeric_columns].fillna(0).astype(int)

    # 순위를 기준으로 정렬합니다.
    df = df.sort_values("rank").reset_index(drop=True)

    # 전날 대비 순위 변동 표시를 만듭니다.
    # rankInten이 양수면 순위 상승, 음수면 순위 하락입니다.
    def format_rank_change(value: int) -> str:
        if value > 0:
            return f"🔺 {value}"
        if value < 0:
            return f"🔽 {abs(value)}"
        return "—"

    df["rank_change_display"] = df["rankInten"].apply(format_rank_change)

    # 누적 관객이 100만 명을 넘으면 영화명 뒤에 트로피를 붙입니다.
    df["movie_name_display"] = df.apply(
        lambda row: (
            f"{row['movieNm']} 🏆"
            if row["audiAcc"] > 1_000_000
            else row["movieNm"]
        ),
        axis=1,
    )

    return df


# ---------------------------------------------------------
# 5. 데이터 불러오기
# ---------------------------------------------------------
try:
    boxoffice_df = load_boxoffice_data(kobis_key, target_dt)

except RuntimeError as error:
    st.error(str(error))
    st.info(
        "인증키와 인터넷 연결 상태, 그리고 선택한 날짜의 데이터 제공 여부를 확인해 주세요."
    )
    st.stop()


# ---------------------------------------------------------
# 6. 1위 영화 지표 카드
# ---------------------------------------------------------
first_place = boxoffice_df.iloc[0]

st.markdown("### 🏆 박스오피스 1위")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="영화명",
        value=first_place["movie_name_display"],
    )

with col2:
    st.metric(
        label="당일 관객수",
        value=f"{first_place['audiCnt']:,}명",
    )

with col3:
    st.metric(
        label="누적 관객수",
        value=f"{first_place['audiAcc']:,}명",
    )

with col4:
    st.metric(
        label="스크린수",
        value=f"{first_place['scrnCnt']:,}개",
    )


# ---------------------------------------------------------
# 7. 전체 순위 표
# ---------------------------------------------------------
st.markdown("### 📋 일별 박스오피스 순위")

table_df = boxoffice_df[
    [
        "rank",
        "rank_change_display",
        "movie_name_display",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt",
    ]
].copy()

table_df = table_df.rename(
    columns={
        "rank": "순위",
        "rank_change_display": "전날 대비",
        "movie_name_display": "영화명",
        "openDt": "개봉일",
        "audiCnt": "관객수",
        "audiAcc": "누적관객",
        "scrnCnt": "스크린수",
    }
)

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "순위": st.column_config.NumberColumn(
            "순위",
            format="%d위",
        ),
        "전날 대비": st.column_config.TextColumn(
            "전날 대비",
            help="🔺 순위 상승 / 🔽 순위 하락 / — 변동 없음",
        ),
        "관객수": st.column_config.NumberColumn(
            "관객수",
            format="%d명",
        ),
        "누적관객": st.column_config.NumberColumn(
            "누적관객",
            format="%d명",
        ),
        "스크린수": st.column_config.NumberColumn(
            "스크린수",
            format="%d개",
        ),
    },
)


# ---------------------------------------------------------
# 8. 관객수 상위 5편 막대그래프
# ---------------------------------------------------------
st.markdown("### 📊 관객수 상위 5편")

top5_df = (
    boxoffice_df
    .sort_values("audiCnt", ascending=False)
    .head(5)
    [["movieNm", "audiCnt"]]
    .rename(
        columns={
            "movieNm": "영화명",
            "audiCnt": "관객수",
        }
    )
    .set_index("영화명")
)

st.bar_chart(
    top5_df,
    x_label="영화명",
    y_label="관객수",
    use_container_width=True,
)


# ---------------------------------------------------------
# 9. 하단 안내
# ---------------------------------------------------------
st.divider()
st.caption(
    f"조회 기준일: {display_date} · "
    "자료 출처: 영화진흥위원회 KOBIS 영화관입장권통합전산망"
)
