"""배정 엔진 단위 테스트 — Design §8.2 L0 시나리오.

검증 속성:
  1. 총량 편차 ≤ 1            (FR-05)
  2. 간격(휴식 주기) 균일      (FR-05b)
  3. 같은 주 새벽 ≠ 야간       (FR-04)
  4. 결정성(같은 입력 → 동일)
  5. 멤버 1명 → 거부
"""
import pytest

from app.scheduling.engine import Member, assign, fairness_stats


def make_members(n: int):
    return [Member(id=i + 1, name=f"M{i+1}", sort_order=i) for i in range(n)]


# 1) 총량 편차 ≤ 1 ----------------------------------------------------
@pytest.mark.parametrize("n,weeks", [(2, 52), (5, 52), (6, 52), (7, 52), (10, 52), (3, 100), (8, 13)])
def test_total_count_diff_within_one(n, weeks):
    members = make_members(n)
    res = assign(members, weeks)
    stats = fairness_stats(members, res)
    assert stats["total"]["diff"] <= 1, stats["total"]


# 2) 간격 공정성: 간격 표준편차가 작아야 함 --------------------------
def test_gap_uniformity():
    members = make_members(10)
    res = assign(members, 52, seed=42)
    stats = fairness_stats(members, res)
    # 10명·52주 → 각자 약 10~11회, 평균 간격 ~5주. 표준편차가 과도하지 않아야 함.
    assert stats["gap"]["stdev"] <= 1.5, stats["gap"]


def test_gap_no_immediate_repeat_when_enough_members():
    """멤버가 충분하면(>=3) 같은 사람이 연속 주에 다시 배정되지 않아야 한다."""
    members = make_members(6)
    res = assign(members, 52, seed=7)
    last_idx = {}
    for a in res:
        for m in (a.dawn, a.night):
            if m.id in last_idx:
                assert a.week_index - last_idx[m.id] >= 1
            last_idx[m.id] = a.week_index
    # 6명에서 한 주 2명 소비 → 다음 주 즉시 재등장은 없어야 정상
    repeats = 0
    seen_prev = set()
    for a in res:
        cur = {a.dawn.id, a.night.id}
        repeats += len(cur & seen_prev)
        seen_prev = cur
    assert repeats == 0


# 3) 같은 주 새벽 ≠ 야간 ----------------------------------------------
def test_dawn_and_night_are_different():
    members = make_members(4)
    res = assign(members, 52)
    for a in res:
        assert a.dawn.id != a.night.id


# 4) 시드 재현성 / 랜덤성 ----------------------------------------------
def test_same_seed_reproducible():
    """같은 시드 → 동일 결과 (감사/재현 가능)."""
    r1 = assign(make_members(7), 52, seed=123)
    r2 = assign(make_members(7), 52, seed=123)
    assert [(a.week_index, a.dawn.id, a.night.id) for a in r1] == \
           [(a.week_index, a.dawn.id, a.night.id) for a in r2]


def test_different_seed_changes_order():
    """다른 시드 → 첫 주 배정 순서가 달라진다 (엑셀 순서 고정 방지)."""
    first = set()
    for s in range(20):
        r = assign(make_members(8), 52, seed=s)
        first.add((r[0].dawn.id, r[0].night.id))
    # 20개 시드 중 첫 주 조합이 최소 2종류 이상이면 랜덤이 동작하는 것
    assert len(first) >= 2


def test_total_diff_holds_regardless_of_seed():
    """시드와 무관하게 총량 편차 ≤ 1 (공정성 보장 불변)."""
    for s in range(10):
        members = make_members(7)
        res = assign(members, 52, seed=s)
        assert fairness_stats(members, res)["total"]["diff"] <= 1


# 5) 검증 에러 ---------------------------------------------------------
def test_single_member_rejected():
    with pytest.raises(ValueError):
        assign(make_members(1), 52)


def test_zero_weeks_returns_empty():
    assert assign(make_members(5), 0) == []


# 7) 과거 이력 시드: 절대 주차키 + initial -----------------------------
def test_assign_with_absolute_week_keys():
    members = make_members(5)
    res = assign(members, [100, 101, 102, 103, 104])  # 절대 키도 동작
    assert len(res) == 5
    assert all(a.dawn.id != a.night.id for a in res)


def test_seed_deprioritizes_high_total_members():
    """과거에 많이 한 사람(시드 total 큼)은 새 구간에서 뒤로 밀린다(catch-up)."""
    members = make_members(4)  # ids 1..4
    # 1,2는 과거 10회 + 최근 근무(99), 3,4는 이력 없음
    initial = {1: (10, 99), 2: (10, 99)}
    res = assign(members, list(range(100, 104)), initial=initial)
    # 첫 주는 이력 없는 3,4가 배정돼야 함
    first = {res[0].dawn.id, res[0].night.id}
    assert first == {3, 4}, first


def test_incremental_generation_keeps_cumulative_fairness():
    """구간을 둘로 나눠 생성(2차에 1차 이력 시드)해도 누적 총량 편차 ≤ 1."""
    members = make_members(6)

    # 1차: 키 0..25
    r1 = assign(members, list(range(0, 26)))
    total = {m.id: 0 for m in members}
    last = {}
    for a in r1:
        for m in (a.dawn, a.night):
            total[m.id] += 1
            last[m.id] = a.week_index  # 위치=키 (0..25)

    # 2차: 키 26..51, 1차 이력을 시드
    initial = {mid: (total[mid], last[mid]) for mid in total}
    r2 = assign(members, list(range(26, 52)), initial=initial)
    for a in r2:
        for m in (a.dawn, a.night):
            total[m.id] += 1

    vals = list(total.values())
    assert max(vals) - min(vals) <= 1, total


# 6) 슬롯 균형: 새벽/야간 횟수도 어느 정도 균등 -----------------------
def test_slot_balance_reasonable():
    members = make_members(6)
    res = assign(members, 60, seed=5)
    stats = fairness_stats(members, res)
    for mid, info in stats["per_member"].items():
        # 개인의 새벽/야간 횟수 차이가 과도하지 않아야 함
        assert abs(info["dawn"] - info["night"]) <= 2, (mid, info)
