import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

from base_builder import FundDatabaseBuilder
from strategie_1 import PreSelectorESG
from strategie_2 import StrategyEngine
from performances import PerformanceAnalyzer

st.set_page_config(page_title="Fonds ESG", layout="wide")
st.title("🌱 Fonds ESG — Simulation dynamique")

DB_PATH = "Fund.db"

# CONTRÔLES ESG DANS LA SIDEBAR
st.sidebar.header("📏 Contraintes ESG personnalisées")

score_env_max = st.sidebar.slider("Score Environnement max", 0, 26, 2)
score_social_max = st.sidebar.slider("Score Social max", 0, 22, 8)
score_gouv_max = st.sidebar.slider("Score Gouvernance max", 0, 20, 5)
score_total_max = st.sidebar.slider("Score ESG total max", 0, 44, 17)

# EXÉCUTION COMPLÈTE
if st.sidebar.button("⏸️ Exécuter toute la stratégie"):

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        st.sidebar.info("🧹 Base supprimée")

    builder = FundDatabaseBuilder()
    builder.build_database()
    with sqlite3.connect(builder.db_file) as conn:
        cursor = conn.cursor()
        builder.build_base(cursor)
        conn.commit()

    st.sidebar.write("📊 Application des seuils ESG")

    class ESGSelectorCustom(PreSelectorESG):
        def filter_by_portfolio(self, products, portfolio_name):
            if portfolio_name == "Green Growth Leader":
                return [p["product_id"] for p in products if p["score_environment"] is not None and p["score_environment"] <= score_env_max]
            elif portfolio_name == "Stability":
                return [p["product_id"] for p in products if (
                    p["score_social"] is not None and p["score_social"] <= score_social_max and
                    p["score_governance"] is not None and p["score_governance"] <= score_gouv_max
                )]
            elif portfolio_name == "ESG Global":
                return [p["product_id"] for p in products if p["score_total"] is not None and p["score_total"] <= score_total_max]
            else:
                return []

    ESGSelectorCustom().update_range_products()

    StrategyEngine().run_strategie("2020-01-01", "2024-12-31")
    st.sidebar.success("✅ Simulation terminée !")

# VISUALISATION DES PERFORMANCES
if os.path.exists(DB_PATH):
    st.subheader("📈 Résultats de la simulation")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    df_perf = pd.read_sql_query("SELECT date, portfolio_id, nom_portefeuille, rendement_moyen FROM Portefeuilles_suivi", conn)
    df_perf['date'] = pd.to_datetime(df_perf['date'])

    portefeuilles = df_perf['nom_portefeuille'].unique()
    selected = st.selectbox("📌 Choisir un portefeuille", portefeuilles)

    df_selected = df_perf[df_perf['nom_portefeuille'] == selected].copy()
    df_selected['cumulative_return'] = df_selected['rendement_moyen'].cumsum()

    cum = df_selected['rendement_moyen'].sum()
    n_years = (df_selected['date'].max() - df_selected['date'].min()).days / 365.25
    annual_return = (1 + cum) ** (1 / n_years) - 1
    vol = df_selected['rendement_moyen'].std() * (12 ** 0.5)
    sharpe = (annual_return - 0.01) / vol

    col1, col2, col3 = st.columns(3)
    col1.metric("🎯 Rendement annualisé", f"{annual_return*100:.2f}%")
    col2.metric("📉 Volatilité annualisée", f"{vol*100:.2f}%")
    col3.metric("📈 Sharpe ratio", f"{sharpe:.2f}")

    st.subheader(f"📊 Performance cumulative — {selected}")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df_selected['date'], df_selected['cumulative_return'], label=selected)
    ax.set_xlabel("Date")
    ax.set_ylabel("Rendement cumulé")
    ax.legend()
    st.pyplot(fig)

    # Détail portefeuille : Deals et composition
    st.subheader(f"📖 Détail du portefeuille : {selected}")

    min_date = df_selected["date"].min().to_pydatetime().date()
    max_date = df_selected["date"].max().to_pydatetime().date()

    date_range = st.slider(
        "🗓️ Sélectionner une période",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM"
    )

    start_date, end_date = date_range

    cursor.execute("SELECT product_id, ticker FROM Products")
    id_to_ticker = dict(cursor.fetchall())

    df_deals = pd.read_sql_query("""
        SELECT date, actif_achete, actif_vendu
        FROM Deals
        WHERE portefeuille_id = (
            SELECT portfolio_id FROM Portfolios WHERE nom_portefeuille = ?
        )
        AND date BETWEEN ? AND ?
        ORDER BY date ASC
    """, conn, params=(selected, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))

    st.markdown("### 🔁 Transactions mensuelles (achats / ventes)")
    st.dataframe(df_deals)

    df_alloc = pd.read_sql_query("""
        SELECT date, produits
        FROM Portefeuilles_suivi
        WHERE nom_portefeuille = ?
        AND date BETWEEN ? AND ?
        ORDER BY date ASC
    """, conn, params=(selected, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))

    df_alloc['produits'] = df_alloc['produits'].apply(
        lambda x: ", ".join([id_to_ticker.get(pid, f"ID{pid}") for pid in eval(x)]) if x else ""
    )

    st.markdown("### 📄 Composition historique du portefeuille")
    st.dataframe(df_alloc)
    st.subheader("💸 Comparaison des portefeuilles (rendement cumulé)")
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    for name, group in df_perf.groupby("nom_portefeuille"):
        group = group.sort_values("date").copy()
        group['cumulative_return'] = group['rendement_moyen'].cumsum()
        ax2.plot(group['date'], group['cumulative_return'], label=name)
    ax2.set_xlabel("Date")
    ax2.set_ylabel("Rendement cumulé")
    ax2.set_title("Performance cumulative comparée")
    ax2.legend()
    st.pyplot(fig2)

else:
    st.info("Cliquez sur ⏸️ dans la sidebar pour lancer une simulation.")