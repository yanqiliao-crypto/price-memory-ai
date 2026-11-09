"""Public classroom demonstration. All candles are synthetic; real performance is a fixed,
precomputed summary from an earlier offline experiment. No licensed price data or model included.
"""
import json
import os
import random
import math
from datetime import datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, 'performance_summary.json'), encoding='utf-8') as fh:
    PERFORMANCE = json.load(fh)

rng = random.Random(20261109)
BARS = []
price = 23000.0
start = datetime(2026, 10, 5)
for d in range(26):
    day = start + timedelta(days=d)
    if day.weekday() >= 5:
        continue
    for session, st, count in [('日盤', '08:45', 60), ('夜盤', '15:00', 72)]:
        hour, minute = map(int, st.split(':'))
        ts = day.replace(hour=hour, minute=minute)
        for j in range(count):
            op = price
            price += (math.sin(len(BARS) / 37) * 2.2 + rng.gauss(0, 13))
            cl = round(price)
            hi = max(round(op), cl) + rng.randint(2, 19)
            lo = min(round(op), cl) - rng.randint(2, 19)
            BARS.append({'t': (ts + timedelta(minutes=5*j)).strftime('%Y-%m-%d %H:%M'),
                         'o': round(op), 'h': hi, 'l': lo, 'c': cl, 's': session})
N = len(BARS)

def state(i):
    i = max(50, min(N-1, i))
    candle = BARS[i]
    past = BARS[max(0, i-50):i]
    high50 = max(v['h'] for v in past)
    low50 = min(v['l'] for v in past)
    event = '突破前高' if candle['c'] > high50 else ('跌破前低' if candle['c'] < low50 else '一般行情')
    past_250 = BARS[max(0, i-250):i]
    width = 40
    counts = {}
    for row in past_250:
        b = math.floor(((row['h']+row['l'])/2)/width)*width
        counts[b] = counts.get(b, 0)+1
    zones = [{'lo': k, 'hi': k+width, 'count': v} for k,v in sorted(counts.items(),key=lambda kv:-kv[1])[:5]]
    levels = sorted(set([high50,low50]+[x for z in zones for x in (z['lo'],z['hi'])]))
    above = next((p for p in levels if p>candle['c']),None)
    below = next((p for p in reversed(levels) if p<candle['c']),None)
    return {'mode':'synthetic','index':i,'total':N,'timestamp':candle['t'],
            'current':candle['c'],'ohlc':candle,'session':candle['s'],
            'candles':BARS[max(0,i-99):i+1],'event':event,
            'high50':high50,'low50':low50,'above':above,'below':below,'zones':zones,
            'prediction':None,'prediction_note':'模擬 K 線不使用真實模型推論；此畫面不提供行情方向預測。'}

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE, **kwargs)
    def log_message(self, *args):
        return
    def send_json(self, obj, status=200):
        body=json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        p=urlparse(self.path)
        if p.path=='/api/metrics':
            return self.send_json(PERFORMANCE)
        if p.path=='/api/state':
            try:
                v=parse_qs(p.query).get('i',[str(N-1)])[0]
                i=int(v)
            except (ValueError,TypeError):
                return self.send_json({'error':'Invalid index'},400)
            return self.send_json(state(i))
        if p.path in ('/','/index.html'):
            self.path='/index.html'
            return super().do_GET()
        self.send_error(404,'Not Found')

if __name__=='__main__':
    port=int(os.environ.get('PORT','8765'))
    print(f'Public demo: {N} synthetic candles, no licensed data. Listening on {port}',flush=True)
    ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
