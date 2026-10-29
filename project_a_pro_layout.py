import streamlit as st
from datetime import datetime, date

st.set_page_config(page_title='Project A Pro', page_icon='📊', layout='wide')
st.markdown('''<style>
.block-container{padding-top:1rem;max-width:1600px} [data-testid="stAppViewContainer"]{background:#f5f9fd}
.brand{font-size:2rem;font-weight:800;color:#10234b}.sub{color:#53627d}
.card{border:1px solid #d8e6f1;border-radius:12px;padding:12px;background:white;margin-bottom:10px}
.green{background:#eaf9f3;border-color:#c5eadb}.pink{background:#fff0f2;border-color:#f2d2d8}.yellow{background:#fff8e5;border-color:#f1e2b9}
</style>''', unsafe_allow_html=True)

h1,h2,h3=st.columns([5,1.5,1.5])
with h1:
 st.markdown('<div class="brand">📊 Project A Pro</div><div class="sub">Options Ratio Spread Scanner</div>',unsafe_allow_html=True)
with h2: st.success('● Layout Preview')
with h3: st.caption(datetime.now().strftime('%d %b %Y %H:%M:%S')); st.button('⟳ Refresh',use_container_width=True)

with st.container(border=True):
 a,b,c,d,e=st.columns([1.2,1,1,1.1,2.3])
 with a: delta=st.text_input('Delta','0.20 - 0.25')
 with b: ratio=st.selectbox('Ratio',['1 : 3','3 : 10','1 : 4'])
 with c: option=st.selectbox('Option Type',['CE (Call)','PE (Put)'])
 with d: expiry=st.date_input('Expiry',date(2026,11,26))
 with e:
  x,y=st.columns(2)
  with x: st.markdown('**Spread Cost (₹) — Debit**'); debit=st.text_input('Debit range','0 - 5000',label_visibility='collapsed')
  with y: st.markdown('**Spread Cost (₹) — Credit**'); credit=st.text_input('Credit range','0 - 5000',label_visibility='collapsed')

x,y,z=st.columns(3)
with x:
 with st.container(border=True):
  st.markdown('### 1. Debit ₹0 Scanner')
  p,q,r=st.columns(3)
  with p: st.button('Auto',key='dauto',use_container_width=True)
  with q: st.button('Manual',key='dmanual',use_container_width=True)
  with r: st.button('Scan',key='dscan',type='primary',use_container_width=True)
with y:
 with st.container(border=True):
  st.markdown('### 2. % Gap Scanner')
  p,q=st.columns([2,1])
  with p: gap=st.number_input('Gap %',min_value=0,max_value=100,value=20)
  with q: st.markdown('**%**'); st.button('Auto',key='gauto',use_container_width=True)
  p,q=st.columns(2)
  with p: st.button('Manual',key='gmanual',use_container_width=True)
  with q: st.button('Scan',key='gscan',use_container_width=True)
with z:
 with st.container(border=True):
  st.markdown('### 3. Option Premium Spike (UP / DOWN)')
  p,q=st.columns(2)
  with p: spike=st.number_input('Spike %',min_value=1,max_value=100,value=10)
  with q: direction=st.selectbox('Direction',['UP','DOWN'])
  p,q=st.columns(2)
  with p: st.toggle('Auto',value=False,key='spike_auto')
  with q: st.button('Manual Scan',key='spike_manual',use_container_width=True)

st.markdown('## 🎯 Scan Results (Live)')
st.caption('Visual layout preview only — the sample rows below are not live market data.')
a,b,c=st.columns([1.3,1,2])
with a: minimum=st.number_input('Minimum Profit ₹',min_value=-100000,max_value=100000,value=0,step=1)
with b: st.metric('Total Results','—')
with c: search=st.text_input('Search company',placeholder='Search company...')
rows=[
 {'Company':'RELIANCE','Delta':'0.22','Lot Size':500,'Buy Strike':840,'Buy Price (LTP)':118.50,'Sell Strike':900,'Sell Price (LTP)':39.20,'Debit / Credit':'Preview','Result Date':'—'},
 {'Company':'TCS','Delta':'0.21','Lot Size':175,'Buy Strike':3200,'Buy Price (LTP)':145.30,'Sell Strike':3300,'Sell Price (LTP)':48.80,'Debit / Credit':'Preview','Result Date':'—'},
 {'Company':'INFY','Delta':'0.23','Lot Size':400,'Buy Strike':1520,'Buy Price (LTP)':62.40,'Sell Strike':1580,'Sell Price (LTP)':19.50,'Debit / Credit':'Preview','Result Date':'—'},
 {'Company':'HDFCBANK','Delta':'0.24','Lot Size':550,'Buy Strike':1640,'Buy Price (LTP)':74.20,'Sell Strike':1700,'Sell Price (LTP)':22.10,'Debit / Credit':'Preview','Result Date':'—'},
 {'Company':'ICICIBANK','Delta':'0.21','Lot Size':700,'Buy Strike':1120,'Buy Price (LTP)':48.90,'Sell Strike':1180,'Sell Price (LTP)':15.60,'Debit / Credit':'Preview','Result Date':'—'},
 {'Company':'SBIN','Delta':'0.20','Lot Size':750,'Buy Strike':360,'Buy Price (LTP)':36.70,'Sell Strike':420,'Sell Price (LTP)':11.40,'Debit / Credit':'Preview','Result Date':'—'},
 {'Company':'BHARTIARTL','Delta':'0.22','Lot Size':475,'Buy Strike':880,'Buy Price (LTP)':42.10,'Sell Strike':940,'Sell Price (LTP)':12.30,'Debit / Credit':'Preview','Result Date':'—'},
 {'Company':'LT','Delta':'0.21','Lot Size':150,'Buy Strike':3600,'Buy Price (LTP)':158.20,'Sell Strike':3700,'Sell Price (LTP)':52.60,'Debit / Credit':'Preview','Result Date':'—'},
]
st.dataframe([r for r in rows if search.lower() in r['Company'].lower()],use_container_width=True,hide_index=True)
for name in ['RELIANCE','TCS','INFY','HDFCBANK','ICICIBANK','SBIN','BHARTIARTL','LT']:
 with st.expander(f'{name} — Review-1 / Review-2'):
  st.write('Review-1: Supporting Spread — actual values will be connected to Project A logic.')
  st.write('Review-2: One-strike-gap spread — actual values will be connected to Project A logic.')
st.warning('Prototype only: no live scanning is connected yet. F&O Ban, NSE official Result Date, live LTP, Margin, and the original Project A calculations will be added after layout approval.')
