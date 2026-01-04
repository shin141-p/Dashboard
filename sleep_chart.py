import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 6))

for _, r in df.iterrows():
    day = r["day"]
    b = r["bedtime_hour"]
    w = r["wake_time_hour"]

    if r["cross_day_wake"] == 0:
        # 同日
        ax.bar(
            day,
            height=w - b,
            bottom=b,
            width=0.8
        )
    else:
        # 日付跨ぎ（2本）
        ax.bar(
            day,
            height=24 - b,
            bottom=b,
            width=0.8
        )
        ax.bar(
            day + 1,
            height=w,
            bottom=0,
            width=0.8
        )

ax.set_ylim(0, 24)
ax.set_xlabel("Day")
ax.set_ylabel("Hour")
ax.invert_yaxis()  # 上が0時
plt.show()
