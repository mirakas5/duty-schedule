"""평일/공휴일 계산 및 주(週) 그룹화 — 순수 모듈 (DB/HTTP 비의존).

Design Ref: §3.5, §1.1 — calendar.workdays / calendar.weeks
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Set


@dataclass
class Week:
    """ISO 주 단위 근무 묶음. 그 주의 실제 당직 평일(공휴일 제외) 목록을 가진다."""
    week_start: date          # 해당 ISO 주의 월요일
    iso_year: int
    iso_week: int
    workdays: List[date] = field(default_factory=list)


def one_year_end(start: date) -> date:
    """start로부터 1년(다음 해 같은 날 전날)까지를 포함 종료일로 반환. 윤년 2/29 보정."""
    try:
        next_year_same_day = start.replace(year=start.year + 1)
    except ValueError:
        # 2/29 → 다음 해 2/28 로 보정
        next_year_same_day = start.replace(year=start.year + 1, day=28)
    return next_year_same_day - timedelta(days=1)


def workdays_in_range(start: date, end_inclusive: date, holidays: Set[date]) -> List[date]:
    """[start, end_inclusive] 구간의 평일(월~금)에서 공휴일을 제외한 날짜 목록.

    Plan SC: FR-03/FR-06 — 평일만, 수동 지정 공휴일 제외.
    """
    days: List[date] = []
    cur = start
    while cur <= end_inclusive:
        # weekday(): 월=0 ... 금=4, 토=5, 일=6
        if cur.weekday() < 5 and cur not in holidays:
            days.append(cur)
        cur += timedelta(days=1)
    return days


def group_into_weeks(workdays: List[date]) -> List[Week]:
    """당직 평일들을 ISO 주(연도+주차) 단위로 묶는다.

    Plan SC: FR-04/FR-06b — 주 단위 고정. 공휴일이 낀 주는 평일이 줄어든 채 1주로 유지
    (예: 공휴일 1일 → workdays 4개). 평일이 0인 주는 생성되지 않는다.
    """
    buckets: dict[tuple, Week] = {}
    order: List[tuple] = []
    for d in workdays:
        iso = d.isocalendar()
        key = (iso[0], iso[1])  # (iso_year, iso_week)
        if key not in buckets:
            # 해당 ISO 주의 월요일
            monday = date.fromisocalendar(iso[0], iso[1], 1)
            buckets[key] = Week(week_start=monday, iso_year=iso[0], iso_week=iso[1])
            order.append(key)
        buckets[key].workdays.append(d)
    return [buckets[k] for k in order]


def build_weeks(start: date, end_inclusive: date, holidays: Set[date]) -> List[Week]:
    """[start, end_inclusive] 구간의 당직 주 목록 (평일 산출 → 주 그룹화)."""
    workdays = workdays_in_range(start, end_inclusive, holidays)
    return group_into_weeks(workdays)


def build_year_weeks(start: date, holidays: Set[date]) -> List[Week]:
    """start부터 1년치 당직 주 목록 (build_weeks의 1년 편의 래퍼)."""
    return build_weeks(start, one_year_end(start), holidays)


def week_ordinal(monday: date) -> int:
    """월요일 날짜를 연속 정수 주차 키로 변환(과거/미래 구간을 같은 시간축으로 연결).

    week_start는 항상 ISO 주 월요일이므로 연속 월요일은 키가 1씩 증가한다.
    """
    return monday.toordinal() // 7
