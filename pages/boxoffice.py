import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st


# =========================================================
# 1. 페이지 기본 설정
# =========================================================
st.set_page_config(
    page_title="KOBIS 시네마 박스오피스",
    page_icon="🎬",
    layout="wide",
)


# =========================================================
# 2. 영화 소개 화면에 어울리는 시네마 테마 CSS
# =========================================================
st.markdown(
    """
    <style>
    /* 전체 화면 배경 */
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(126, 34, 206, 0.22), transparent 28%),
            radial-gradient(circle at top right, rgba(220, 38, 38, 0.18), transparent 24%),
            linear-gradient(180deg, #09090b 0%, #111827 52%, #09090b 100%);
        color: #f8fafc;
    }

    /* 기본 본문 폭과 위쪽 여백 */
    .block-container {
        max-width: 1280px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* 상단 시네마 배너 */
    .cinema-hero {
        position: relative;
        overflow: hidden;
        padding: 2.2rem 2.4rem;
        margin-bottom: 1.4rem;
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        background:
            linear-gradient(135deg, rgba(15, 23, 42, 0.94), rgba(88, 28, 135, 0.86)),
            repeating-linear-gradient(
                90deg,
                rgba(255,255,255,0.03) 0px,
                rgba(255,255,255,0.03) 16px,
                transparent 16px,
                transparent 32px
            );
        box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
    }

    .cinema-hero::after {
        content: "🎞️";
        position: absolute;
        right: 2rem;
        top: 0.6rem;
        font-size: 6.5rem;
        opacity: 0.13;
        transform: rotate(-8deg);
    }

    .cinema-kicker {
        display: inline-block;
        padding: 0.35rem 0.75rem;
        margin-bottom: 0.8rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.12);
        color: #fde68a;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.08em;
    }

    .cinema-title {
        margin: 0;
        color: #ffffff;
        font-size: 2.35rem;
        line-height: 1.15;
        font-weight: 900;
    }

    .cinema-subtitle {
        margin-top: 0.85rem;
        margin-bottom: 0;
        color: #dbeafe;
        font-size: 1rem;
        line-height: 1.65;
    }

    /* 섹션 제목 */
    .section-title {
        margin-top: 1.3rem;
        margin-bottom: 0.8rem;
        color: #ffffff;
        font-size: 1.28rem;
        font-weight: 800;
    }

    /* 1위 영화 강조 카드 */
    .winner-card {
        padding: 1.35rem 1.45rem;
        border-radius: 20px;
        border: 1px solid rgba(251, 191, 36, 0.35);
        background:
            linear-gradient(135deg, rgba(120, 53, 15, 0.72), rgba(15, 23, 42, 0.92));
        box-shadow: 0 18px 38px rgba(0, 0, 0, 0.28);
    }

    .winner-rank {
        color: #fbbf24;
        font-size: 0.84rem;
        font-weight: 800;
        letter-spacing: 0.08em;
    }

    .winner-name {
        margin-top: 0.4rem;
        color: #ffffff;
        font-size: 1.85rem;
        font-weight: 900;
    }

    .winner-meta {
        margin-top: 0.65rem;
        color: #e5e7eb;
        font-size: 0.95rem;
    }

    /* 작은 정보 카드 */
    .info-card {
        height: 100%;
        padding: 1rem 1.1rem;
        border-radius: 18px;
        border: 1px solid rgba(255, 255, 255, 0.10);
        background: rgba(15, 23, 42, 0.72);
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.20);
    }

    .info-label {
        color: #94a3b8;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.04em;
    }

    .info-value {
        margin-top: 0.35rem;
        color: #ffffff;
        font-size: 1.25rem;
        font-weight: 800;
    }

    /* 탭과 입력 위젯 */
    div[data-baseweb="tab-list"] {
        gap: 0.5rem;
    }

    button[data-baseweb="tab"] {
        border-radius: 12px;
        padding-left: 1rem;
        padding-right: 1rem;
        background: rgba(255,255,255,0.04);
    }

    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        background-color: rgba(15, 23, 42, 0.78);
    }

    /* 데이터프레임 영역 */
    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 16px;
        overflow: hidden;
    }

    /* Streamlit 기본 메뉴와 푸터를 조금 정리 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 3. 상단 배너
# =========================================================
st.markdown(
    """
    <div class="cinema-hero">
        <div class="cinema-kicker">KOREAN BOX OFFICE DASHBOARD</div>
        <h1 class="cinema-title">🎬 KOBIS 시네마 박스오피스</h1>
        <p class="cinema-subtitle">
            하루의 흥행 순위부터 지정 기간의 누적 관객 TOP 5까지,
            영화관입장권통합전산망 데이터를 한 화면에서 탐색합니다.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 4. 한국 시간 기준 날짜 계산
# =========================================================
seoul_now = datetime.now(ZoneInfo("Asia/Seoul"))
today = seoul_now.date()
yesterday = today - timedelta(days=1)

# KOBIS 일별 박스오피스 서비스의 제공 시작일
min_date = datetime(2003, 11, 11).date()


# =========================================================
# 5. Secrets에서 인증키 불러오기
# =========================================================
try:
    kobis_key = st.secrets["KOBIS_KEY"]
except KeyError:
    st.error(
        "KOBIS 인증키를 찾을 수 없습니다. "
        "Streamlit Cloud의 Secrets에 `KOBIS_KEY`를 등록해 주세요."
    )
    st.stop()


# =========================================================
# 6. 공통 함수
# =========================================================
def format_rank_change(value: int) -> str:
    """
    rankInten 값을 보기 쉬운 표시로 변환합니다.
    양수는 순위 상승, 음수는 순위 하락입니다.
    """
    if value > 0:
        return f"🔺 {value}"
    if value < 0:
        return f"🔽 {abs(value)}"
    return "—"


@st.cache_data(ttl=3600, show_spinner=False)
def load_daily_boxoffice(api_key: str, target_dt: str) -> pd.DataFrame:
    """
    KOBIS 일별 박스오피스 API를 호출해 데이터프레임으로 반환합니다.
    같은 날짜 데이터는 1시간 동안 캐시에 저장합니다.
    """
    api_url = (
        "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
        "boxoffice/searchDailyBoxOfficeList.json"
    )

    params = {
        "key": api_key,
        "targetDt": target_dt,
    }

    try:
        response = requests.get(api_url, params=params, timeout=12)
        response.raise_for_status()

    except requests.exceptions.Timeout as error:
        raise RuntimeError(
            "KOBIS 서버의 응답 시간이 너무 오래 걸립니다. 잠시 후 다시 시도해 주세요."
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
            "KOBIS API 요청 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요."
        ) from error

    try:
        data = response.json()
    except ValueError as error:
        raise RuntimeError(
            "KOBIS 서버에서 올바른 JSON 응답을 받지 못했습니다."
        ) from error

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

    required_columns = [
        "rank",
        "rankInten",
        "movieNm",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt",
        "showCnt",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise RuntimeError(
            "KOBIS 응답에서 필요한 항목을 찾지 못했습니다: "
            + ", ".join(missing_columns)
        )

    df = df[required_columns].copy()

    numeric_columns = [
        "rank",
        "rankInten",
        "audiCnt",
        "audiAcc",
        "scrnCnt",
        "showCnt",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df[numeric_columns] = df[numeric_columns].fillna(0).astype(int)
    df = df.sort_values("rank").reset_index(drop=True)

    return df


def build_daily_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    일별 순위 표에 표시할 데이터프레임을 만듭니다.
    """
    table_df = df.copy()

    table_df["전날 대비"] = table_df["rankInten"].apply(format_rank_change)

    table_df["영화명 표시"] = table_df.apply(
        lambda row: (
            f"{row['movieNm']} 🏆"
            if row["audiAcc"] > 1_000_000
            else row["movieNm"]
        ),
        axis=1,
    )

    table_df = table_df[
        [
            "rank",
            "전날 대비",
            "영화명 표시",
            "openDt",
            "audiCnt",
            "audiAcc",
            "scrnCnt",
        ]
    ].rename(
        columns={
            "rank": "순위",
            "영화명 표시": "영화명",
            "openDt": "개봉일",
            "audiCnt": "관객수",
            "audiAcc": "누적관객",
            "scrnCnt": "스크린수",
        }
    )

    return table_df


@st.cache_data(ttl=3600, show_spinner=False)
def load_period_boxoffice(
    api_key: str,
    start_dt: str,
    end_dt: str,
) -> pd.DataFrame:
    """
    시작일부터 종료일까지 날짜별 API를 호출한 뒤 하나로 합칩니다.

    기간이 너무 길면 API 호출 횟수가 많아지므로
    화면에서는 최대 31일까지 선택하도록 제한합니다.
    """
    start_date = datetime.strptime(start_dt, "%Y%m%d").date()
    end_date = datetime.strptime(end_dt, "%Y%m%d").date()

    all_frames = []
    current_date = start_date

    while current_date <= end_date:
        current_dt = current_date.strftime("%Y%m%d")
        daily_df = load_daily_boxoffice(api_key, current_dt).copy()
        daily_df["targetDate"] = current_date
        all_frames.append(daily_df)

        current_date += timedelta(days=1)

        # 연속 호출 시 서버 부담을 조금 줄이기 위한 짧은 간격입니다.
        time.sleep(0.05)

    if not all_frames:
        raise RuntimeError("선택한 기간의 데이터를 불러오지 못했습니다.")

    return pd.concat(all_frames, ignore_index=True)


def aggregate_period_top5(period_df: pd.DataFrame) -> pd.DataFrame:
    """
    기간 중 영화별 당일 관객수를 합산해 TOP 5를 계산합니다.
    """
    summary = (
        period_df
        .groupby("movieNm", as_index=False)
        .agg(
            기간관객수=("audiCnt", "sum"),
            최고순위=("rank", "min"),
            순위진입일수=("targetDate", "nunique"),
            마지막누적관객=("audiAcc", "max"),
            최대스크린수=("scrnCnt", "max"),
        )
        .sort_values(
            ["기간관객수", "마지막누적관객"],
            ascending=[False, False],
        )
        .head(5)
        .reset_index(drop=True)
    )

    summary.insert(0, "기간순위", range(1, len(summary) + 1))
    summary["영화명"] = summary.apply(
        lambda row: (
            f"{row['movieNm']} 🏆"
            if row["마지막누적관객"] > 1_000_000
            else row["movieNm"]
        ),
        axis=1,
    )

    return summary


# =========================================================
# 7. 주요 화면: 일별 조회 / 기간 TOP 5
# =========================================================
daily_tab, period_tab = st.tabs(
    ["📅 특정 날짜 박스오피스", "🏆 기간 누적 TOP 5"]
)


# =========================================================
# 8. 특정 날짜 박스오피스 화면
# =========================================================
with daily_tab:
    selected_date = st.date_input(
        "조회 날짜를 선택하세요",
        value=yesterday,
        min_value=min_date,
        max_value=yesterday,
        key="daily_date",
        help="오늘 데이터는 아직 집계 전일 수 있어 어제까지만 선택할 수 있습니다.",
    )

    target_dt = selected_date.strftime("%Y%m%d")
    display_date = selected_date.strftime("%Y년 %m월 %d일")

    try:
        with st.spinner(f"{display_date} 박스오피스를 불러오는 중입니다."):
            daily_df = load_daily_boxoffice(kobis_key, target_dt)

    except RuntimeError as error:
        st.error(str(error))
        st.info(
            "인증키, 인터넷 연결, KOBIS 서비스 상태와 선택한 날짜를 확인해 주세요."
        )
        st.stop()

    first_place = daily_df.iloc[0]
    first_name = (
        f"{first_place['movieNm']} 🏆"
        if first_place["audiAcc"] > 1_000_000
        else first_place["movieNm"]
    )

    st.markdown(
        f"""
        <div class="winner-card">
            <div class="winner-rank">BOX OFFICE NO. 1 · {display_date}</div>
            <div class="winner-name">{first_name}</div>
            <div class="winner-meta">
                개봉일 {first_place['openDt']} ·
                당일 관객 {first_place['audiCnt']:,}명 ·
                누적 관객 {first_place['audiAcc']:,}명
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">오늘의 흥행 지표</div>', unsafe_allow_html=True)

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

    with metric_col1:
        st.metric("1위 영화", first_name)

    with metric_col2:
        st.metric("1위 당일 관객", f"{first_place['audiCnt']:,}명")

    with metric_col3:
        st.metric("1위 누적 관객", f"{first_place['audiAcc']:,}명")

    with metric_col4:
        st.metric("1위 스크린", f"{first_place['scrnCnt']:,}개")

    st.markdown('<div class="section-title">일별 박스오피스 순위</div>', unsafe_allow_html=True)

    table_df = build_daily_table(daily_df)

    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "순위": st.column_config.NumberColumn("순위", format="%d위"),
            "전날 대비": st.column_config.TextColumn(
                "전날 대비",
                help="🔺 순위 상승 / 🔽 순위 하락 / — 변동 없음",
            ),
            "관객수": st.column_config.NumberColumn("관객수", format="%d명"),
            "누적관객": st.column_config.NumberColumn("누적관객", format="%d명"),
            "스크린수": st.column_config.NumberColumn("스크린수", format="%d개"),
        },
    )

    st.markdown('<div class="section-title">관객수 상위 5편</div>', unsafe_allow_html=True)

    top5_daily = (
        daily_df
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
        top5_daily,
        x_label="영화명",
        y_label="관객수",
        use_container_width=True,
    )

    st.caption(
        f"조회 기준일: {display_date} · "
        "자료 출처: 영화진흥위원회 KOBIS 영화관입장권통합전산망"
    )


# =========================================================
# 9. 기간 누적 TOP 5 화면
# =========================================================
with period_tab:
    st.markdown(
        """
        <div class="info-card">
            <div class="info-label">기간 집계 방식</div>
            <div class="info-value">영화별 일일 관객수(audiCnt) 합산</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    period_col1, period_col2 = st.columns(2)

    with period_col1:
        start_date = st.date_input(
            "시작일",
            value=yesterday - timedelta(days=6),
            min_value=min_date,
            max_value=yesterday,
            key="period_start",
        )

    with period_col2:
        end_date = st.date_input(
            "종료일",
            value=yesterday,
            min_value=min_date,
            max_value=yesterday,
            key="period_end",
        )

    if start_date > end_date:
        st.error("시작일은 종료일보다 늦을 수 없습니다.")
        st.stop()

    period_days = (end_date - start_date).days + 1

    # 날짜별 API 호출 횟수가 많아지는 것을 방지합니다.
    if period_days > 31:
        st.error(
            "한 번에 조회할 수 있는 기간은 최대 31일입니다. "
            "시작일과 종료일을 다시 선택해 주세요."
        )
        st.stop()

    start_text = start_date.strftime("%Y%m%d")
    end_text = end_date.strftime("%Y%m%d")
    start_display = start_date.strftime("%Y년 %m월 %d일")
    end_display = end_date.strftime("%Y년 %m월 %d일")

    run_period = st.button(
        "🎟️ 기간 TOP 5 집계하기",
        type="primary",
        use_container_width=True,
    )

    if run_period:
        try:
            with st.spinner(
                f"{start_display}부터 {end_display}까지 "
                f"{period_days}일의 데이터를 집계하는 중입니다."
            ):
                period_df = load_period_boxoffice(
                    kobis_key,
                    start_text,
                    end_text,
                )
                period_top5 = aggregate_period_top5(period_df)

        except RuntimeError as error:
            st.error(str(error))
            st.info(
                "기간 안의 일부 날짜 데이터가 없거나 API 요청이 실패했을 수 있습니다."
            )
            st.stop()

        total_period_audience = int(period_df["audiCnt"].sum())
        unique_movies = int(period_df["movieNm"].nunique())
        top_movie = period_top5.iloc[0]

        st.markdown(
            f"""
            <div class="winner-card">
                <div class="winner-rank">PERIOD BOX OFFICE NO. 1</div>
                <div class="winner-name">{top_movie['영화명']}</div>
                <div class="winner-meta">
                    {start_display} ~ {end_display} ·
                    기간 관객 {top_movie['기간관객수']:,}명 ·
                    순위 진입 {top_movie['순위진입일수']}일
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section-title">기간 요약</div>', unsafe_allow_html=True)

        summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

        with summary_col1:
            st.metric("집계 기간", f"{period_days}일")

        with summary_col2:
            st.metric("전체 관객수", f"{total_period_audience:,}명")

        with summary_col3:
            st.metric("등장 영화 수", f"{unique_movies:,}편")

        with summary_col4:
            st.metric("TOP 1 관객수", f"{top_movie['기간관객수']:,}명")

        st.markdown('<div class="section-title">기간 누적 관객 TOP 5</div>', unsafe_allow_html=True)

        period_chart = (
            period_top5
            [["영화명", "기간관객수"]]
            .set_index("영화명")
        )

        st.bar_chart(
            period_chart,
            x_label="영화명",
            y_label="기간 누적 관객수",
            use_container_width=True,
        )

        st.markdown('<div class="section-title">TOP 5 상세 정보</div>', unsafe_allow_html=True)

        period_table = period_top5[
            [
                "기간순위",
                "영화명",
                "기간관객수",
                "최고순위",
                "순위진입일수",
                "마지막누적관객",
                "최대스크린수",
            ]
        ].copy()

        st.dataframe(
            period_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "기간순위": st.column_config.NumberColumn(
                    "기간 순위",
                    format="%d위",
                ),
                "기간관객수": st.column_config.NumberColumn(
                    "기간 관객수",
                    format="%d명",
                ),
                "최고순위": st.column_config.NumberColumn(
                    "기간 중 최고 순위",
                    format="%d위",
                ),
                "순위진입일수": st.column_config.NumberColumn(
                    "순위 진입 일수",
                    format="%d일",
                ),
                "마지막누적관객": st.column_config.NumberColumn(
                    "누적 관객",
                    format="%d명",
                ),
                "최대스크린수": st.column_config.NumberColumn(
                    "최대 스크린수",
                    format="%d개",
                ),
            },
        )

        st.caption(
            f"집계 기간: {start_display} ~ {end_display} · "
            "기간 관객수는 각 날짜의 audiCnt를 영화별로 합산한 값입니다."
        )

    else:
        st.info(
            "시작일과 종료일을 선택한 뒤 "
            "`기간 TOP 5 집계하기` 버튼을 눌러 주세요."
        )
