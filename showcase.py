import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Showcase - Budget Lab", layout="wide")

# --- FONCTION DE NORMALISATION ---
def nettoyer_categorie(cat):
    if pd.isna(cat): return "Inconnue"
    s = str(cat).lower().strip()
    import unicodedata
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s.capitalize()

# --- CHARGEMENT AUTOMATIQUE DES DONNÉES (VERSION SHOWCASE) ---
@st.cache_data
def load_and_process_data():
    try:
        # Lecture des fichiers locaux [cite: 43-45]
        df_hist = pd.read_csv('historique_frais.csv', sep=';')
        df_budget = pd.read_csv('budget_alloue.csv', sep=';')
        
        # Nettoyage des noms de colonnes
        df_hist.columns = [c.strip() for c in df_hist.columns]
        df_budget.columns = [c.strip() for c in df_budget.columns]
        
        # Conversion numérique [cite: 48, 89]
        df_hist['Montant'] = pd.to_numeric(df_hist['Montant'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        df_budget['Budget_Alloue'] = pd.to_numeric(df_budget['Budget_Alloue'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        
        # Normalisation des catégories [cite: 90]
        df_hist['Categorie'] = df_hist['Categorie'].apply(nettoyer_categorie)
        df_budget['Categorie'] = df_budget['Categorie'].apply(nettoyer_categorie)
        
        # Ordre chronologique [cite: 49, 91]
        ordre_mois = ['janv', 'fev', 'mar', 'avr', 'mai', 'juin', 'juill', 'aout', 'sep', 'oct', 'nov', 'dec']
        df_hist['Mois'] = pd.Categorical(df_hist['Mois'], categories=ordre_mois, ordered=True)
        
        return df_hist, df_budget, ordre_mois
    except Exception as e:
        st.error(f"Erreur de chargement : {e}")
        return None, None, None

# --- CALCULS ---
df_hist, df_budget, ordre_mois = load_and_process_data()

if df_hist is not None:
    # 1. Moyennes sur 3 ans (2022-2024) [cite: 52, 93]
    annee_cible = 2025
    df_3ans = df_hist[df_hist['Annee'].isin([annee_cible-3, annee_cible-2, annee_cible-1])]
    # observed=False pour éviter le warning console
    pivot_moyennes = df_3ans.pivot_table(index='Mois', columns='Categorie', values='Montant', aggfunc='mean', observed=False).fillna(0)
    
    # 2. Calcul des ratios [cite: 61, 101]
    ratios = pivot_moyennes.div(pivot_moyennes.sum(axis=0), axis=1).fillna(0)
    
    # 3. Répartition 2025 [cite: 65, 104]
    budget_2025 = pd.DataFrame(index=ordre_mois)
    for cat in df_budget['Categorie'].unique():
        montant_total = df_budget[df_budget['Categorie'] == cat]['Budget_Alloue'].values[0]
        if cat in ratios.columns:
            budget_2025[cat] = ratios[cat] * montant_total
        else:
            budget_2025[cat] = montant_total / 12

    # --- UI STREAMLIT ---
    st.title("📊 Mensualisation Budgétaire Dynamique")
    st.sidebar.markdown("### 🏷️ Infos Projet")
    st.sidebar.info("Données historiques 2022-2024 chargées. Analyse prédictive pour 2025 active.")
    st.sidebar.metric("Enveloppe Budget 2025", f"{df_budget['Budget_Alloue'].sum():,.0f} FCFA")

    tabs = st.tabs(["📋 Données", "📈 Analyses Graphiques", "💰 Totaux & Parts", "💡 Méthodologie", "📤 Export"])

    with tabs[0]:
        st.subheader("Prévisions Mensualisées 2025")
        st.dataframe(budget_2025.style.format("{:,.0f}"), width='stretch')

    with tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            # Courbe par catégorie [cite: 109]
            selected_cat = st.selectbox("Choisir une catégorie pour la courbe", budget_2025.columns)
            fig_line = px.line(budget_2025, y=selected_cat, title=f"Profil de dépense : {selected_cat}", markers=True)
            st.plotly_chart(fig_line, width='stretch')
        
        with col2:
            # Charge totale mensuelle (Histogramme) [cite: 71, 110]
            total_mensuel = budget_2025.sum(axis=1)
            fig_bar_mensuel = px.bar(x=total_mensuel.index, y=total_mensuel.values, 
                                     title="Charge Totale Mensuelle (Toutes catégories)",
                                     labels={'x': 'Mois', 'y': 'Montant Total'})
            st.plotly_chart(fig_bar_mensuel, width='stretch')

    with tabs[2]:
        col3, col4 = st.columns(2)
        with col3:
            # Barplot des totaux annuels par catégorie [cite: 73, 111]
            fig_bar_annuel = px.bar(df_budget, x='Categorie', y='Budget_Alloue', 
                                    title="Budget Annuel par Type de Frais",
                                    color='Categorie')
            st.plotly_chart(fig_bar_annuel, width='stretch')
        
        with col4:
            # Camembert de répartition [cite: 72, 112]
            fig_pie = px.pie(df_budget, values='Budget_Alloue', names='Categorie', title="Répartition (%) du Budget 2025")
            st.plotly_chart(fig_pie, width='stretch')

    with tabs[3]:
        st.markdown("""
        ### 🧠 Algorithme de Mensualisation Pondérée
        Ce projet remplace la division linéaire par une **projection saisonnière** :
        1. **Moyennes glissantes** : Calcul des dépenses réelles par mois sur les 36 derniers mois[cite: 16, 93].
        2. **Modélisation des poids** : Déduction du ratio de consommation mensuelle pour chaque type de frais[cite: 22, 101].
        3. **Ajustement budgétaire** : Application automatique aux nouvelles enveloppes pour 2025[cite: 30, 105].
        """)

    with tabs[4]:
        st.subheader("Générer le rapport final")
        
        # Préparation du fichier Excel en mémoire pour l'export [cite: 117]
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            budget_2025.to_excel(writer, sheet_name='Repartition_2025')
            pivot_moyennes.to_excel(writer, sheet_name='Moyennes_Historiques')
            ratios.to_excel(writer, sheet_name='Ratios_Ponderation')
        
        # Le bouton de téléchargement qui fonctionne réellement [cite: 118]
        st.download_button(
            label="📥 Télécharger le Rapport Budgétaire (Excel)",
            data=output.getvalue(),
            file_name="Résumé.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.info("Le fichier contient les prévisions, les moyennes historiques et les ratios de calcul.")

else:
    st.error("Assurez-vous que les fichiers 'historique_frais.csv' et 'budget_alloue.csv' sont bien présents dans votre dossier Jupyter.")