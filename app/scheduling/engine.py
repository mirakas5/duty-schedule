"""공정 당직 배정 엔진 — 순수 모듈 (DB/HTTP 비의존).

Design Ref: §3.5 — 두 축의 공정성을 동시에 만족시키는 결정적 배정 알고리즘
  - FR-05  [총량 공정성]   : 인원별 누적 배정 횟수 편차 최소 (하드 보장: diff ≤ 1)
  - FR-05b [간격 공정성]   : 마지막 근무 이후 경과 주차가 큰 인원 우선 (소프트 최적화)
  - FR-04  [서로 다른 사람] : 같은 주의 새벽/야간은 항상 다른 사람

핵심 설계:
  점수 = w_total * (max_total - total) * DOM + w_gap * (week_idx - last_idx)
  여기서 DOM = (전체 주차 + 1) 로 스케일하여, 총량 1차이가 어떤 간격 차이보다
  항상 우선되도록 만든다 → 총량 편차 ≤ 1 을 보장하면서, 동률(같은 총량) 안에서는
  간격이 큰(오래 쉰) 인원을 우선해 간격 공정성을 달성한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple, Union


@dataclass(frozen=True)
class Member:
    id: int
    name: str
    sort_order: int = 0


@dataclass
class Assignment:
    week_index: int
    dawn: Member
    night: Member


@dataclass
class _State:
    total: int = 0
    dawn_count: int = 0
    night_count: int = 0
    last_idx: int = -1  # 미배정 상태(아직 한 번도 안 함)


def assign(
    members: List[Member],
    weeks: Union[int, Sequence[int]],
    w_total: float = 1.0,
    w_gap: float = 1.0,
    initial: Optional[Dict[int, Tuple[int, int]]] = None,
) -> List[Assignment]:
    """주차 순서대로 새벽/야간 담당자를 배정한다(과거 이력 시드 지원).

    Args:
        members: 배정 대상(활성) 인원. 2명 이상.
        weeks:   배정할 주. int이면 0..n-1 인덱스, Sequence[int]이면 절대 주차 키
                 (week_ordinal — 과거/미래 구간을 같은 시간축으로 잇기 위함).
        w_total: 총량 공정성 가중치(기본 1.0).
        w_gap:   간격 공정성 가중치(기본 1.0).
        initial: {member_id: (누적_총횟수, 마지막_근무_주차키)} — 과거 이력 시드.
                 5월 생성 후 6월을 따로 생성해도 누적 형평성을 잇기 위해 사용.

    Returns:
        Assignment 목록. week_index는 weeks 내 0-based 위치(주차 매핑용).

    Raises:
        ValueError: 활성 멤버 2명 미만 또는 weeks가 음수일 때.
    """
    if isinstance(weeks, int):
        if weeks < 0:
            raise ValueError("weeks must be >= 0")
        week_keys: List[int] = list(range(weeks))
    else:
        week_keys = list(weeks)

    if not week_keys:
        return []
    if len(members) < 2:
        raise ValueError("배정에는 활성 멤버가 2명 이상 필요합니다")

    state: Dict[int, _State] = {m.id: _State() for m in members}

    # 과거 이력 시드
    if initial:
        for mid, (tot, last) in initial.items():
            if mid in state:
                state[mid].total = tot
                state[mid].last_idx = last

    first_key = week_keys[0]
    # 이력 없는(시드 안 된) 멤버는 '직전 주' 기준으로 두어 신규자가 과도 우선되지 않게 함
    seeded_ids = set(initial.keys()) if initial else set()
    for m in members:
        if m.id not in seeded_ids:
            state[m.id].last_idx = first_key - 1

    # 총량 1차이가 어떤 간격 차이보다 항상 우선되도록 동적 스케일
    min_last = min(state[m.id].last_idx for m in members)
    max_key = week_keys[-1]
    dom = (max_key - min_last) + 1

    assignments: List[Assignment] = []

    for pos, key in enumerate(week_keys):
        max_total = max(state[m.id].total for m in members)

        def score(m: Member) -> float:
            st = state[m.id]
            total_term = w_total * (max_total - st.total) * dom
            gap_term = w_gap * (key - st.last_idx)
            return total_term + gap_term

        ranked = sorted(
            members,
            key=lambda m: (
                -score(m),
                state[m.id].total,
                state[m.id].last_idx,
                m.sort_order,
                m.id,
            ),
        )
        pick_a, pick_b = ranked[0], ranked[1]  # 서로 다른 사람 보장 (FR-04)

        dawn_member, night_member = _balance_slots(pick_a, pick_b, state)
        assignments.append(Assignment(week_index=pos, dawn=dawn_member, night=night_member))

        ds = state[dawn_member.id]
        ds.total += 1
        ds.dawn_count += 1
        ds.last_idx = key

        ns = state[night_member.id]
        ns.total += 1
        ns.night_count += 1
        ns.last_idx = key

    return assignments


def _balance_slots(a: Member, b: Member, state: dict) -> Tuple[Member, Member]:
    """두 인원에게 (새벽, 야간) 슬롯을 배정. 각자의 dawn/night 누적 불균형 합이
    더 작아지는 조합을 선택한다. 동률이면 (a=새벽, b=야간)으로 결정적 처리."""
    sa, sb = state[a.id], state[b.id]

    # 옵션1: a=새벽, b=야간
    imb1 = abs((sa.dawn_count + 1) - sa.night_count) + abs(sb.dawn_count - (sb.night_count + 1))
    # 옵션2: a=야간, b=새벽
    imb2 = abs(sa.dawn_count - (sa.night_count + 1)) + abs((sb.dawn_count + 1) - sb.night_count)

    if imb2 < imb1:
        return b, a
    return a, b


# ── 통계 유틸 (검증/통계 화면용) ───────────────────────────────────

def fairness_stats(members: List[Member], assignments: List[Assignment]) -> dict:
    """배정 결과의 공정성 통계: 총량(min/max/diff) + 간격(mean/stdev)."""
    counts = {m.id: 0 for m in members}
    dawn = {m.id: 0 for m in members}
    night = {m.id: 0 for m in members}
    last_seen: dict = {m.id: None for m in members}
    gaps: List[int] = []

    for a in assignments:
        for m, slot in ((a.dawn, "dawn"), (a.night, "night")):
            counts[m.id] += 1
            if slot == "dawn":
                dawn[m.id] += 1
            else:
                night[m.id] += 1
            if last_seen[m.id] is not None:
                gaps.append(a.week_index - last_seen[m.id])
            last_seen[m.id] = a.week_index

    totals = list(counts.values())
    lo, hi = (min(totals), max(totals)) if totals else (0, 0)

    if gaps:
        mean = sum(gaps) / len(gaps)
        var = sum((g - mean) ** 2 for g in gaps) / len(gaps)
        stdev = var ** 0.5
    else:
        mean = stdev = 0.0

    return {
        "per_member": {
            m.id: {"name": m.name, "total": counts[m.id], "dawn": dawn[m.id], "night": night[m.id]}
            for m in members
        },
        "total": {"min": lo, "max": hi, "diff": hi - lo},
        "gap": {"mean_weeks": round(mean, 2), "stdev": round(stdev, 2)},
    }
