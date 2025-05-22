#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from io import StringIO

st.set_page_config(page_title="Répartition Budgétaire", layout="wide")
st.title("📊 Planification_Répartition Budgétaire SUNU IARD_BF")

# --- Barre latérale ---
st.sidebar.header("📁 Données à charger")
histo_file = st.sidebar.file_uploader("Fichier Historique (CSV)", type="csv")
budget_file = st.sidebar.file_uploader("Fichier Budget alloué (CSV)", type="csv")
annee_cible = st.sidebar.number_input("Année cible", min_value=2022, value=2025)

# Réinitialisation
def reset_app():
    st.session_state.clear()

if st.sidebar.button("🔄 Réinitialiser"):
    reset_app()
    st.rerun()

if histo_file and budget_file:
    df_histo = pd.read_csv(histo_file, sep=";", encoding="utf-8")
    df_budget = pd.read_csv(budget_file, sep=";", encoding="utf-8")

    df_histo.columns = df_histo.columns.str.strip()
    df_histo["Montant"] = pd.to_numeric(df_histo["Montant"], errors="coerce").fillna(0)

    mois_order = ["janv", "fev", "mar", "avr", "mai", "juin", "juill", "aout", "sep", "oct", "nov", "dec"]
    df_histo = df_histo[df_histo["Mois"].isin(mois_order)]
    df_histo["Mois"] = pd.Categorical(df_histo["Mois"], categories=mois_order, ordered=True)

    annees_historiques = [annee_cible - 3, annee_cible - 2, annee_cible - 1]
    histo_filtre = df_histo[df_histo["Annee"].isin(annees_historiques)]

    # Moyennes mensuelles par catégorie
    pivot = histo_filtre.pivot_table(index="Mois", columns="Categorie", values="Montant", aggfunc="mean", fill_value=0, observed=False)
    total_annuel = pivot.sum(axis=0)
    df_ratios = pivot.divide(total_annuel, axis=1).fillna(0)

    with st.expander("📌 Moyennes mensuelles par catégorie"):
        st.dataframe(pivot.round(2))

    with st.expander("📌 Ratios mensuels (poids par mois)"):
        st.dataframe(df_ratios.round(4))

    # Application des ratios au budget alloué
    repartition = pd.DataFrame(index=mois_order)
    for _, row in df_budget.iterrows():
        cat = row["Categorie"]
        budget = row["Budget_Alloue"]
        if cat in df_ratios.columns:
            repartition[cat] = df_ratios[cat] * budget
        else:
            repartition[cat] = 0

    repartition.index.name = "Mois"
    repartition = repartition.reset_index()
    df_resultat = pd.melt(repartition, id_vars="Mois", var_name="Categorie", value_name=f"Montant_{annee_cible}")

    with st.expander("📌 Répartition linéaire du budget"):
        st.dataframe(df_resultat.round(2))

    # Comparaison avec la moyenne historique
    historique_moyenne = pivot.stack().reset_index().rename(columns={0: "Montant_Moyenne"})
    comparaison = df_resultat.merge(historique_moyenne, on=["Mois", "Categorie"], how="left")
    comparaison["Ecart"] = comparaison[f"Montant_{annee_cible}"] - comparaison["Montant_Moyenne"]

    with st.expander("📌 Tableau des écarts (2025 vs Moyenne historique)"):
        st.dataframe(comparaison.round(2))

    # Graphiques interactifs
    st.subheader("📈 Comparaison graphique avec les années précédentes")
    categorie_select = st.selectbox("Choisissez une catégorie", df_resultat["Categorie"].unique())
    temp_2025 = df_resultat[df_resultat["Categorie"] == categorie_select].set_index("Mois")
    temp_moy = historique_moyenne[historique_moyenne["Categorie"] == categorie_select].set_index("Mois")

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(temp_2025.index, temp_2025[f"Montant_{annee_cible}"], label="2025 Calculé", marker="o")
    ax.plot(temp_moy.index, temp_moy["Montant_Moyenne"], label="Moyenne 2022–2024", linestyle="--")
    ax.set_title(f"Comparaison - {categorie_select}")
    ax.legend()
    st.pyplot(fig)

    # Totaux
    repartition["Total_Mensuel"] = repartition.drop(columns=["Mois"]).sum(axis=1)
    total_par_categorie = repartition.drop(columns=["Mois", "Total_Mensuel"]).sum()
    total_general_annuel = total_par_categorie.sum()

    st.subheader("📊 Total mensuel toutes catégories confondues")
    fig2, ax2 = plt.subplots(figsize=(14, 9))
    bars = sns.barplot(data=repartition, x="Mois", y="Total_Mensuel", color="skyblue", ax=ax2)
    ax2.set_title(f"Total mensuel - {annee_cible}")
    for bar in bars.containers[0]:
        height = bar.get_height()
        ax2.annotate(f"{height:,.0f}", xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 5), textcoords="offset points", ha="center", fontsize=9)
    st.pyplot(fig2)

    st.subheader("📉 Totaux annuels par catégorie")
    fig3, ax3 = plt.subplots(figsize=(20, 9))
    bars = sns.barplot(x=total_par_categorie.index, y=total_par_categorie.values, palette="Set2", ax=ax3)
    ax3.set_title("Totaux annuels par catégorie")
    for bar in bars.patches:
        height = bar.get_height()
        ax3.annotate(f"{height:,.0f}", xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 5), textcoords="offset points", ha="center", fontsize=9)
    st.pyplot(fig3)

    st.subheader("📊 Répartition annuelle en pourcentage par catégorie")
    pourcentages = (total_par_categorie / total_general_annuel * 100).round(2)

    fig4, ax4 = plt.subplots(figsize=(8, 8))
    ax4.pie(pourcentages.values, labels=pourcentages.index, autopct='%1.1f%%', startangle=90, colors=sns.color_palette("pastel"))
    ax4.axis('equal')  # Pour que le camembert soit circulaire
    ax4.set_title(f"Répartition annuelle {annee_cible} - Pourcentage par catégorie")
    st.pyplot(fig4)


    st.success(f"✅ Analyse terminée pour l'année {annee_cible}. Total annuel général : {total_general_annuel:,.0f} FCFA")

    # Fusion avec l'historique
    df_resultat["Annee"] = annee_cible
    df_export = df_resultat.rename(columns={f"Montant_{annee_cible}": "Montant"})
    df_histo_update = pd.concat([df_histo, df_export], ignore_index=True)

    # Nettoyage encodage avant export
    df_export_clean = df_export.copy()
    df_export_clean["Categorie"] = df_export_clean["Categorie"].astype(str).str.normalize('NFKD').str.encode('utf-8', errors='ignore').str.decode('utf-8')
    df_export_clean["Montant"] = df_export_clean["Montant"].astype(float)

    df_histo_update_clean = df_histo_update.copy()
    df_histo_update_clean["Categorie"] = df_histo_update_clean["Categorie"].astype(str).str.normalize('NFKD').str.encode('utf-8', errors='ignore').str.decode('utf-8')
    df_histo_update_clean["Montant"] = df_histo_update_clean["Montant"].astype(float)

    with st.expander("📄 Exporter les résultats"):
        st.download_button("Télécharger la répartition 2025 (CSV)",
                           data=df_export_clean.to_csv(index=False, sep=';', encoding='utf-8-sig'),
                           file_name=f"repartition_{annee_cible}.csv",
                           mime='text/csv')

        st.download_button("Télécharger l'historique mis à jour (CSV)",
                           data=df_histo_update_clean.to_csv(index=False, sep=';', encoding='utf-8-sig'),
                           file_name="historique_maj.csv",
                           mime='text/csv')

else:
    st.info("Veuillez charger les deux fichiers CSV dans la barre latérale pour lancer l'analyse.")



# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:




