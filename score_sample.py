import pandas as pd

def hhmm_to_min(hhmm: str) -> int:
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m

def interval_overlap(a1, a2, b1, b2):
    return max(0, min(a2, b2) - max(a1, b1))

def add_sleep_fit_score(df: pd.DataFrame, target_start="23:30", target_end="08:00"):
    ts = hhmm_to_min(target_start)
    te = hhmm_to_min(target_end)
    if te <= ts:
        te += 1440  # 想定区間が跨ぐ

    scores = []
    overlaps = []
    actuals = []

    for _, r in df.iterrows():
        bs = hhmm_to_min(r["bedtime_hhmm"])
        we = hhmm_to_min(r["wake_time_hhmm"])

        # 実睡眠区間が跨ぐ場合（cross_day_wake=1）または we<=bs を保険で処理
        if int(r.get("cross_day_wake", 0)) == 1 or we <= bs:
            we += 1440

        actual = we - bs
        overlap = interval_overlap(bs, we, ts, te)

        score = 0 if actual == 0 else 100 * overlap / actual

        actuals.append(actual)
        overlaps.append(overlap)
        scores.append(score)

    df = df.copy()
    df["actual_sleep_min"] = actuals
    df["target_overlap_min"] = overlaps
    df["sleep_fit_score"] = [round(s, 1) for s in scores]
    return df
