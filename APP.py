
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import unicodedata

# --- Configuration de la page ---
st.set_page_config(page_title="Répartition Budgétaire", layout="wide")
st.title("📊 Planification - Répartition Budgétaire SUNU IARD BF")

# --- Barre latérale ---
st.sidebar.header("📁 Données à charger")
histo_file = st.sidebar.file_uploader("Fichier Historique (CSV)", type="csv")
budget_file = st.sidebar.file_uploader("Fichier Budget alloué (CSV)", type="csv")
annee_cible = st.sidebar.number_input("Année cible", min_value=2022, value=2025)

# --- Réinitialisation ---
def reset_app():
    st.session_state.clear()

if st.sidebar.button("🔄 Réinitialiser"):
    reset_app()
    st.experimental_rerun()

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
    df_histo = pd.read_csv(histo_file, sep=";", encoding="utf-8")
    df_budget = pd.read_csv(budget_file, sep=";", encoding="utf-8")

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

    with st.expander("📌 Moyennes mensuelles par catégorie"):
        st.dataframe(pivot.round(2))

    with st.expander("📌 Ratios mensuels (poids par mois)"):
        st.dataframe(df_ratios.round(4))

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

    with st.expander(f"📌 Répartition Budget {annee_cible}"):
        st.dataframe(df_resultat.round(2))

    historique_moyenne = pivot.stack().reset_index().rename(columns={0: "Montant_Moyenne"})
    comparaison = df_resultat.merge(historique_moyenne, on=["Mois", "Categorie"], how="left")
    comparaison["Ecart"] = comparaison[f"Montant_{annee_cible}"] - comparaison["Montant_Moyenne"]

    with st.expander(f"📌 Tableau des écarts ({annee_cible} vs Moyenne historique)"):
        st.dataframe(comparaison.round(2))

    # --- Graphique Comparatif ---
    st.subheader("📈 Comparaison graphique avec les années précédentes")
    categorie_select = st.selectbox("Choisissez une catégorie", df_resultat["Categorie"].unique())
    temp_resultat = df_resultat[df_resultat["Categorie"] == categorie_select].set_index("Mois")
    temp_moy = historique_moyenne[historique_moyenne["Categorie"] == categorie_select].set_index("Mois")

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(temp_resultat.index, temp_resultat[f"Montant_{annee_cible}"], label=str(annee_cible), marker="o")
    ax.plot(temp_moy.index, temp_moy["Montant_Moyenne"], label="Moyenne sur 3 ans", linestyle="--")
    ax.set_title(f"Comparaison - {categorie_select}")
    ax.legend()
    st.pyplot(fig)

    # --- Total mensuel toutes catégories ---
    repartition["Total_Mensuel"] = repartition.drop(columns=["Mois"]).sum(axis=1)
    total_par_categorie = repartition.drop(columns=["Mois", "Total_Mensuel"]).sum()
    total_general_annuel = total_par_categorie.sum()

    st.subheader("📊 Total mensuel toutes catégories confondues")
    fig2, ax2 = plt.subplots(figsize=(14, 7))
    bars = sns.barplot(data=repartition, x="Mois", y="Total_Mensuel", color="skyblue", ax=ax2)
    ax2.set_title(f"Total mensuel - {annee_cible}")
    for container in bars.containers:
        bars.bar_label(container, fmt='%.0f', label_type='edge', fontsize=8)
    st.pyplot(fig2)

    # --- Totaux annuels par catégorie ---
    st.subheader("📉 Totaux annuels par catégorie")

    df_bar = pd.DataFrame({
        "Categorie": total_par_categorie.index,
        "Montant": total_par_categorie.values
    })

    fig3, ax3 = plt.subplots(figsize=(18, 7))

    palette = sns.color_palette("Set2", n_colors=len(df_bar))

    bars = sns.barplot(data=df_bar, x="Categorie", y="Montant", ax=ax3, color=None)

    for bar, color in zip(bars.patches, palette):
        bar.set_color(color)

    ax3.set_title(f"Totaux annuels par catégorie - {annee_cible}")

    for bar in bars.patches:
        height = bar.get_height()
        ax3.annotate(f"{height:,.0f}",
                     xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 5),
                     textcoords="offset points",
                     ha="center", fontsize=9)

    st.pyplot(fig3)

    # --- Répartition annuelle en pourcentage ---
    st.subheader("📊 Répartition annuelle en pourcentage par catégorie")
    pourcentages = (total_par_categorie / total_general_annuel * 100).round(2)
    fig4, ax4 = plt.subplots(figsize=(8, 8))
    ax4.pie(pourcentages.values, labels=pourcentages.index, autopct='%1.1f%%',
            startangle=90, colors=sns.color_palette("pastel"))
    ax4.axis('equal')
    ax4.set_title(f"Répartition annuelle {annee_cible} - Pourcentage par catégorie")
    st.pyplot(fig4)

    st.success(f"✅ Analyse terminée pour l'année {annee_cible}. Total annuel général : {total_general_annuel:,.0f} FCFA")

    # --- Export des résultats ---
    df_resultat["Annee"] = annee_cible
    df_export = df_resultat.rename(columns={f"Montant_{annee_cible}": "Montant"})
    df_export["Categorie"] = df_export["Categorie"].apply(nettoyer_categorie)
    df_export["Montant"] = df_export["Montant"].astype(float)

    df_histo_update = pd.concat([df_histo, df_export], ignore_index=True)
    df_histo_update["Categorie"] = df_histo_update["Categorie"].apply(nettoyer_categorie)
    df_histo_update["Montant"] = df_histo_update["Montant"].astype(float)

    with st.expander("📄 Exporter les résultats"):
        st.download_button(f"Télécharger la répartition {annee_cible} (CSV)",
                           data=df_export.to_csv(index=False, sep=';', encoding='utf-8-sig'),
                           file_name=f"repartition_{annee_cible}.csv",
                           mime='text/csv')

        st.download_button("Télécharger l'historique mis à jour (CSV)",
                           data=df_histo_update.to_csv(index=False, sep=';', encoding='utf-8-sig'),
                           file_name="historique_maj.csv",
                           mime='text/csv')

else:
    st.info("📥 Veuillez charger les deux fichiers CSV dans la barre latérale pour lancer l'analyse.")

