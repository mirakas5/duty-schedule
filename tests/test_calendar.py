"""캘린더(평일/공휴일/주 그룹화) 단위 테스트 — Design §8.2 L0 (#6, #7)."""
from datetime import date

from app.scheduling.calendar import (
    build_weeks,
    build_year_weeks,
    group_into_weeks,
    one_year_end,
    week_ordinal,
    workdays_in_range,
)


def test_workdays_exclude_weekends():
    # 2026-07-01(수) ~ 2026-07-07(화)
    days = workdays_in_range(date(2026, 7, 1), date(2026, 7, 7), set())
    # 7/4(토), 7/5(일) 제외
    assert date(2026, 7, 4) not in days
    assert date(2026, 7, 5) not in days
    assert date(2026, 7, 1) in days
    assert date(2026, 7, 6) in days
    assert all(d.weekday() < 5 for d in days)


def test_workdays_exclude_holidays():
    holidays = {date(2026, 7, 1)}  # 수요일 공휴일 지정
    days = workdays_in_range(date(2026, 7, 1), date(2026, 7, 3), holidays)
    assert date(2026, 7, 1) not in days
    assert date(2026, 7, 2) in days
    assert date(2026, 7, 3) in days


def test_holiday_week_keeps_four_workdays():
    """공휴일 1일이 낀 주 → 그 주 workdays 4개 (주 단위 고정, FR-06b)."""
    # 2026-07-06(월)~07-10(금) 한 주, 07-08(수) 공휴일
    holidays = {date(2026, 7, 8)}
    days = workdays_in_range(date(2026, 7, 6), date(2026, 7, 10), holidays)
    weeks = group_into_weeks(days)
    assert len(weeks) == 1
    assert len(weeks[0].workdays) == 4


def test_partial_first_week_still_one_assignment():
    """시작일이 주 중간(금요일)이어도 그 부분 주가 1개 주로 그룹화된다."""
    # 2026-07-03 은 금요일
    assert date(2026, 7, 3).weekday() == 4
    days = workdays_in_range(date(2026, 7, 3), date(2026, 7, 3), set())
    weeks = group_into_weeks(days)
    assert len(weeks) == 1
    assert weeks[0].workdays == [date(2026, 7, 3)]


def test_one_year_end_normal():
    assert one_year_end(date(2026, 7, 1)) == date(2027, 6, 30)


def test_one_year_end_leap_day():
    # 2024-02-29 시작 → 다음 해 2/28 보정 후 전날
    assert one_year_end(date(2024, 2, 29)) == date(2025, 2, 27)


def test_build_year_weeks_about_52():
    weeks = build_year_weeks(date(2026, 7, 1), set())
    # 1년 → 약 52~53주
    assert 50 <= len(weeks) <= 54
    # 모든 주는 평일이 1개 이상
    assert all(len(w.workdays) >= 1 for w in weeks)


def test_build_weeks_arbitrary_range():
    # 2026년 5월 한 달
    weeks = build_weeks(date(2026, 5, 1), date(2026, 5, 31), set())
    assert all(date(2026, 5, 1) <= d <= date(2026, 5, 31) for w in weeks for d in w.workdays)
    assert 4 <= len(weeks) <= 6


def test_week_ordinal_consecutive_mondays():
    # 연속 월요일은 키가 1씩 증가
    w1 = week_ordinal(date(2026, 5, 4))   # 월
    w2 = week_ordinal(date(2026, 5, 11))  # 다음 월
    w3 = week_ordinal(date(2026, 5, 18))
    assert w2 - w1 == 1
    assert w3 - w2 == 1
