import pdfplumber
import re
import spacy
from pathlib import Path

# Charger le modèle spaCy français pour correction linguistique
try:
    nlp = spacy.load("fr_core_news_md")
except:
    nlp = None
    print("Le modèle spaCy 'fr_core_news_md' n'est pas installé. Lancez : python -m spacy download fr_core_news_md")

def clean_line(line):
    # Correction des mots collés type 'Chapitre1:Régressionlinéairesimple' -> 'Chapitre 1 : Régression linéaire simple'
    line = re.sub(r'(Chapitre)([0-9]+)', r'\1 \2', line)
    line = re.sub(r'([a-z])([A-Z])', r'\1 \2', line)
    line = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', line)
    line = re.sub(r'([0-9])([a-zA-Z])', r'\1 \2', line)
    # Espaces après ponctuation
    line = re.sub(r'([.,;:!?])([^ ])', r'\1 \2', line)
    # Nettoyage artefacts
    line = re.sub(r'cid:[0-9]+', '', line)
    line = re.sub(r'\s+', ' ', line)
    return line.strip()

def correct_text_with_spacy(text):
    if nlp is None:
        return text
    doc = nlp(text)
    # Recréer le texte avec une segmentation propre
    sentences = [sent.text.strip() for sent in doc.sents]
    return '\n'.join(sentences)

def extract_tables(page):
    tables_md = ""
    tables = page.extract_tables()
    for table in tables:
        if not table or len(table) < 2:
            continue
        # Remplacer None par "" dans chaque cellule
        table = [[cell if cell is not None else "" for cell in row] for row in table]
        header = '| ' + ' | '.join(table[0]) + ' |\n'
        sep = '| ' + ' | '.join(['---'] * len(table[0])) + ' |\n'
        rows = ''
        for row in table[1:]:
            rows += '| ' + ' | '.join(row) + ' |\n'
        tables_md += '\n' + header + sep + rows + '\n'
    return tables_md

def extract_and_format_markdown(pdf_path, output_md):
    with pdfplumber.open(pdf_path) as pdf:
        all_text = ""
        for page in pdf.pages:
            # Extraction du texte brut
            text = page.extract_text() or ""
            # Extraction des tableaux
            tables_md = extract_tables(page)
            # Nettoyage ligne par ligne
            lines = [clean_line(line) for line in text.split('\n') if line.strip()]
            page_text = '\n'.join(lines)
            # Correction linguistique avancée
            page_text = correct_text_with_spacy(page_text)
            # Mise en forme Markdown (titres, sous-titres)
            lines = page_text.split('\n')
            for line in lines:
                if re.match(r'^[A-Z][A-Z\s\-]+$', line) and len(line) > 5:
                    all_text += f"\n\n# {line.title()}\n\n"
                elif re.match(r'^(Chapitre|[0-9]+\.|[0-9]+\s)', line, re.I):
                    all_text += f"\n\n## {line.strip()}\n\n"
                else:
                    all_text += line + "\n"
            # Ajouter les tableaux extraits
            if tables_md:
                all_text += tables_md
        # Nettoyage final
        all_text = re.sub(r'\n{3,}', '\n\n', all_text)
        with open(output_md, 'w', encoding='utf-8') as f:
            f.write(all_text)

def main():
    extract_and_format_markdown("Chapitre1.pdf", "Chapitre1.md")
    print("Le contenu structuré du Chapitre 1 a été enregistré dans Chapitre1.md")
    extract_and_format_markdown("Chapitre2.pdf", "Chapitre2.md")
    print("Le contenu structuré du Chapitre 2 a été enregistré dans Chapitre2.md")

if __name__ == "__main__":
    main() 