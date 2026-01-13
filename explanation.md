# 睡眠ダッシュボード 計算ロジック解説

このダッシュボードで使用されている主要な指標の計算ロジックについて解説します。

---

## 1. 睡眠時間 (Sleep Duration)

夜間の睡眠時間を算出します。

- **入力**: `就寝時間` (Bedtime), `起床時間` (Waketime)
- **計算式**:
  $$
  \text{Sleep Duration (h)} = \frac{\text{Waketime} - \text{Bedtime}}{3600}
  $$
- **日付またぎの処理**:
  - `起床時間` が `就寝時間` より早い時刻（例: 就寝 23:00, 起床 07:00）の場合、起床時間は**翌日**であるとみなして計算します。

## 2. 昼寝時間 (Nap Duration)

昼寝の時間を算出します。

- **入力**: `昼寝の時間` (Naptime)
- **計算式**:
  $$
  \text{Nap Duration (h)} = \frac{\text{Naptime (min)}}{60}
  $$
  ※ 入力された時刻（例: 01:00:00）を「1 時間 0 分」の長さとして扱います。

## 3. 合計睡眠時間 (Total Sleep)

睡眠負債の計算に使用される、1 日の総睡眠時間です。

- **計算式**:
  $$
  \text{Total Sleep} = \text{Sleep Duration (夜間)} + \text{Nap Duration (昼寝)}
  $$

## 4. 睡眠負債 (Sleep Debt)

理想の睡眠時間に対する不足分の累積値を算出します。

- **入力**: `理想の睡眠時間` (Target), `合計睡眠時間` (Total Sleep)
- **単日の収支 (Balance)**:

  $$
  \text{Balance}_i = \text{Target} - \text{Total Sleep}_i
  $$

  - 正の値: 睡眠不足
  - 負の値: 睡眠超過（寝だめ）

- **累積負債 (Cumulative Debt)**:
  $$
  \text{Debt}_i = \max(0, \text{Debt}_{i-1} + \text{Balance}_i)
  $$
  - **Offset Mode**: 目標を超えて寝た場合（Balance < 0）、その分だけ過去の負債から差し引きます（返済）。
  - ただし、負債が 0 未満（貯金）になることはありません（下限 0）。

## 5. 睡眠スコア (Sleep Fit Score)

設定された「推奨睡眠時間帯」の間に、どれだけ実際に寝ていたかを表す一致度です（効率や質ではなく、スケジュールの遵守率）。

- **入力**:
  - 推奨時間帯 ($T_{start}$ 〜 $T_{end}$)
  - 実際の睡眠時間帯 ($S_{start}$ 〜 $S_{end}$)
- **タイムライン補正**:
  - 正午(12:00)を区切りとした 24 時間軸（12:00 〜 翌 12:00）に変換して計算します。
- **計算式**:
  $$
  \text{Score} (\%) = \left( \frac{\text{Overlap Duration}}{\text{Actual Sleep Duration}} \right) \times 100
  $$
  - **Overlap Duration**: 推奨時間帯と実際の睡眠時間帯が重なっている時間の長さ。
  - つまり、「実際に寝た時間のうち、推奨時間帯からはみ出さずに寝ていた割合」を示します。
