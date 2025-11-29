import pandas as pd
import numpy as np

def generate_dummy_data():
    # 湿度データを読み込む
    humidity_df = pd.read_csv('tokyo_humidity_2025_10.csv')
    
    # 湿度データが存在する日数分だけ生成
    days = humidity_df['Day'].values
    humidities = humidity_df['Avg_Humidity'].values
    
    # パラメータ設定
    target_mean = 7.0
    correlation_strength = -0.05 # 湿度が上がると睡眠時間が少し下がる（またはその逆）適当な係数
    noise_std = 1.0 # ノイズの標準偏差
    
    # 湿度の平均からの偏差
    humidity_mean = np.mean(humidities)
    humidity_deviation = humidities - humidity_mean
    
    # 睡眠時間を生成: 基本値 + 湿度による変動 + ノイズ
    # 湿度が高いと不快で睡眠時間が減る...かもしれないという仮定で負の相関にしてみる
    # ただし「中程度の相関」とのことなので、係数とノイズを調整
    
    # 正規化して相関を持たせる
    # sleep = mean + (humidity_norm * corr + noise * sqrt(1-corr^2)) * std
    # ここでは簡易的に線形結合で作る
    
    base_sleep = target_mean + (humidity_deviation * correlation_strength)
    noise = np.random.normal(0, noise_std, len(days))
    
    raw_sleep_times = base_sleep + noise
    
    # 平均を7.0に補正
    current_mean = np.mean(raw_sleep_times)
    raw_sleep_times = raw_sleep_times - current_mean + target_mean
    
    # 15分刻み (0.25時間) に丸める
    sleep_times = np.round(raw_sleep_times * 4) / 4
    
    # 0以下や24以上にならないようにクリップ
    sleep_times = np.clip(sleep_times, 0, 24)
    
    df = pd.DataFrame({
        'Day': days,
        'Sleep_Time': sleep_times
    })
    
    # 確認用: 相関係数と平均
    corr = np.corrcoef(humidities, sleep_times)[0, 1]
    print(f"平均睡眠時間: {np.mean(sleep_times):.2f} 時間")
    print(f"湿度との相関係数: {corr:.2f}")
    
    return df

if __name__ == "__main__":
    df = generate_dummy_data()
    
    # CSVとして保存
    output_file = 'dummy_sleep_data.csv'
    df.to_csv(output_file, index=False)
    print(f"\n{output_file} に保存しました。")
