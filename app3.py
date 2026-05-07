import streamlit as st
import yfinance as yf
import pandas as pd
import io
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Autentification
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.title("🔐 Accès à l'application")

    nom = st.text_input("Nom")
    prenom = st.text_input("Prénom")
    mot_de_passe = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter"):
        if not nom.strip() or not prenom.strip() or not mot_de_passe.strip():
            st.error("Veuillez remplir Nom, Prénom et Mot de passe.")
        else:
            st.session_state["logged_in"] = True
            st.session_state["nom"] = nom.strip()
            st.session_state["prenom"] = prenom.strip()

    # Bloque tout le reste tant que pas connecté
    st.stop()

# Configuration et style
st.set_page_config(layout="wide")
st.title("TABLEAU DE BORD - Yahoo Finance")

st.markdown(
    """
    <style>
    .main {
        background-color: #F8F9FA;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #302F7C;
        font-family: 'Segoe UI', sans-serif;
    }
    .sidebar .sidebar-content {
        background-color: #F1F3F8;
    }
    .stAlert, .stSuccess, .stError, .stInfo {
        border-radius: 8px;
    }
    .stButton > button {
        background-color: #302F7C !important;
        color: white !important;
        border-radius: 8px;
        font-size: 14px;
    }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.1);
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.write(f"Bienvenue, {st.session_state['prenom']} {st.session_state['nom']} 👋")

# Recuperation des données
def get_data(tickers, period):
    data = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            info = stock.info if hasattr(stock, "info") else {}
            data[ticker] = {"hist": hist, "info": info}
        except Exception as e:
            st.warning(f"Erreur pour {ticker} : {e}")
    return data

# Filtres
st.sidebar.header("Filtres")
st.sidebar.markdown("---")

if st.sidebar.button("🔄 Actualiser les données"):
    st.rerun()

ticker_list = ["AAPL", "MSFT", "TSLA", "GOOGL", "NVDA", "AMZN", "META"]
chosen_ticker = st.sidebar.selectbox(
    "1. Choisir une entreprise",
    options=ticker_list,
    key="ticker_select"
)

st.sidebar.header("Période de données")
period_map = {
    "1 mois": "1mo",
    "3 mois": "3mo",
    "6 mois": "6mo",
    "1 an": "1y",
    "2 ans": "2y",
    "5 ans": "5y",
    "Tout l'historique": "max"
}
selected_period_label = st.sidebar.selectbox(
    "Période",
    list(period_map.keys()),
    index=3,
    key="period_select"
)
selected_period = period_map[selected_period_label]

#  Récuperation des données pour chaque ticker
all_data = get_data(ticker_list, selected_period)
d = all_data.get(chosen_ticker, {})
if not d:
    st.error("Aucune donnée disponible pour ce ticker.")
    st.stop()

hist = d.get("hist", pd.DataFrame())
info = d.get("info", {})

if hist.empty:
    st.error("Aucune donnée pour ce ticker.")
    st.stop()

# SYNTHÈSE KPIs 
price = hist.Close.iloc[-1] if len(hist) > 0 else 0.0
change = hist.Close.pct_change().iloc[-1] * 100 if len(hist) > 1 else 0
volume = hist.Volume.iloc[-1] if "Volume" in hist.columns and len(hist) > 0 else 0
market_cap = info.get("marketCap", None)
mcap = f"{market_cap / 1e9:.2f} Md$" if market_cap else "N/A"

st.header(f"Synthèse - {chosen_ticker}")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Prix actuel", f"{price:.2f} $")
with col2:
    st.metric("Variation", f"{change:+.2f} %")
with col3:
    st.metric("Volume", f"{volume:,.0f}")
with col4:
    st.metric("Cap. boursière", mcap)

# FILTRE PAR ANNÉE + INTERPRÉTATION BOUGIE ---
st.sidebar.subheader("📅 Filtre par année")
years = pd.to_datetime(hist.index).year.unique()
years = sorted(years, reverse=True)
selected_year = st.sidebar.selectbox("Choisissez une année", years)
hist_filtered = hist[pd.to_datetime(hist.index).year == selected_year]

st.sidebar.markdown("### 🔍 Interprétation par bougie")
all_dates = hist_filtered.index.strftime('%Y-%m-%d')
selected_date_str = st.sidebar.selectbox(
    "Choisissez une date",
    all_dates,
    key="candle_date"
)

# GRAPHES COLONNES A ET B ---
st.markdown("---")
st.header("Grap")

colA, colB = st.columns(2)

# Graphique en bougies (colA) 
with colA:
    st.markdown("Bougies")

    selected_row = hist_filtered[
        hist_filtered.index.strftime('%Y-%m-%d') == selected_date_str
    ].iloc[0]

    st.markdown("#### Interprétation de la bougie")
    st.write(
        f"**{selected_row.name.strftime('%Y-%m-%d')}** : "
        f"Prix d'ouverture : **{selected_row.Open.item():.2f} $**, "
        f"Prix de clôture : **{selected_row.Close.item():.2f} $**"
    )

    if selected_row.Close.item() > selected_row.Open.item():
        st.success(":green[✓] Prix montant → Tendance haussière pour ce jour.")
    elif selected_row.Close.item() < selected_row.Open.item():
        st.error(":red[✗] Prix descendant → Tendance baissière pour ce jour.")
    else:
        st.info(":blue[≈] Prix stable → Pas de variation significative.")

    fig1 = go.Figure()
    fig1.add_trace(go.Candlestick(
        x=hist_filtered.index,
        open=hist_filtered.Open,
        high=hist_filtered.High,
        low=hist_filtered.Low,
        close=hist_filtered.Close,
        name=chosen_ticker
    ))
    fig1.update_layout(
        title="",
        xaxis_title="Date",
        yaxis_title="Prix ($)",
        template="plotly_white",
        hovermode="x unified"
    )
    st.plotly_chart(fig1, use_container_width=True, key="plot_bougies")

# Graphique Prix + Volume (colB) 
with colB:
    st.markdown("📊 Volume")
    st.markdown("#### Interprétation prix + volume (7 jours)")

    if len(hist) >= 7:
        last_7 = hist.tail(7)
        first_price = last_7.Close.iloc[0]
        last_price = last_7.Close.iloc[-1]
        first_volume = last_7.Volume.iloc[0]
        last_volume = last_7.Volume.iloc[-1]

        price_up = last_price > first_price
        volume_up = last_volume > first_volume

        if price_up and volume_up:
            st.success(
                f":green[✓] Prix montant + Volume montant → Tendance haussière forte sur 7 jours. "
                f"De {first_price:.2f}$ à {last_price:.2f}$."
            )
        elif price_up and not volume_up:
            st.warning(
                f":orange[⚠] Prix montant + Volume descendant → Hausse fragile sur 7 jours. "
                f"De {first_price:.2f}$ à {last_price:.2f}$."
            )
        elif not price_up and volume_up:
            st.error(
                f":red[✗] Prix descendant + Volume important → Tendance baissière forte sur 7 jours. "
                f"De {first_price:.2f}$ à {last_price:.2f}$."
            )
        else:
            st.info(
                f":blue[≈] Prix descendant ou stable + Volume faible → Baisse modérée sur 7 jours. "
                f"De {first_price:.2f}$ à {last_price:.2f}$."
            )
    else:
        st.write("- Pas assez de données sur 7 jours.")

    fig2 = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=("Prix de clôture", "Volume")
    )
    fig2.add_trace(
        go.Scatter(
            x=hist.index,
            y=hist.Close,
            mode="lines",
            name="Close",
            line=dict(color="red")
        ),
        row=1, col=1
    )
    fig2.add_trace(
        go.Bar(
            x=hist.index,
            y=hist.Volume,
            name="Volume",
            marker=dict(color="lightgray")
        ),
        row=2, col=1
    )
    fig2.update_layout(
        title="",
        template="plotly_white",
        hovermode="x unified",
        height=500
    )
    fig2.update_traces(marker_color="#302F7C")
    st.plotly_chart(fig2, use_container_width=True, key="plot_cours_volume")

#  Base de donnée
st.markdown("---")
st.header(f"Données brutes - {chosen_ticker}")
st.dataframe(hist, use_container_width=True)

csv = hist.to_csv().encode("utf-8")
st.download_button(
    label=f"Télécharger {chosen_ticker} en CSV",
    data=csv,
    file_name=f"{chosen_ticker}_{selected_period_label}.csv",
    mime="text/csv",
    key=f"download_{chosen_ticker.lower()}"
)

# Export Excel (sans fuseau horaire)
hist_naive = hist.copy()
hist_naive.index = hist_naive.index.tz_localize(None)
hist_export = hist_naive.reset_index()

buffer = io.BytesIO()
hist_export.to_excel(buffer, sheet_name="Données", index=False)

st.download_button(
    label="⬇ Télécharger en Excel",
    data=buffer.getvalue(),
    file_name=f"{chosen_ticker}_{selected_period_label}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)