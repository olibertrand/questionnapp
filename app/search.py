"""Recherche par mots-clés dans les questions (base de l'appli et fichiers de banque/).

Une recherche est une suite de mots séparés par des espaces : une question correspond si elle
contient **tous** les mots (dans le titre, l'identifiant, le chapitre, les compétences, l'énoncé,
les intitulés des champs, la correction, les indices, ou les textes du générateur : variantes
tirées au hasard comme les noms de méthodes « taille », « somme »…). Un mot précédé de « - » exclut les
questions qui le contiennent ; « des mots entre guillemets » cherchent l'expression exacte.
Majuscules, accents et tirets bas ne comptent pas (« chainee » trouve « chaînée »,
« min liste » trouve « min_liste ») ; un mot peut être le début ou un morceau d'un mot
plus long (« min » trouve « minimum »).
"""

import ast
import re
import unicodedata

_QUOTED = re.compile(r'(-?)"([^"]*)"|(\S+)')


def normalize(text):
    """Minuscules, sans accents ; les tirets bas et la ponctuation deviennent des espaces."""
    text = unicodedata.normalize("NFKD", str(text or "")).casefold()
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[\W_]+", " ", text).split())


def parse(query):
    """(mots à trouver, mots à exclure), déjà normalisés."""
    include, exclude = [], []
    for m in _QUOTED.finditer(query or ""):
        if m.group(3) is not None:
            word, neg = m.group(3), m.group(3).startswith("-") and len(m.group(3)) > 1
            word = word[1:] if neg else word
        else:
            word, neg = m.group(2), m.group(1) == "-"
        word = normalize(word)
        if word:
            (exclude if neg else include).append(word)
    return include, exclude


def matches(text, query):
    include, exclude = parse(query)
    norm = " " + normalize(text) + " "
    return all(w in norm for w in include) and not any(w in norm for w in exclude)


def template_text(template):
    """Le texte d'un modèle qui sert à la recherche (avec les chaînes du générateur, pas son code)."""
    if not isinstance(template, dict):
        return ""
    parts = [template.get("statement", ""), template.get("solution", "")]
    parts += [h for h in template.get("hints") or [] if isinstance(h, str)]
    parts += [f.get("label", "") for f in template.get("fields") or [] if isinstance(f, dict)]
    parts += _strings(template.get("code"))
    return "\n".join(p for p in parts if isinstance(p, str))


def _strings(code):
    """Les chaînes écrites dans le code du générateur (variantes de l'énoncé), sans le reste du code."""
    try:
        tree = ast.parse(code or "")
    except (SyntaxError, ValueError):
        return []
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def question_text(uid, title, chapter, skills, template, sample=None):
    parts = [uid or "", title or "", chapter or "", " ".join(skills or []), template_text(template)]
    if isinstance(sample, dict):
        parts.append(sample.get("statement", ""))
    return "\n".join(parts)
