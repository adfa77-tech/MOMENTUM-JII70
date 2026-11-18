import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import json
import feedparser
from datetime import datetime, timezone
from pathlib import Path
import yfinance as yf
import urllib.parse

st.set_page_config(page_title="JII70 Quant Pro", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM STYLING (HIJAU EMERALD, KUNING EMAS, & GELAP ESTETIK) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');
html, body, [class*="css"] {font-family:'DM Sans',sans-serif;}
.stApp {background:linear-gradient(135deg,#061a14 0%,#092e22 55%,#0f172a 100%); color:#eaf1fb;}
[data-testid="stSidebar"] {background:#0a1423;border-right:1px solid #1b2c43;}
h1,h2,h3 {font-family:'Space Grotesk',sans-serif;color:#f4f8ff;}
div[data-testid="stMetric"] {background:linear-gradient(145deg,#12233a,#101d30);padding:15px 17px;border:1px solid #203651;border-radius:15px;}
div[data-testid="stMetricLabel"] {color:#9eb3cc;}
div[data-testid="stMetricValue"] {color:#f4f8ff;}
.stButton>button {border-radius:10px;border:1px solid #059669;background:#065f46;color:#eff7ff;font-weight:700;}
.stButton>button:hover {border-color:#34d399;color:white;background:#047857;}
section[data-testid="stMain"] .block-container {padding-top:1.6rem;max-width:1600px;}
div[data-testid="stDataFrame"] {border:1px solid #213751;border-radius:12px;overflow:hidden;}
.small-muted {color:#9eb3cc;font-size:0.88rem;}
.hero {padding:24px 26px;border:1px solid #059669;border-radius:18px;background:radial-gradient(circle at 85% 0%,#047857 0%,transparent 34%),linear-gradient(120deg,#064e3b,#092e22);margin-bottom:18px;}
.pill {display:inline-block;padding:5px 10px;border-radius:30px;background:#065f46;color:#34d399;font-size:12px;font-weight:700;letter-spacing:.04em;}

/* Custom Card untuk Hasil Kalkulator agar tulisan lebih kecil & tidak terpotong titik-titik */
.calc-card {
    background: linear-gradient(145deg, #12233a, #101d30);
    padding: 14px 16px;
    border: 1px solid #203651;
    border-radius: 14px;
    height: 100%;
}
.calc-label {
    color: #9eb3cc;
    font-size: 0.82rem;
    font-weight: 500;
    margin-bottom: 6px;
}
.calc-value {
    color: #f4f8ff;
    font-size: 1.12rem;
    font-weight: 700;
    line-height: 1.3;
    word-break: break-word;
}
.calc-delta-pos {
    color: #34d399;
    font-size: 0.82rem;
    font-weight: 700;
    margin-top: 4px;
}
.calc-delta-neg {
    color: #f87171;
    font-size: 0.82rem;
    font-weight: 700;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
WATCH_FILE = DATA_DIR / "watchlist.json"

# --- 70 EMITEN JII70 LENGKAP ---
DEFAULT_TICKERS = [
    "AADI.JK", "ACES.JK", "ADMR.JK", "ADRO.JK", "AKRA.JK", "ANTM.JK", "ARCI.JK", "AVIA.JK", "BKSL.JK", "BRIS.JK",
    "BRMS.JK", "BSDE.JK", "BTPS.JK", "BUMI.JK", "CMRY.JK", "CPIN.JK", "CTRA.JK", "DEWA.JK", "DKFT.JK", "DSNG.JK",
    "ELSA.JK", "ENRG.JK", "ERAA.JK", "ESSA.JK", "EXCL.JK", "HEAL.JK", "HRTA.JK", "HRUM.JK", "ICBP.JK", "IMPC.JK",
    "INDF.JK", "INDY.JK", "INKP.JK", "INTP.JK", "ISAT.JK", "ITMG.JK", "JPFA.JK", "JSMR.JK", "KIJA.JK", "KLBF.JK",
    "KPIG.JK", "LSIP.JK", "MAPA.JK", "MAPI.JK", "MARK.JK", "MBMA.JK", "MDKA.JK", "MEDC.JK", "MIKA.JK", "MTEL.JK",
    "MYOR.JK", "PGAS.JK", "PTBA.JK", "RAJA.JK", "RATU.JK", "SIDO.JK", "SMGR.JK", "SMRA.JK", "SRTG.JK", "SSIA.JK",
    "TAPG.JK", "TCPI.JK", "TINS.JK", "TKIM.JK", "TLKM.JK", "TOBA.JK", "TPIA.JK", "UNTR.JK", "UNVR.JK", "WIFI.JK"
]

def load_watchlist():
    try:
        if WATCH_FILE.exists():
            data = json.loads(WATCH_FILE.read_text())
            return data if isinstance(data, list) else []
        return []
    except Exception:
        return []

def save_watchlist(items):
    WATCH_FILE.write_text(json.dumps(sorted(set(items)), indent=2))

if "watchlist" not in st.session_state:
    st.session_state.watchlist = load_watchlist()

if "universe" not in st.session_state:
    st.session_state.universe = DEFAULT_TICKERS.copy()

# --- FUNGSI UTILITY & TEKNIKAL ---
def fmt_rupiah(val):
    if pd.isna(val) or val is None:
        return "-"
    return f"Rp {int(round(val)):,}".replace(",", ".")

def ticker_label(t):
    return t.replace(".JK", "")

def normalize_ticker(val):
    v = val.strip().upper()
    if not v: return None
    if v.startswith("^"): return v
    if not v.endswith(".JK"): v += ".JK"
    return v

def to_tv_symbol(ticker):
    if ticker == "^JKSE":
        return "IDX:COMPOSITE"
    return f"IDX:{ticker_label(ticker)}"

@st.cache_data(ttl=300)
def get_history(ticker, period="6mo", interval="1d"):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna()
        return df
    except Exception:
        return None

def indicators(df):
    if df is None or df.empty or len(df) < 15:
        return pd.DataFrame()
    d = df.copy()
    d["MA20"] = d["Close"].rolling(20).mean()
    d["MA50"] = d["Close"].rolling(50).mean()
    d["MA200"] = d["Close"].rolling(min(len(d), 200)).mean()
    
    delta = d["Close"].diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / loss
    d["RSI"] = 100 - (100 / (1 + rs))
    
    exp1 = d["Close"].ewm(span=12, adjust=False).mean()
    exp2 = d["Close"].ewm(span=26, adjust=False).mean()
    d["MACD"] = exp1 - exp2
    
    d["Support"] = d["Low"].rolling(20).min()
    d["Resistance"] = d["High"].rolling(20).max()
    return d

def make_signal(ind_df):
    if ind_df.empty:
        return {"signal": "WAIT", "buy": 0, "sell": 0, "reason": "Data kurang"}
    row = ind_df.iloc[-1]
    c = row["Close"]
    ma20 = row["MA20"]
    rsi = row["RSI"]
    sup = row["Support"]
    res = row["Resistance"]
    
    if pd.notna(rsi) and rsi < 35 and c >= sup * 0.98:
        return {"signal": "BUY KUAT", "buy": sup, "sell": res, "reason": "RSI oversold & mendekati area support utama (Buy on Weakness)."}
    elif pd.notna(ma20) and c > ma20 and row["MACD"] > 0:
        return {"signal": "BUY", "buy": c * 0.99, "sell": res, "reason": "Tren positif di atas MA20 dengan momentum MACD menguat."}
    elif pd.notna(rsi) and rsi > 75:
        return {"signal": "SELL", "buy": sup, "sell": c, "reason": "RSI jenuh beli (overbought), waspadai koreksi wajar."}
    else:
        return {"signal": "WAIT", "buy": sup, "sell": res, "reason": "Pergerakan harga sideways / konsolidasi wajar."}

@st.cache_data(ttl=1800)
def get_profile(ticker):
    try:
        t = yf.Ticker(ticker)
        return t.info
    except Exception:
        return {}

@st.cache_data(ttl=600)
def get_news(query="saham syariah JII70 IHSG"):
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=id&gl=ID&ceid=ID:id"
        feed = feedparser.parse(url)
        res = []
        for e in feed.entries[:12]:
            res.append({
                "title": e.title,
                "link": e.link,
                "publisher": e.source.title if hasattr(e, 'source') else "Google News",
                "published": e.published if hasattr(e, 'published') else ""
            })
        return res
    except Exception:
        return []

with st.sidebar:
    st.markdown("## 📈 JII70 QUANT PRO")
    st.caption("Islamic equities • Technical intelligence")
    page = st.radio("NAVIGASI", [
        "Dashboard", "Screener JII70", "Chart & Analisis", "Profil Perusahaan",
        "Watchlist", "Kalkulator Saham", "Berita Saham", "Pengaturan & Data"
    ])
    st.divider()
    st.markdown("**Koneksi data**")
    st.caption("Yahoo Finance & TradingView")
    if st.button("↻ Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption("Build 1.0 • Data bukan feed bursa berlisensi")

def load_one(ticker, period="6mo", interval="1d"):
    return get_history(ticker, period, interval)

def latest_snapshot(ticker):
    df = load_one(ticker, "6mo", "1d")
    if df is None or df.empty:
        return None
    ind = indicators(df)
    if ind.empty:
        return None
    row = ind.iloc[-1]
    sig = make_signal(ind)
    prev = ind.iloc[-2]["Close"] if len(ind) > 1 else row["Close"]
    return {
        "Kode": ticker_label(ticker), "Harga": row["Close"], "Open": row["Open"],
        "High": row["High"], "Low": row["Low"], "Prev": prev,
        "Chg %": (row["Close"]/prev-1)*100 if prev else 0,
        "Volume": row["Volume"], "Support": row["Support"], "Resistance": row["Resistance"],
        "RSI": row["RSI"], "MA20": row["MA20"], "MA50": row["MA50"], "MA200": row["MA200"],
        "MACD": row["MACD"], "Signal": sig["signal"], "Harga Buy": sig["buy"],
        "Harga Sell": sig["sell"], "Alasan": sig["reason"], "Waktu": str(ind.index[-1])
    }

def metric_cards(snap):
    cols = st.columns(4)
    vals = [
        ("Harga terakhir", fmt_rupiah(snap["Harga"])),
        ("Perubahan", f'{snap["Chg %"]:+.2f}%'),
        ("RSI 14", f'{snap["RSI"]:.1f}' if pd.notna(snap["RSI"]) else "—"),
        ("Sinyal", snap["Signal"])
    ]
    for c,(lab,val) in zip(cols,vals):
        c.metric(lab,val)

def tradingview_chart(ticker, height=620):
    tv_symbol = to_tv_symbol(ticker)
    widget_html = f"""
    <div class="tradingview-widget-container" style="height:{height}px;width:100%;border-radius:14px;overflow:hidden;border:1px solid #203651;">
      <div id="tv_chart_container" style="height:calc(100% - 32px);width:100%;"></div>
      <div class="tradingview-widget-copyright" style="background:#0b1622;color:#8fa3bf;font-family:sans-serif;font-size:11px;padding:6px 12px;text-align:right;">
        Chart interaktif oleh <a href="https://id.tradingview.com/" rel="noopener nofollow" target="_blank" style="color:#34d399;text-decoration:none;">TradingView</a>
      </div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "{tv_symbol}",
        "interval": "D",
        "timezone": "Asia/Jakarta",
        "theme": "dark",
        "style": "1",
        "locale": "id",
        "toolbar_bg": "#0b1622",
        "backgroundColor": "#081713",
        "gridColor": "rgba(32, 54, 81, 0.35)",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "save_image": true,
        "studies": [
          "MASimple@tv-basicstudies"
        ],
        "container_id": "tv_chart_container"
      }});
      </script>
    </div>
    """
    components.html(widget_html, height=height + 10)

st.markdown('<div class="hero"><span class="pill">JII70 • QUANTITATIVE MARKET WORKSTATION</span><h1 style="margin:12px 0 4px 0;">JII70 Screener & Trading Desk</h1><div class="small-muted">Analisis teknikal, pemantauan syariah, chart candlestick, riset emiten, watchlist dan kalkulator transaksi.</div></div>',unsafe_allow_html=True)

if page == "Dashboard":
    st.subheader("Market overview")
    c1,c2,c3 = st.columns(3)
    idx = latest_snapshot("^JKSE")
    if idx:
        c1.metric("IHSG",fmt_rupiah(idx["Harga"]),f'{idx["Chg %"]:+.2f}%')
    else:
        c1.metric("IHSG","Data belum tersedia")
    c2.metric("Universe saham",len(st.session_state.universe))
    c3.metric("Watchlist",len(st.session_state.watchlist))
    st.info("Universe sudah mencakup daftar 70 emiten JII70 secara lengkap.")
    
    if st.session_state.watchlist:
        st.subheader("Watchlist — ringkasan teknikal")
        rows=[]
        for t in st.session_state.watchlist[:20]:
            s=latest_snapshot(t)
            if s: rows.append(s)
        if rows:
            df=pd.DataFrame(rows)
            st.dataframe(df[["Kode","Harga","Chg %","RSI","Support","Resistance","Signal","Harga Buy","Harga Sell"]],use_container_width=True,hide_index=True)

    st.subheader("IHSG — Chart Candlestick TradingView")
    tradingview_chart("^JKSE", height=580)

elif page == "Screener JII70":
    st.subheader("Screener JII70")
    st.caption("Pemeringkatan berbasis tren, momentum, MACD, RSI, volume dan posisi harga terhadap MA.")
    limit=st.slider("Jumlah saham yang dipindai",min_value=5,max_value=max(5,len(st.session_state.universe)),value=min(25,max(5,len(st.session_state.universe))),step=5)
    if st.button("Jalankan screener",type="primary"):
        rows=[]; bar=st.progress(0)
        tickers=st.session_state.universe[:limit]
        for i,t in enumerate(tickers):
            try:
                s=latest_snapshot(t)
                if s: rows.append(s)
            except Exception: pass
            bar.progress((i+1)/len(tickers))
        st.session_state.scan_rows=rows
    rows=st.session_state.get("scan_rows",[])
    if rows:
        df=pd.DataFrame(rows)
        rank={"BUY KUAT":0,"BUY":1,"WAIT":2,"SELL":3}
        df["_rank"]=df["Signal"].map(rank).fillna(4)
        df=df.sort_values(["_rank","Chg %"],ascending=[True,False]).drop(columns="_rank")
        st.dataframe(df[["Kode","Harga","Open","High","Low","Prev","Chg %","Volume","Support","Resistance","Harga Buy","Harga Sell","Signal","Alasan","Waktu"]],use_container_width=True,hide_index=True)
        st.download_button("⬇ Download hasil CSV",df.to_csv(index=False).encode("utf-8"),"jii70_screener.csv","text/csv")
    else:
        st.info("Klik **Jalankan screener** untuk mengambil data Yahoo Finance. Scan banyak ticker dapat memerlukan waktu.")

elif page == "Chart & Analisis":
    st.subheader("Chart candlestick & analisis teknikal")
    options=st.session_state.universe+["^JKSE"]
    t=st.selectbox("Pilih saham / indeks",options,format_func=lambda x:"IHSG (^JKSE)" if x=="^JKSE" else ticker_label(x))
    
    tradingview_chart(t, height=620)
    
    snap=latest_snapshot(t)
    if snap:
        metric_cards(snap)
        st.markdown("**Rekomendasi teknikal**")
        st.write(snap["Signal"],"—",snap["Alasan"])
        st.write(f"Area buy indikatif: **{fmt_rupiah(snap['Harga Buy'])}** | Area sell/target indikatif: **{fmt_rupiah(snap['Harga Sell'])}**")
        st.caption(f"Timestamp candle terakhir: {snap['Waktu']}. Harga indikatif berdasarkan candle harian.")
    else:
        st.warning("Ringkasan indikator harian belum tersedia untuk ticker ini.")

elif page == "Profil Perusahaan":
    st.subheader("Profil perusahaan")
    t=st.selectbox("Pilih emiten",st.session_state.universe,format_func=ticker_label)
    p=get_profile(t)
    if p:
        a,b,c=st.columns(3)
        a.metric("Sektor",p.get("sector") or "—")
        b.metric("Industri",p.get("industry") or "—")
        c.metric("Karyawan",f'{p.get("fullTimeEmployees"):,}' if p.get("fullTimeEmployees") else "—")
        st.markdown(f"### {p.get('longName') or ticker_label(t)}")
        st.write(p.get("longBusinessSummary") or "Ringkasan bisnis tidak tersedia dari Yahoo Finance.")
        details=pd.DataFrame([{"Informasi":k,"Data":p.get(k)} for k in ["website","country","city","address1","phone","marketCap","currency","exchange","quoteType"] if p.get(k) is not None])
        st.dataframe(details,use_container_width=True,hide_index=True)
        st.link_button("Cari profil emiten di situs BEI",f"https://www.idx.co.id/id/perusahaan-tercatat/profil-perusahaan-tercatat/?kodeEmiten={ticker_label(t)}")
    else: st.warning("Profil belum tersedia.")

elif page == "Watchlist":
    st.subheader("Watchlist pribadi")
    add=st.selectbox("Pilih saham untuk ditambahkan",["— Pilih Saham —"] + st.session_state.universe,format_func=lambda x: x if x=="— Pilih Saham —" else ticker_label(x),key="watch_add")
    if st.button("＋ Tambahkan ke watchlist"):
        if add != "— Pilih Saham —":
            if add not in st.session_state.watchlist:
                st.session_state.watchlist.append(add)
                save_watchlist(st.session_state.watchlist)
                st.success(f"{ticker_label(add)} ditambahkan ke watchlist.")
                st.rerun()
            else:
                st.info(f"{ticker_label(add)} sudah ada di watchlist.")
        else:
            st.warning("Silakan pilih saham terlebih dahulu.")
            
    if st.session_state.watchlist:
        rows=[]
        for t in st.session_state.watchlist:
            s=latest_snapshot(t)
            if s: rows.append(s)
        if rows:
            st.dataframe(pd.DataFrame(rows)[["Kode","Harga","Chg %","RSI","Support","Resistance","Signal","Alasan"]],use_container_width=True,hide_index=True)
        rem=st.selectbox("Hapus dari watchlist",["—"]+st.session_state.watchlist,format_func=lambda x:ticker_label(x) if x!="—" else x)
        if st.button("Hapus pilihan") and rem!="—":
            st.session_state.watchlist=[x for x in st.session_state.watchlist if x!=rem]
            save_watchlist(st.session_state.watchlist)
            st.rerun()
    else:
        st.info("Watchlist masih kosong. Pilih saham di atas dan klik **＋ Tambahkan ke watchlist** untuk mulai memantau.")

elif page == "Kalkulator Saham":
    st.subheader("Kalkulator transaksi saham")
    
    # --- KOLOM NAMA / KODE SAHAM ---
    s1, s2 = st.columns([2, 1])
    pilih_saham = s1.selectbox(
        "Pilih kode saham (JII70)",
        ["Input Manual"] + [ticker_label(t) for t in st.session_state.universe],
        index=1
    )
    if pilih_saham == "Input Manual":
        nama_saham = s2.text_input("Ketik kode / nama saham", value="BBCA").strip().upper() or "-"
    else:
        nama_saham = s2.text_input("Kode / nama saham terpilih", value=pilih_saham).strip().upper() or pilih_saham

    x1, x2, x3 = st.columns(3)
    lot = x1.number_input("Jumlah lot", min_value=1, value=10, step=1)
    buy = x2.number_input("Harga beli / lembar (Rp)", min_value=1, value=1000, step=1)
    sell = x3.number_input("Harga jual / lembar (Rp)", min_value=1, value=1100, step=1)
    
    y1, y2 = st.columns(2)
    buy_fee = y1.number_input("Fee beli (%)", min_value=0.0, value=0.15, step=0.01, format="%.2f")
    sell_fee = y2.number_input("Fee jual (%)", min_value=0.0, value=0.25, step=0.01, format="%.2f")
    
    # --- RUMUS TETAP SAMA ---
    qty = lot * 100
    gross_buy = qty * buy
    gross_sell = qty * sell
    fee_b = gross_buy * buy_fee / 100
    fee_s = gross_sell * sell_fee / 100
    total_buy = gross_buy + fee_b
    net_sell = gross_sell - fee_s
    pnl = net_sell - total_buy
    pct = pnl / total_buy * 100 if total_buy else 0

    st.markdown(f"**Ringkasan Simulasi: {nama_saham}**")
    delta_class = "calc-delta-pos" if pnl >= 0 else "calc-delta-neg"
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="calc-card">
            <div class="calc-label">Modal + fee beli ({nama_saham})</div>
            <div class="calc-value">{fmt_rupiah(total_buy)}</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="calc-card">
            <div class="calc-label">Hasil bersih jual</div>
            <div class="calc-value">{fmt_rupiah(net_sell)}</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="calc-card">
            <div class="calc-label">Profit / loss</div>
            <div class="calc-value">{fmt_rupiah(pnl)}</div>
            <div class="{delta_class}">{pct:+.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="calc-card">
            <div class="calc-label">Jumlah saham</div>
            <div class="calc-value">{f"{qty:,}".replace(",", ".")} lembar</div>
        </div>
        """, unsafe_allow_html=True)

elif page == "Berita Saham":
    st.subheader("Berita terkini terkait saham")
    q=st.text_input("Kata kunci berita",value="saham Indonesia BEI JII70")
    items=get_news(q)
    if items:
        for item in items:
            st.markdown(f"**[{item['title']}]({item['link']})**")
            st.caption(f"{item.get('publisher','Sumber online')} • {item.get('published','Waktu tidak tersedia')}")
            st.divider()
    else:
        st.info("Berita belum berhasil dimuat.")

elif page == "Pengaturan & Data":
    st.subheader("Universe JII70 & konfigurasi data")
    st.write(f"Jumlah ticker tersedia: **{len(st.session_state.universe)}**")
    st.code(", ".join(ticker_label(t) for t in st.session_state.universe))
    up=st.file_uploader("Unggah CSV konstituen JII70",type=["csv"])
    if up:
        try:
            raw=pd.read_csv(up)
            col=next((c for c in raw.columns if c.lower() in ["kode","ticker","symbol","code"]),raw.columns[0])
            new=[]
            for v in raw[col].dropna().astype(str):
                z=normalize_ticker(v)
                if z: new.append(z)
            if st.button("Gunakan universe dari CSV"):
                st.session_state.universe=sorted(set(new))
                st.session_state.scan_rows=[]
                st.success(f"Universe diperbarui: {len(st.session_state.universe)} ticker.")
        except Exception as e: st.error(f"Gagal membaca CSV: {e}")
