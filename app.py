
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
import json, time
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from screener_core import (
    get_history, indicators, make_signal, get_profile, get_news,
    fmt_rupiah, normalize_ticker, DEFAULT_TICKERS
)

st.set_page_config(page_title="JII70 Quant Pro", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');
html, body, [class*="css"] {font-family:'DM Sans',sans-serif;}
.stApp {background:linear-gradient(135deg,#08111f 0%,#0c1728 55%,#101c31 100%); color:#eaf1fb;}
[data-testid="stSidebar"] {background:#0a1423;border-right:1px solid #1b2c43;}
h1,h2,h3 {font-family:'Space Grotesk',sans-serif;color:#f4f8ff;}
div[data-testid="stMetric"] {background:linear-gradient(145deg,#12233a,#101d30);padding:15px 17px;border:1px solid #203651;border-radius:15px;}
div[data-testid="stMetricLabel"] {color:#9eb3cc;}
div[data-testid="stMetricValue"] {color:#f4f8ff;}
.stButton>button {border-radius:10px;border:1px solid #2d5274;background:#153453;color:#eff7ff;font-weight:700;}
.stButton>button:hover {border-color:#54b7ff;color:white;}
section[data-testid="stMain"] .block-container {padding-top:1.6rem;max-width:1600px;}
div[data-testid="stDataFrame"] {border:1px solid #213751;border-radius:12px;overflow:hidden;}
.small-muted {color:#9eb3cc;font-size:0.88rem;}
.hero {padding:24px 26px;border:1px solid #203a57;border-radius:18px;background:radial-gradient(circle at 85% 0%,#16446a 0%,transparent 34%),linear-gradient(120deg,#12243a,#0e1a2b);margin-bottom:18px;}
.pill {display:inline-block;padding:5px 10px;border-radius:30px;background:#173a50;color:#8dd8ff;font-size:12px;font-weight:700;letter-spacing:.04em;}
</style>
""", unsafe_allow_html=True)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
WATCH_FILE = DATA_DIR / "watchlist.json"

def load_watchlist():
    try:
        return json.loads(WATCH_FILE.read_text())
    except Exception:
        return ["BRMS.JK", "ANTM.JK", "ADRO.JK", "^JKSE"]

def save_watchlist(items):
    WATCH_FILE.write_text(json.dumps(sorted(set(items)), indent=2))

if "watchlist" not in st.session_state:
    st.session_state.watchlist = load_watchlist()

if "universe" not in st.session_state:
    st.session_state.universe = DEFAULT_TICKERS.copy()

with st.sidebar:
    st.markdown("## 📈 JII70 QUANT PRO")
    st.caption("Islamic equities • Technical intelligence")
    page = st.radio("NAVIGASI", [
        "Dashboard", "Screener JII70", "Chart & Analisis", "Profil Perusahaan",
        "Watchlist", "Kalkulator Saham", "Berita Saham", "Pengaturan & Data"
    ])
    st.divider()
    st.markdown("**Koneksi data**")
    st.caption("Yahoo Finance / yfinance")
    st.caption("Refresh manual untuk mengambil data terbaru.")
    if st.button("↻ Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption("Build 1.0 • Data bukan feed bursa berlisensi")

def ticker_label(t):
    return t.replace(".JK","")

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

def candle_chart(df, title):
    d = indicators(df)
    if d.empty: 
        st.warning("Data chart tidak tersedia.")
        return
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=.04,
                        row_heights=[.72,.28], specs=[[{"secondary_y":True}],[{"secondary_y":False}]])
    fig.add_trace(go.Candlestick(x=d.index, open=d["Open"], high=d["High"], low=d["Low"], close=d["Close"], name="Candlestick"), row=1,col=1, secondary_y=False)
    for col, name in [("MA20","MA20"),("MA50","MA50"),("MA200","MA200")]:
        if col in d: fig.add_trace(go.Scatter(x=d.index,y=d[col],name=name,mode="lines",line=dict(width=1.4)),row=1,col=1,secondary_y=False)
    fig.add_trace(go.Bar(x=d.index,y=d["Volume"],name="Volume",opacity=.55),row=2,col=1)
    fig.update_layout(title=title, template="plotly_dark", height=650, xaxis_rangeslider_visible=False,
                      paper_bgcolor="#0e1a2b",plot_bgcolor="#0e1a2b",legend=dict(orientation="h",y=1.02),
                      margin=dict(l=15,r=15,t=60,b=15))
    fig.update_yaxes(title_text="Harga (IDR)",row=1,col=1)
    fig.update_yaxes(title_text="Volume",row=2,col=1)
    st.plotly_chart(fig,use_container_width=True)

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
    st.info("Universe awal memakai daftar yang pernah Anda kirim. Daftar tersebut belum lengkap 70 emiten; unggah file CSV resmi JII70 pada menu Pengaturan & Data untuk melengkapi dan memvalidasi konstituen.")
    st.subheader("Watchlist — ringkasan teknikal")
    rows=[]
    for t in st.session_state.watchlist[:20]:
        s=latest_snapshot(t)
        if s: rows.append(s)
    if rows:
        df=pd.DataFrame(rows)
        st.dataframe(df[["Kode","Harga","Chg %","RSI","Support","Resistance","Signal","Harga Buy","Harga Sell"]],use_container_width=True,hide_index=True)
    st.subheader("IHSG — candlestick 6 bulan")
    if idx:
        ih=load_one("^JKSE","6mo","1d")
        candle_chart(ih,"IHSG • 6 bulan • 1D")

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
    df=load_one(t,"6mo","1d")
    if df is not None and not df.empty:
        candle_chart(df,f"{ticker_label(t)} • Candlestick 6 bulan")
        snap=latest_snapshot(t)
        if snap:
            metric_cards(snap)
            st.markdown("**Rekomendasi teknikal**")
            st.write(snap["Signal"],"—",snap["Alasan"])
            st.write(f"Area buy indikatif: **{fmt_rupiah(snap['Harga Buy'])}** | Area sell/target indikatif: **{fmt_rupiah(snap['Harga Sell'])}**")
            st.caption(f"Timestamp candle terakhir: {snap['Waktu']}. Harga indikatif berdasarkan candle harian, bukan sinyal eksekusi intraday.")
    else: st.error("Yahoo Finance tidak mengembalikan data untuk ticker ini.")

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
        st.caption("Sumber profil: Yahoo Finance company profile. Untuk keputusan investasi, cocokkan dengan keterbukaan informasi, laporan keuangan, dan profil emiten di situs BEI/OJK.")
        st.link_button("Cari profil emiten di situs BEI",f"https://www.idx.co.id/id/perusahaan-tercatat/profil-perusahaan-tercatat/?kodeEmiten={ticker_label(t)}")
    else: st.warning("Profil belum tersedia. Periksa ticker atau coba lagi.")

elif page == "Watchlist":
    st.subheader("Watchlist pribadi")
    add=st.selectbox("Tambah saham",st.session_state.universe,format_func=ticker_label,key="watch_add")
    if st.button("＋ Tambahkan ke watchlist"):
        if add not in st.session_state.watchlist: st.session_state.watchlist.append(add); save_watchlist(st.session_state.watchlist)
        st.success(f"{ticker_label(add)} ditambahkan.")
    rows=[]
    for t in st.session_state.watchlist:
        s=latest_snapshot(t)
        if s: rows.append(s)
    if rows:
        st.dataframe(pd.DataFrame(rows)[["Kode","Harga","Chg %","RSI","Support","Resistance","Signal","Alasan"]],use_container_width=True,hide_index=True)
    rem=st.selectbox("Hapus dari watchlist",["—"]+st.session_state.watchlist,format_func=lambda x:ticker_label(x) if x!="—" else x)
    if st.button("Hapus pilihan") and rem!="—":
        st.session_state.watchlist=[x for x in st.session_state.watchlist if x!=rem]; save_watchlist(st.session_state.watchlist); st.rerun()

elif page == "Kalkulator Saham":
    st.subheader("Kalkulator transaksi saham")
    x1,x2,x3=st.columns(3)
    lot=x1.number_input("Jumlah lot",min_value=1,value=10,step=1)
    buy=x2.number_input("Harga beli / lembar (Rp)",min_value=1,value=1000,step=1)
    sell=x3.number_input("Harga jual / lembar (Rp)",min_value=1,value=1100,step=1)
    y1,y2=st.columns(2)
    buy_fee=y1.number_input("Fee beli (%)",min_value=0.0,value=0.15,step=0.01,format="%.2f")
    sell_fee=y2.number_input("Fee jual (%)",min_value=0.0,value=0.25,step=0.01,format="%.2f")
    qty=lot*100
    gross_buy=qty*buy; gross_sell=qty*sell
    fee_b=gross_buy*buy_fee/100; fee_s=gross_sell*sell_fee/100
    total_buy=gross_buy+fee_b; net_sell=gross_sell-fee_s
    pnl=net_sell-total_buy; pct=pnl/total_buy*100 if total_buy else 0
    m1,m2,m3,m4=st.columns(4)
    m1.metric("Modal + fee beli",fmt_rupiah(total_buy))
    m2.metric("Hasil bersih jual",fmt_rupiah(net_sell))
    m3.metric("Profit / loss",fmt_rupiah(pnl),f"{pct:+.2f}%")
    m4.metric("Jumlah saham",f"{qty:,} lembar")
    st.caption("Fee dapat berbeda menurut broker dan dapat berubah. Masukkan fee aktual dari sekuritas Anda. Perhitungan belum memasukkan pajak/biaya lain yang tidak tercakup pada fee input.")

elif page == "Berita Saham":
    st.subheader("Berita terkini terkait saham")
    q=st.text_input("Kata kunci berita",value="saham Indonesia BEI JII70")
    items=get_news(q)
    if items:
        for item in items:
            st.markdown(f"**[{item['title']}]({item['link']})**")
            st.caption(f"{item.get('publisher','Sumber online')} • {item.get('published','Waktu tidak tersedia')}")
            if item.get("summary"): st.write(item["summary"][:500])
            st.divider()
    else:
        st.info("Berita belum berhasil dimuat. Periksa koneksi internet atau coba kata kunci lain.")
    st.caption("Berita dikumpulkan dari RSS Google News yang mengindeks berbagai penerbit. Buka artikel sumber untuk membaca konteks dan verifikasi.")

elif page == "Pengaturan & Data":
    st.subheader("Universe JII70 & konfigurasi data")
    st.warning("Daftar yang tersedia dari percakapan sebelumnya belum memuat 70 kode secara lengkap. Jangan anggap daftar awal ini sebagai daftar resmi final.")
    st.write(f"Jumlah ticker tersedia: **{len(st.session_state.universe)}**")
    st.code(", ".join(ticker_label(t) for t in st.session_state.universe))
    up=st.file_uploader("Unggah CSV konstituen JII70 (kolom kode / ticker)",type=["csv"])
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
    st.download_button("Unduh template CSV",pd.DataFrame({"kode":["ANTM","BRMS","TLKM"]}).to_csv(index=False).encode(),"template_jii70.csv","text/csv")
    st.markdown("### Catatan sumber & kualitas data")
    st.markdown("""
- **Harga dan OHLCV:** Yahoo Finance melalui `yfinance`; ketersediaan, jeda, dan kelengkapan data bergantung pada Yahoo Finance.
- **Realtime:** aplikasi ini tidak menjamin streaming real-time atau harga eksekusi BEI. Gunakan feed resmi/broker berlisensi untuk transaksi.
- **Profil emiten:** Yahoo Finance; tautan profil BEI disediakan untuk pemeriksaan silang.
- **Berita:** RSS Google News; artikel berasal dari penerbit yang diindeks dan perlu dibaca pada situs asal.
- **Indeks IHSG:** simbol Yahoo Finance `^JKSE`.
- **Syariah:** keanggotaan JII70 harus divalidasi dengan daftar resmi BEI untuk periode berlaku. Screener teknikal tidak menentukan status syariah.
""")
