import urllib.request
import urllib.error
from html.parser import HTMLParser
import csv
import ssl

class JMAHTMLParser(HTMLParser):
    """
    気象庁のHTMLテーブルを解析するためのパーサクラスです。
    HTMLParserを継承して、テーブルの行とセルのデータを抽出します。
    """
    def __init__(self):
        super().__init__()
        self.in_row = False          # 行(tr)の中にいるかどうかのフラグ
        self.current_row_data = []   # 現在処理中の行のデータリスト
        self.current_cell_text = ""  # 現在処理中のセルのテキスト
        self.rows = []               # 全行のデータを格納するリスト
        self.in_cell = False         # セル(td/th)の中にいるかどうかのフラグ

    def handle_starttag(self, tag, attrs):
        # <tr>タグの開始：新しい行の始まり
        if tag == 'tr':
            self.in_row = True
            self.current_row_data = []
        # <td>または<th>タグの開始：新しいセルの始まり
        elif tag in ('td', 'th'):
            if self.in_row:
                self.in_cell = True
                self.current_cell_text = ""

    def handle_endtag(self, tag):
        # <tr>タグの終了：行の終わり。データをrowsに追加
        if tag == 'tr':
            if self.in_row:
                self.in_row = False
                if self.current_row_data:
                    self.rows.append(self.current_row_data)
        # <td>または<th>タグの終了：セルの終わり。テキストを行データに追加
        elif tag in ('td', 'th'):
            if self.in_cell:
                self.in_cell = False
                self.current_row_data.append(self.current_cell_text.strip())

    def handle_data(self, data):
        # セル内のテキストデータを取得
        if self.in_cell:
            self.current_cell_text += data

def scrape_tokyo_humidity(year, month):
    """
    指定された年と月の東京都の日別平均相対湿度をスクレイピングします。
    
    Args:
        year (int): 対象の年
        month (int): 対象の月
        
    Returns:
        list: (日, 湿度) のタプルのリスト。失敗した場合はNone。
    """
    # 東京 (prec_no=44, block_no=47662) の日別データのURL
    # view= は表示オプションですが、空でもデフォルト表示になります
    url = f"https://www.data.jma.go.jp/obd/stats/etrn/view/daily_s1.php?prec_no=44&block_no=47662&year={year}&month={month}&day=&view="
    print(f"データを取得中: {url}")

    # SSL証明書エラーを回避するためのコンテキストを作成（一部の環境で必要）
    ssl_context = ssl._create_unverified_context()

    try:
        # URLを開いてHTMLコンテンツを取得
        with urllib.request.urlopen(url, context=ssl_context) as response:
            html_content = response.read().decode('utf-8')
        
        # HTMLパーサを初期化してデータを解析
        parser = JMAHTMLParser()
        parser.feed(html_content)
        
        data = []
        # 解析された行データをループ処理して、必要なデータを抽出
        # データの構造（列のインデックス）は気象庁のページ構造に基づいています
        # 列0: 日付
        # ...
        # 列9: 平均湿度 (0始まりのインデックスで9番目、つまり10列目)
        
        for row in parser.rows:
            # 行の列数が十分か、かつ最初の列が数値（日付）かを確認
            if len(row) > 10:
                try:
                    # 日付の抽出（余計な文字が含まれる場合があるので数字のみ抽出）
                    day_str = ''.join(filter(str.isdigit, row[0]))
                    if not day_str:
                        continue
                    day = int(day_str)
                    
                    # 湿度はインデックス9にあります
                    humidity_str = row[9]
                    # 気温はインデックス6にあります
                    temp_str = row[6]
                    
                    # 湿度の文字列が空でないか確認
                    if not humidity_str:
                        continue
                        
                    # 数値部分を抽出（品質情報フラグ ')' や ']' などを除去するため）
                    def extract_float(val_str):
                        clean_str = ""
                        for char in val_str:
                            if char.isdigit() or char == '.' or char == '-': # マイナス記号も考慮
                                clean_str += char
                            elif char == ' ':
                                continue
                            else:
                                pass
                        try:
                            return float(clean_str)
                        except ValueError:
                            return None

                    humidity = extract_float(humidity_str)
                    temperature = extract_float(temp_str)
                    
                    if humidity is not None and temperature is not None:
                        data.append((day, humidity, temperature))
                        
                except ValueError:
                    continue
        
        return data

    except urllib.error.URLError as e:
        print(f"URLエラーが発生しました: {e}")
        return None

if __name__ == "__main__":
    # 例: 2024年11月のデータを取得
    year = 2025
    month = 10
    
    print(f"{year}年{month}月の東京都の湿度・気温データをスクレイピングします...")
    result = scrape_tokyo_humidity(year, month)
    
    if result:
        print("\n日 | 平均湿度 (%) | 平均気温 (℃)")
        print("---|--------------|-------------")
        for day, hum, temp in result:
            print(f"{day:2} | {hum:<12} | {temp}")
            
        # CSVファイルに保存
        filename = f"tokyo_humidity_{year}_{month}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Day', 'Avg_Humidity', 'Avg_Temperature'])
            writer.writerows(result)
        print(f"\nファイルに保存しました: {filename}")
    else:
        print("データが見つからないか、エラーが発生しました。")
