import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import unicodedata
import plotly.express as px
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder

# --- Configuration de la page ---
st.set_page_config(page_title="Répartition Budgétaire", layout="wide")
st.title("📊 Planification - Répartition Budgétaire SUNU IARD BF")

# --- Barre latérale ---
st.sidebar.header("📁 Données à charger")
histo_file = st.sidebar.file_uploader("Fichier Historique (CSV)", type="csv")
budget_file = st.sidebar.file_uploader("Fichier Budget alloué (CSV)", type="csv")
annee_cible = st.sidebar.number_input("Année cible", min_value=2022, value=2025)


# --- Fonction de nettoyage des catégories ---
def nettoyer_categorie(cat):
    if pd.isnull(cat):
        return "Inconnu"
    cat = str(cat)
    cat = unicodedata.normalize('NFKD', cat).encode('ASCII', 'ignore').decode()
    cat = cat.lower()
    cat = cat.replace("’", "").replace("'", "").replace("‘", "")
    cat = cat.replace("-", " ").replace(",", "").replace("|", "").replace("\n", "")
    cat = cat.replace("  ", " ").strip()

    correspondances = {
        "dotations aux amrt & prov": "Dotations aux Amrt & Prov",
        "frais de personnel": "Frais de personnel",
        "frais divers de gestion": "Frais divers de gestion",
        "impots et taxes": "Impôts et taxes",
        "transports et deplacements": "Transports et déplacements",
        "travaux fournitures et services exterieurs": "Travaux, fournitures et services extérieurs"
    }

    for cle, val in correspondances.items():
        if cle in cat:
            return val
    return cat.title()

# --- Traitement principal ---
if histo_file and budget_file:
    with st.spinner("🔍 Traitement des données en cours..."):
        df_histo = pd.read_csv(histo_file, sep=";", encoding="utf-8")
        df_budget = pd.read_csv(budget_file, sep=";", encoding="utf-8")

        st.subheader("📄 Aperçu des fichiers")
        with st.expander("Aperçu - Historique"):
            st.dataframe(df_histo.head())
        with st.expander("Aperçu - Budget"):
            st.dataframe(df_budget.head())

        df_histo.columns = df_histo.columns.str.strip()
        df_histo["Montant"] = pd.to_numeric(df_histo["Montant"], errors="coerce").fillna(0)
        df_histo["Categorie"] = df_histo["Categorie"].apply(nettoyer_categorie)
        df_budget["Categorie"] = df_budget["Categorie"].apply(nettoyer_categorie)

        mois_order = ["janv", "fev", "mar", "avr", "mai", "juin", "juill", "aout", "sep", "oct", "nov", "dec"]
        df_histo = df_histo[df_histo["Mois"].isin(mois_order)]
        df_histo["Mois"] = pd.Categorical(df_histo["Mois"], categories=mois_order, ordered=True)

        annees_historiques = [annee_cible - 3, annee_cible - 2, annee_cible - 1]
        histo_filtre = df_histo[df_histo["Annee"].isin(annees_historiques)]

        pivot = histo_filtre.pivot_table(index="Mois", columns="Categorie", values="Montant",
                                         aggfunc="mean", fill_value=0, observed=False)
        total_annuel = pivot.sum(axis=0)
        df_ratios = pivot.divide(total_annuel, axis=1).fillna(0)

        # --- Calcul répartition ---
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
        df_resultat["Categorie"] = df_resultat["Categorie"].apply(nettoyer_categorie)

        # --- Moyennes et écarts ---
        historique_moyenne = pivot.stack().reset_index().rename(columns={0: "Montant_Moyenne"})
        comparaison = df_resultat.merge(historique_moyenne, on=["Mois", "Categorie"], how="left")
        comparaison["Ecart"] = comparaison[f"Montant_{annee_cible}"] - comparaison["Montant_Moyenne"]

        # --- Organisation par onglets ---
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Tableaux", "📈 Graphiques", "📊 Totaux", "📥 Export", "⚙️ Paramètres"])

        with tab1:
            st.subheader("📌 Moyennes mensuelles par catégorie")
            AgGrid(pivot.round(2))

            st.subheader("📌 Ratios mensuels")
            AgGrid(df_ratios.round(4))

            st.subheader(f"📌 Répartition Budget {annee_cible}")
            AgGrid(df_resultat.round(2))

            st.subheader("📌 Tableau des écarts")
            AgGrid(comparaison.round(2))

        with tab2:
            st.subheader("📈 Comparaison graphique")
            categories = st.multiselect("Choisissez une ou plusieurs catégories", df_resultat["Categorie"].unique())
            for cat in categories:
                temp_resultat = df_resultat[df_resultat["Categorie"] == cat]
                temp_moy = historique_moyenne[historique_moyenne["Categorie"] == cat]
                fig = px.line(temp_resultat, x="Mois", y=f"Montant_{annee_cible}", title=f"{cat} - {annee_cible}", markers=True)
                fig.add_scatter(x=temp_moy["Mois"], y=temp_moy["Montant_Moyenne"], mode="lines", name="Moyenne 3 ans")
                st.plotly_chart(fig, use_container_width=True)

        with tab3:
            repartition["Total_Mensuel"] = repartition.drop(columns=["Mois"]).sum(axis=1)
            total_par_categorie = repartition.drop(columns=["Mois", "Total_Mensuel"]).sum()
            total_general_annuel = total_par_categorie.sum()

            st.subheader("📊 Total mensuel")
            fig2 = px.bar(repartition, x="Mois", y="Total_Mensuel", title="Total mensuel toutes catégories")
            st.plotly_chart(fig2, use_container_width=True)

            st.subheader("📉 Totaux annuels par catégorie")
            df_bar = pd.DataFrame({"Categorie": total_par_categorie.index, "Montant": total_par_categorie.values})
            fig3 = px.bar(df_bar, x="Categorie", y="Montant", color="Categorie", title="Totaux annuels")
            st.plotly_chart(fig3, use_container_width=True)

            st.subheader("📊 Répartition annuelle en %")
            pourcentages = (total_par_categorie / total_general_annuel * 100).round(2)
            fig4 = px.pie(values=pourcentages.values, names=pourcentages.index, title="Répartition annuelle en %")
            st.plotly_chart(fig4)

        with tab4:
            df_resultat["Annee"] = annee_cible
            df_export = df_resultat.rename(columns={f"Montant_{annee_cible}": "Montant"})
            df_export["Montant"] = df_export["Montant"].astype(float)
            df_histo_update = pd.concat([df_histo, df_export], ignore_index=True)

            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                pivot.to_excel(writer, sheet_name="Moyennes")
                df_ratios.to_excel(writer, sheet_name="Ratios")
                df_resultat.to_excel(writer, sheet_name="Répartition")
                comparaison.to_excel(writer, sheet_name="Écarts")
            st.download_button("📥 Télécharger le fichier Excel complet", data=buffer.getvalue(), file_name=f"budget_{annee_cible}.xlsx")

        with tab5:
            st.markdown("**Années utilisées pour les moyennes :**")
            st.write(annees_historiques)

    st.success(f"✅ Analyse terminée pour l'année {annee_cible}. Total général : {total_general_annuel:,.0f} FCFA")

else:
    st.info("📥 Veuillez charger les deux fichiers CSV dans la barre latérale pour lancer l'analyse.")

