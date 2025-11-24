from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Default NSE stock list
DEFAULT_STOCKS = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
    'HINDUNILVR.NS', 'ITC.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS',
    'LT.NS', 'AXISBANK.NS', 'ASIANPAINT.NS', 'MARUTI.NS', 'HCLTECH.NS',
    'WIPRO.NS', 'ULTRACEMCO.NS', 'TITAN.NS', 'NESTLEIND.NS', 'BAJFINANCE.NS'
]

def calculate_ema(data, period):
    return data['Close'].ewm(span=period, adjust=False).mean()

def calculate_rsi(data, period=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(data):
    exp1 = data['Close'].ewm(span=12, adjust=False).mean()
    exp2 = data['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def analyze_stock(symbol):
    try:
        stock = yf.Ticker(symbol)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        hist = stock.history(start=start_date, end=end_date)
        
        if hist.empty or len(hist) < 50:
            return None
        
        # Calculate indicators
        hist['EMA_20'] = calculate_ema(hist, 20)
        hist['EMA_50'] = calculate_ema(hist, 50)
        hist['EMA_200'] = calculate_ema(hist, 200)
        hist['RSI'] = calculate_rsi(hist)
        hist['MACD'], hist['Signal'] = calculate_macd(hist)
        
        latest = hist.iloc[-1]
        prev = hist.iloc[-2]
        
        signals = []
        signal_count = 0
        
        # Breakout signals
        if latest['Close'] > latest['EMA_20']:
            signals.append('Price above EMA 20')
            signal_count += 1
        
        if latest['EMA_20'] > latest['EMA_50'] > latest['EMA_200']:
            signals.append('Bullish EMA alignment')
            signal_count += 1
        
        if 30 < latest['RSI'] < 70:
            signals.append('RSI in healthy range')
            signal_count += 1
        
        if latest['MACD'] > latest['Signal']:
            signals.append('MACD bullish crossover')
            signal_count += 1
        
        if latest['Volume'] > hist['Volume'].tail(20).mean() * 1.5:
            signals.append('High volume breakout')
            signal_count += 1
        
        return {
            'symbol': symbol,
            'name': symbol.replace('.NS', ''),
            'price': round(latest['Close'], 2),
            'ema_20': round(latest['EMA_20'], 2),
            'ema_50': round(latest['EMA_50'], 2),
            'ema_200': round(latest['EMA_200'], 2),
            'rsi': round(latest['RSI'], 2),
            'macd': round(latest['MACD'], 2),
            'macd_signal': round(latest['Signal'], 2),
            'volume': int(latest['Volume']),
            'avg_volume': int(hist['Volume'].tail(20).mean()),
            'signals': signals,
            'signal_count': signal_count,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return None

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'name': 'NSE Stock Breakout Scanner API',
        'version': '1.0',
        'endpoints': {
            '/breakout_scan': 'Scan default stocks for breakout signals',
            '/breakout_scan?symbols=SYMBOL1.NS,SYMBOL2.NS': 'Scan specific stocks',
            '/breakout_scan?min_signals=3': 'Filter by minimum signal count'
        }
    })

@app.route('/breakout_scan', methods=['GET'])
def breakout_scan():
    symbols_param = request.args.get('symbols', '')
    min_signals = int(request.args.get('min_signals', 2))
    
    if symbols_param:
        symbols = [s.strip().upper() for s in symbols_param.split(',')]
        if not all('.NS' in s for s in symbols):
            symbols = [s + '.NS' if '.NS' not in s else s for s in symbols]
    else:
        symbols = DEFAULT_STOCKS
    
    results = []
    for symbol in symbols:
        analysis = analyze_stock(symbol)
        if analysis and analysis['signal_count'] >= min_signals:
            results.append(analysis)
    
    results.sort(key=lambda x: x['signal_count'], reverse=True)
    
    return jsonify({
        'status': 'success',
        'scan_time': datetime.now().isoformat(),
        'stocks_scanned': len(symbols),
        'breakouts_found': len(results),
        'min_signals': min_signals,
        'results': results
    })

if __name__ == '__main__':
    app.run(debug=True)
