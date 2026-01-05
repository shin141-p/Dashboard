import numpy as np
import pandas as pd

def add_cumulative_sleep_debt(
    df: pd.DataFrame,
    actual_col: str,
    target_sleep_hours: float,
    mode: str = "offset",          # "offset" or "no_offset"
    output_col: str = "sleep_debt_cum",
    debt_day_col: str = "sleep_debt_day",
) -> pd.DataFrame:
    """
    Add cumulative sleep debt columns.

    Parameters
    ----------
    df : pd.DataFrame
    actual_col : str
        Column name for actual sleep duration in hours.
    target_sleep_hours : float
        Target sleep duration in hours.
    mode : str
        "no_offset": accumulate only shortfalls (oversleep does NOT repay)
        "offset": oversleep repays debt, but debt never goes below 0
    output_col : str
        Name for cumulative debt column.
    debt_day_col : str
        Name for per-day debt column (for inspection).

    Returns
    -------
    pd.DataFrame
        Copy of df with added columns:
          - debt_day_col
          - output_col
    """
    out = df.copy()

    actual = pd.to_numeric(out[actual_col], errors="coerce")
    balance = target_sleep_hours - actual  # +: shortfall, -: oversleep

    if mode == "no_offset":
        # 不足だけ積む（超過は無視）
        out[debt_day_col] = balance.clip(lower=0)
        out[output_col] = out[debt_day_col].cumsum()

    elif mode == "offset":
        # 不足は積む、超過で返済（ただし0未満にしない）
        # 逐次計算が必要（clipの位置が重要）
        debt = []
        running = 0.0
        for x in balance:
            if pd.isna(x):
                debt.append(np.nan)
                continue
            running = max(0.0, running + x)
            debt.append(running)

        out[output_col] = debt
        # 参考：その日の「不足分」だけも欲しければ（任意）
        out[debt_day_col] = balance.clip(lower=0)

    else:
        raise ValueError("mode must be 'offset' or 'no_offset'")

    return out
