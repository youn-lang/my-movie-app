import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ---------------------------------------------------------
# 1. Streamlit 페이지 기본 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 어제의 박스오피스 분석 대시보드")
st.caption("KOBIS 영화관입장권통합전산망 일별 박스오피스 데이터를 사용합니다.")


# ---------------------------------------------------------
# 2. 한국 시간 기준으로 '어제' 날짜 계산
# ---------------------------------------------------------
# Streamlit Cloud 서버는 한국이 아닌 지역의 시간을 사용할 수 있으므로,
# 반드시 Asia/Seoul 시간대를 지정해서 현재 날짜를 계산합니다.
seoul_now = datetime.now(ZoneInfo("Asia/Seoul"))
yesterday = seoul_now.date() - timedelta(days=1)

# KOBIS API의 targetDt 형식은 yyyymmdd입니다.
target_dt = yesterday.strftime("%Y%m%d")

# 화면에 표시할 날짜 형식입니다.
display_date = yesterday.strftime("%Y년 %m월 %d일")

st.subheader(f"📅 {display_date} 박스오피스")


# ---------------------------------------------------------
# 3. Streamlit 비밀 금고에서 API 인증키 불러오기
# ---------------------------------------------------------
# Streamlit Cloud의 앱 설정에서 Secrets에 아래처럼 등록해야 합니다.
#
# KOBIS_KEY = "발급받은_인증키"
#
# 인증키는 코드에 직접 적지 않습니다.
try:
    kobis_key = st.secrets["KOBIS_KEY"]
except KeyError:
    st.error(
        "KOBIS 인증키를 찾을 수 없습니다. "
        "Streamlit Cloud의 Secrets에 `KOBIS_KEY`를 등록해 주세요."
    )
    st.stop()


# ---------------------------------------------------------
# 4. KOBIS 일별 박스오피스 API 호출 함수
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def load_boxoffice_data(api_key: str, date_text: str) -> pd.DataFrame:
    """
    KOBIS 일별 박스오피스 API를 호출하고,
    분석에 필요한 열만 정리한 데이터프레임을 반환합니다.

    ttl=3600은 같은 데이터를 1시간 동안 캐시에 저장한다는 뜻입니다.
    앱을 새로고침할 때마다 API를 반복 호출하는 일을 줄일 수 있습니다.
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
        # timeout을 지정하면 서버 응답이 지나치게 오래 걸릴 때 요청을 중단합니다.
        response = requests.get(api_url, params=params, timeout=10)

        # 200번대가 아닌 HTTP 응답이면 예외를 발생시킵니다.
        response.raise_for_status()

    except requests.exceptions.Timeout as error:
        raise RuntimeError(
            "KOBIS 서버의 응답 시간이 너무 오래 걸립니다. 잠시 후 다시 시도해 주세요."
        ) from error

    except requests.exceptions.ConnectionError as error:
        raise RuntimeError(
            "KOBIS 서버에 연결할 수 없습니다. 인터넷 연결이나 API 서버 상태를 확인해 주세요."
        ) from error

    except requests.exceptions.HTTPError as error:
        raise RuntimeError(
            f"KOBIS API 요청이 실패했습니다. HTTP 상태 코드: {response.status_code}"
        ) from error

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            "KOBIS API 요청 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요."
        ) from error

    try:
        data = response.json()
    except ValueError as error:
        raise RuntimeError(
            "KOBIS 서버에서 올바른 JSON 응답을 받지 못했습니다."
        ) from error

    # KOBIS API는 인증키 오류 등의 상황에서 faultInfo를 반환할 수 있습니다.
    if "faultInfo" in data:
        fault_info = data["faultInfo"]
        message = fault_info.get("message", "알 수 없는 오류")
        error_code = fault_info.get("errorCode", "코드 없음")

        raise RuntimeError(
            f"KOBIS API 오류가 발생했습니다. "
            f"오류 코드: {error_code} / 안내: {message}"
        )

    try:
        movie_list = data["boxOfficeResult"]["dailyBoxOfficeList"]
    except (KeyError, TypeError) as error:
        raise RuntimeError(
            "KOBIS 응답 형식이 예상과 다릅니다. API 응답 구조를 확인해 주세요."
        ) from error

    if not movie_list:
        raise RuntimeError(
            "조회된 박스오피스 데이터가 없습니다. "
            "집계가 아직 완료되지 않았거나 해당 날짜의 데이터가 없을 수 있습니다."
        )

    # API 응답 목록을 판다스 데이터프레임으로 변환합니다.
    df = pd.DataFrame(movie_list)

    # 화면과 분석에 필요한 열만 선택합니다.
    required_columns = [
        "rank",
        "movieNm",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt",
    ]

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise RuntimeError(
            "KOBIS 응답에서 필요한 항목을 찾지 못했습니다: "
            + ", ".join(missing_columns)
        )

    df = df[required_columns].copy()

    # 숫자 값은 문자열로 오므로 반드시 숫자형으로 변환합니다.
    numeric_columns = ["rank", "audiCnt", "audiAcc", "scrnCnt"]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # 숫자로 바뀌지 않은 비정상 값이 있으면 0으로 처리합니다.
    df[numeric_columns] = df[numeric_columns].fillna(0).astype(int)

    # 순위를 기준으로 오름차순 정렬합니다.
    df = df.sort_values("rank").reset_index(drop=True)

    # 표에 표시할 한글 열 이름으로 변경합니다.
    df = df.rename(
        columns={
            "rank": "순위",
            "movieNm": "영화명",
            "openDt": "개봉일",
            "audiCnt": "관객수",
            "audiAcc": "누적관객",
            "scrnCnt": "스크린수",
        }
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
        "인증키가 올바른지, KOBIS 서비스가 정상인지, "
        "어제 날짜의 집계가 완료되었는지 확인해 주세요."
    )
    st.stop()


# ---------------------------------------------------------
# 6. 1위 영화 지표 카드
# ---------------------------------------------------------
first_place = boxoffice_df.iloc[0]

st.markdown("### 🏆 박스오피스 1위")

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

with metric_col1:
    st.metric(
        label="영화명",
        value=first_place["영화명"],
    )

with metric_col2:
    st.metric(
        label="어제 관객수",
        value=f"{first_place['관객수']:,}명",
    )

with metric_col3:
    st.metric(
        label="누적 관객수",
        value=f"{first_place['누적관객']:,}명",
    )

with metric_col4:
    st.metric(
        label="스크린수",
        value=f"{first_place['스크린수']:,}개",
    )


# ---------------------------------------------------------
# 7. 전체 순위 표
# ---------------------------------------------------------
st.markdown("### 📋 일별 박스오피스 순위")

# 표에 표시할 복사본을 만듭니다.
table_df = boxoffice_df.copy()

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "순위": st.column_config.NumberColumn(
            "순위",
            format="%d위",
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

# 관객수를 기준으로 내림차순 정렬한 뒤 상위 5편만 선택합니다.
top5_df = (
    boxoffice_df
    .sort_values("관객수", ascending=False)
    .head(5)
    [["영화명", "관객수"]]
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
