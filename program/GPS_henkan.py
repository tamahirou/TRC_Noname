import re
import csv

def hex_to_nmea(hex_string):
    """16進数文字列をNMEA文字列に変換"""
    try:
        bytes_data = bytes.fromhex(hex_string)
        return bytes_data.decode('ascii')
    except:
        return None

def parse_gngga(nmea_sentence):
    """GNGGA文から緯度と経度を抽出"""
    parts = nmea_sentence.split(',')
    
    if not parts[0].endswith('GNGGA'):
        return None
    
    # 緯度の解析 (例: 3538.964597,N)
    if len(parts) > 3 and parts[2] and parts[3]:
        lat_raw = parts[2]  # 3538.964597
        lat_dir = parts[3]  # N
        
        # DDMMmm.mmmm形式をDD.dddddd形式に変換
        lat_deg = float(lat_raw[:2])
        lat_min = float(lat_raw[2:])
        latitude = lat_deg + (lat_min / 60)
        if lat_dir == 'S':
            latitude = -latitude
    else:
        return None
    
    # 経度の解析 (例: 13947.452123,E)
    if len(parts) > 5 and parts[4] and parts[5]:
        lon_raw = parts[4]  # 13947.452123
        lon_dir = parts[5]  # E
        
        # DDDMMmm.mmmm形式をDDD.dddddd形式に変換
        lon_deg = float(lon_raw[:3])
        lon_min = float(lon_raw[3:])
        longitude = lon_deg + (lon_min / 60)
        if lon_dir == 'W':
            longitude = -longitude
    else:
        return None
    
    return (latitude, longitude)

def process_uart_log(input_file, output_file):
    """UARTログファイルを処理してCSVに出力"""
    coordinates = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            # +TEST: RX "HEX文字列" のパターンを検索
            match = re.search(r'\+TEST: RX "([0-9A-Fa-f]+)"', line)
            if match:
                hex_data = match.group(1)
                nmea_sentence = hex_to_nmea(hex_data)
                
                if nmea_sentence:
                    result = parse_gngga(nmea_sentence)
                    if result:
                        coordinates.append(result)
    
    # CSVファイルに書き込み
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['緯度', '経度'])  # ヘッダー
        writer.writerows(coordinates)
    
    print(f"処理完了: {len(coordinates)}件のデータを{output_file}に保存しました")

# 使用例
if __name__ == "__main__":
    input_file = "raw_data.txt"  # 入力ファイル名
    output_file = "coordinates.csv"  # 出力ファイル名
    
    process_uart_log(input_file, output_file)