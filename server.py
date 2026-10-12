import json, os, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
import numpy as np
import pandas as pd
BASE=os.path.dirname(os.path.abspath(__file__))
# DEMO ONLY: deterministic synthetic prices, no licensed market data included.
# This deployment is a UI demonstration, NOT historical TXF market statistics.
rng=np.random.default_rng(20261013)
times=[]
for day in pd.bdate_range('2026-08-03',periods=35):
 for start,steps in [('08:45',60),('15:00',90)]:
  times.extend(pd.date_range(str(day.date())+' '+start,periods=steps,freq='5min'))
changes=rng.normal(0,15,len(times))
close=np.round(23000+np.cumsum(changes)).astype(int)
open_=np.r_[23000,close[:-1]]
spread=rng.integers(3,23,len(times))
high=np.maximum(open_,close)+spread
low=np.minimum(open_,close)-spread
df=pd.DataFrame({'日期':[x.strftime('%Y-%m-%d') for x in times], '時間':[x.strftime('%H:%M') for x in times], '開盤價':open_, '最高價':high, '最低價':low, '收盤價':close})
df['dt']=pd.to_datetime(df['日期'].astype(str)+' '+df['時間'].astype(str),errors='coerce')
df=df.dropna(subset=['dt']).sort_values('dt').drop_duplicates('dt',keep='last').reset_index(drop=True)
for col in ['開盤價','最高價','最低價','收盤價']:df[col]=pd.to_numeric(df[col],errors='coerce')
df=df.dropna(subset=['開盤價','最高價','最低價','收盤價']).reset_index(drop=True)
t=df.dt.to_numpy(dtype='datetime64[m]'); o=df['開盤價'].to_numpy();h=df['最高價'].to_numpy();l=df['最低價'].to_numpy();c=df['收盤價'].to_numpy();n=len(df)
# Market session determined by exchange clock; times 15:00-05:00 night, 08:45-13:45 day.
hour=df.dt.dt.hour.to_numpy(); session=np.where((hour>=15)|(hour<6),'夜盤','日盤')
prevhigh=pd.Series(h).shift(1).rolling(50,min_periods=50).max().to_numpy()
prevlow=pd.Series(l).shift(1).rolling(50,min_periods=50).min().to_numpy()
event=np.where(c>prevhigh,'突破前高',np.where(c<prevlow,'跌破前低','一般行情'))
# Only label outcomes with 6 consecutive 5-minute bars, within the same session.
valid=np.zeros(n,dtype=bool); delta=np.full(n,np.nan)
valid[:-6]=(t[6:]-t[:-6]==np.timedelta64(30,'m')) & (session[6:]==session[:-6])
delta[:-6]=(c[6:]-c[:-6])/c[:-6]
valid &= np.isfinite(delta)
outcome=np.where(delta>0.001,'上漲',np.where(delta< -0.001,'下跌','震盪'))
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=BASE,**kw)
 def log_message(self,*a):pass
 def do_GET(self):
  p=urlparse(self.path)
  if p.path=='/api/state':
   try:
    q=parse_qs(p.query);i=int(q.get('i',[n-7])[0]);i=max(100,min(i,n-1));start=max(0,i-115)
    candles=[{'t':str(df.dt.iloc[j])[:16], 'o':int(o[j]),'h':int(h[j]),'l':int(l[j]),'c':int(c[j]),'s':session[j]} for j in range(start,i+1)]
    # Past-only price occupancy based on OHLC midpoints; never volume.
    back=max(0,i-2500); mids=(h[back:i]+l[back:i])/2
    width=max(20,int(np.nanmedian(h[back:i]-l[back:i])*2//10*10))
    bins=np.floor(mids/width).astype(int); uniq,counts=np.unique(bins,return_counts=True)
    best=np.argsort(counts)[-6:][::-1];zones=[{'lo':int(uniq[k]*width),'hi':int((uniq[k]+1)*width),'count':int(counts[k])} for k in best]
    # Exclude all examples whose future 30m would be after the observation time.
    mask=(np.arange(n)<i-6)&valid&(session==session[i])&(event==event[i]);inds=np.flatnonzero(mask)
    recent=inds[-20000:]; cnt=len(recent);rates={k:round(100*float(np.mean(outcome[recent]==k)),1) if cnt else None for k in ['上漲','震盪','下跌']}
    baseinds=np.flatnonzero((np.arange(n)<i-6)&valid&(session==session[i]));base=baseinds[-20000:]
    baserates={k:round(100*float(np.mean(outcome[base]==k)),1) if len(base) else None for k in ['上漲','震盪','下跌']}
    # Historic event sample rows strictly earlier than observation.
    examples=[{'t':str(df.dt.iloc[j])[:16], 'change':round(float(delta[j]*100),2)} for j in recent[-5:][::-1]]
    current=int(c[i]); levels=sorted(set([z['lo'] for z in zones]+[z['hi'] for z in zones]+([int(prevhigh[i])] if np.isfinite(prevhigh[i]) else [])+([int(prevlow[i])] if np.isfinite(prevlow[i]) else [])))
    above=next((x for x in levels if x>current),None);below=next((x for x in levels[::-1] if x<current),None)
    result={'index':i,'total':n,'timestamp':str(df.dt.iloc[i])[:16], 'session':session[i], 'current':current,'ohlc':{'open':int(o[i]),'high':int(h[i]),'low':int(l[i]),'close':current},'candles':candles,'event':event[i],'high50':int(prevhigh[i]) if np.isfinite(prevhigh[i]) else None,'low50':int(prevlow[i]) if np.isfinite(prevlow[i]) else None,'zones':zones,'above':above,'below':below,'sample':cnt,'rates':rates,'baseline':baserates,'examples':examples,'demo':True,'rule':'【模擬資料，非真實市場統計】後續30分鐘收盤變動 > +0.1% 為上漲，< -0.1% 為下跌，其餘為震盪；同盤別、同事件，且未跨休市時段。'}
    body=json.dumps(result,ensure_ascii=False).encode('utf-8');self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
   except Exception as ex:
    body=json.dumps({'error':str(ex)}).encode();self.send_response(500);self.end_headers();self.wfile.write(body)
  else:super().do_GET()
if __name__=='__main__':
 print(f'已載入模擬資料 {n:,} 根K線，{df.dt.iloc[0]} ～ {df.dt.iloc[-1]}')
 print('伺服器已啟動')
 ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT','8765'))),Handler).serve_forever()
