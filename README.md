# 🌱 Fonds ESG — Simulateur de gestion de portefeuille

Cette application Streamlit permet de simuler la gestion dynamique de portefeuilles d'actifs financiers selon des **critères ESG** personnalisés (Environnement, Social, Gouvernance).

---

## ⚙️ Fonctionnement

1. **Chargement des données**
   - Rendements historiques des actifs
   - Scores ESG : environnement, social, gouvernance

2. **Pré-sélection ESG**
   - Trois portefeuilles :
     - `Green Growth Leader` (filtre Environnement)
     - `Stability` (filtres Social & Gouvernance)
     - `ESG Global` (filtre ESG total)

3. **Stratégie dynamique mensuelle**
   - Sélection des meilleurs actifs selon le **momentum**
   - Rebalancement mensuel automatique (achat/vente)
   - Suivi des performances et des compositions

---

## 🖥️ Interface utilisateur

- 📊 Sélection d’un portefeuille et visualisation :
  - Rendement annualisé, volatilité, Sharpe Ratio
  - Graphique cumulatif des performances
  - Historique des deals (achats/ventes)
  - Composition mensuelle du portefeuille (tickers)

- 📅 Filtrage par période

- 💸 Comparaison des portefeuilles (rendement cumulé)
