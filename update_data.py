#!/usr/bin/env python3
"""
GitHub Actions 环境运行：
用 yfinance 拉取最新 ETF 数据，计算指标，更新 JSON 文件
"""
import os, json, sys, subprocess
from datetime import datetime, timezone, timedelta

ETFS = {
    'SPMO': {'genesis': '2015-10-16', 'file_prefix': 'spy'},
    'SOXX': {'genesis': '2015-01-12', 'file_prefix': 'soxx'},
    'XMMO': {'genesis': '2015-01-12', 'file_prefix': 'xmmo'},
}

def install_deps():
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'yfinance', 'pandas', '-q'], 
                   capture_output=True)

def fetch_yahoo(ticker, start_date):
    try:
        import yfinance as yf
        ticker_obj = yf.Ticker(ticker)
        df = ticker_obj.history(start=start_date, auto_adjust=True)
        if df.empty:
            return []
        pairs = []
        for idx, row in df.iterrows():
            pairs.append((
                idx.strftime('%Y-%m-%d'),
                float(row['Open']),
                float(row['High']),
                float(row['Low']),
                float(row['Close']),
                float(row['Volume']),
            ))
        return pairs
    except Exception as e:
        print(f'  [ERROR] {ticker}: {e}')
        return []

def main():
    print(f'=== GitHub Actions ETF Update: {datetime.now().strftime("%Y-%m-%d %H:%M")} ===')
    install_deps()
    
    base_dir = os.getcwd()
    
    for ticker, cfg in ETFS.items():
        print(f'\n[{ticker}]')
        pairs = fetch_yahoo(ticker, cfg['genesis'])
        if not pairs:
            print(f'  [WARN] No data')
            continue
        print(f'  Got {len(pairs)} bars, latest: {pairs[-1][0]}')
        
        # 保存为 CSV（让 build_from_csv.py 能读取）
        csv_path = os.path.join(base_dir, f'{cfg["file_prefix"]}-ahr999', 'data', f'{cfg["file_prefix"]}_daily.csv')
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        import csv
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['日期', '收盘', '开盘', '高', '低', '交易量', '涨跌幅'])
            for ds, op, hi, lo, cl, vo in pairs:
                writer.writerow([ds, f'{cl:.2f}', f'{op:.2f}', f'{hi:.2f}', f'{lo:.2f}', str(int(vo)), '0.00%'])
        
        print(f'  [OK] Saved to {csv_path}')
        
        # 运行 build_from_csv.py 和 build_clean.py
        folder = f'{cfg["file_prefix"]}-ahr999'
        scripts_dir = os.path.join(base_dir, folder, 'scripts')
        
        if os.path.isdir(scripts_dir):
            r1 = subprocess.run([sys.executable, 'build_from_csv.py'], cwd=scripts_dir, 
                              capture_output=True, text=True, encoding='utf-8', errors='replace')
            if r1.returncode == 0:
                print(f'  [OK] build_from_csv.py')
            else:
                print(f'  [ERROR] build_from_csv.py: {r1.stderr[:200]}')
            
            r2 = subprocess.run([sys.executable, 'build_clean.py'], cwd=scripts_dir,
                              capture_output=True, text=True, encoding='utf-8', errors='replace')
            if r2.returncode == 0:
                print(f'  [OK] build_clean.py')
            else:
                print(f'  [ERROR] build_clean.py: {r2.stderr[:200]}')
    
    print('\n=== Done ===')

if __name__ == '__main__':
    main()
