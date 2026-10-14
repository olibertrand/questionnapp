# highlight.js 11.9.0 (coloration syntaxique)

Copie locale de [highlight.js](https://highlightjs.org/), licence BSD-3-Clause (fichier `LICENSE`),
pour que le navigateur des élèves ne contacte **aucun serveur extérieur** (RGPD : l'adresse IP
n'est pas transmise à un tiers ; sécurité : le script exécuté est celui du dépôt, pas un fichier
distant qui pourrait être modifié).

Provenance : paquet npm `@highlightjs/cdn-assets@11.9.0`
(sha1 `dda036f8a039d2e7ea9a3cc7e6c347116965e58f`), fichiers copiés sans modification :
`highlight.min.js`, `styles/github.min.css`, `styles/github-dark.min.css`, `LICENSE`.

Mise à jour : `npm pack @highlightjs/cdn-assets@<version>`, extraire l'archive et recopier ces
quatre fichiers, puis modifier la version dans `web/index.html` et dans ce fichier.

L'appli fonctionne sans ces fichiers : le code s'affiche alors sans couleurs.
