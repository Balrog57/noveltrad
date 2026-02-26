# Recherche textuelle

Utilisez [\#menus.edit](#menus.edit)[\#menus.edit.search.project](#menus.edit.search.project) pour ouvrir une nouvelle fenêtre de recherche textuelle et entrez le mot ou la phrase que vous souhaitez rechercher dans le champ de recherche.

Plusieurs fenêtres de recherche peuvent être ouvertes en même temps. Appuyer sur <span class="keycombo">C+Maj+F</span> pour réutiliser la fenêtre de recherche la plus récente.

Vous pouvez également sélectionner un mot ou une phrase dans le volet [\#panes.editor](#panes.editor), [\#panes.fuzzy.matches](#panes.fuzzy.matches) ou [\#panes.glossary](#panes.glossary) et utiliser [\#menus.edit](#menus.edit)[\#menus.edit.search.project](#menus.edit.search.project). La sélection sera automatiquement entrée dans le champ de recherche.

Cliquer sur la flèche déroulante du champ Rechercher : pour accéder aux dix dernières recherches.

Cliquer sur Rechercher ou appuyer sur la touche Entrée lorsque le champ de recherche est sélectionné pour commencer la recherche.

Les correspondances seront affichées en bleu et en gras.

    -- 148> | language = [[日本語]]・[[ドイツ語]]
    ---------
    -- 177> [[2001年]]、ドイツの永住権を取得。
    ---------

La fenêtre de recherche dispose de ses propres menus :

-   Fichier &gt; Rechercher la sélection (<span class="keycombo">C+F</span>) : la sélection actuelle est insérée dans le champ de recherche.

-   Fichier &gt; Fermer (<span class="keycombo">C+W</span>) : ferme la fenêtre de recherche.

-   Édition &gt; Insérer le texte source (<span class="keycombo">C+Maj+I</span>) : insère le contenu du segment source actuel.

-   Édition &gt; Remplacer par la source (<span class="keycombo">C+Maj+R</span>) : remplace le contenu du champ de recherche par celui du segment source actuel.

-   Édition &gt; Créer une entrée de glossaire (<span class="keycombo">C+Maj+G</span>) : ajoute un nouvel élément de glossaire Voir [\#menus.edit](#menus.edit)[\#menus.edit.create.glossary.entry](#menus.edit.create.glossary.entry) pour en savoir plus.

-   Édition &gt; Réinitialiser les options : réinitialise les options de la fenêtre de recherche textuelle.

## Type de recherche

Utiliser les boutons radio pour sélectionner le type de recherche.

Les types de recherches suivants sont disponibles :

Recherche exacte  
Recherche la chaine de caractères telle qu’elle a été saisie dans le champ de recherche.

Il s’agit de l’équivalent d’une recherche web entre guillemets.

Recherche par mot-clé  
Recherche des segments contenant chacun des termes de recherche séparés par une espace.

Il s’agit de l’équivalent d’une recherche web sans guillemets.

Les caractères `*` et `?` peuvent être utilisés dans les recherches exactes et par mots-clés.

-   Le caractère `*` correspond à zéro ou plusieurs caractères, partant de la position actuelle jusqu’à la fin du mot.

    Par exemple, rechercher le terme `run*` va correspondre aux mots `run`, `runs` et `running`.

<!-- -->

-   Le caractère `?` correspond à n’importe quel caractère unique.

    Par exemple, `run?` correspond au mot `runs`, mais aussi à la partie `runn` des mots `running` ou `runner`.

<!-- -->

Expressions régulières  
Considérez la chaine de caractères recherchée comme une expression régulière.

Les expressions régulières sont un moyen très efficace de rechercher des motifs généraux ou complexes plutôt que des chaines de caractères exactes. Voir l’annexe [\#app.regex](#app.regex) pour en savoir plus.

Les caractères `*` et `?` ont une signification particulière dans les expressions régulières. Par conséquent, les recherches avec les caractères génériques décrits ci-dessus ne s’appliquent qu’aux recherches exactes et par mots-clés.

## Options

Respecter la casse  
Seuls les résultats dont la casse est identique à celle des termes de la recherche sont affichés.

L’espace comprend l’espace insécable  
Les caractères d’espacement correspondent aux espaces normaux et aux espaces insécables (\u00A).

Source  
Recherche dans les segments source.

Traduction  
Recherche dans les segments cible.

Notes  
Recherche dans les notes attachées aux segments.

Commentaires  
Recherche dans les commentaires attachés aux segments.

Traduits ou pas  
Recherche à la fois dans les segments traduits et non traduits.

Traduits  
Recherche seulement dans les segments traduits.

Non traduits  
Recherche seulement dans les segments non traduits.

Afficher : tous les segments correspondants  
Chaque segment est affiché individuellement, même s’il s’agit d’une répétition trouvée dans le même document ou dans un document différent dans le projet.

Afficher : noms des fichiers  
Le nom du fichier dans lequel se trouve le segment est affiché au-dessus de chaque résultat.

Rechercher dans : le projet  
Recherche dans les différentes ressources bilingues du projet.

Sélectionner l’étendue de la recherche :

la mémoire  
La mémoire du projet ([\#project.folder.project.save.tmx](#project.folder.project.save.tmx)) est incluse.

les MT  
Les mémoires de traductions situées dans le dossier [\#project.folder.tm](#project.folder.tm) sont incluses.

Glossaires  
Les glossaires situés dans le dossier [\#project.folder.glossary](#project.folder.glossary) sont inclus.

Rechercher dans : les fichiers  
Recherche dans les fichiers de références qui ne sont pas inclus dans les ressources du projet.

OmegaT peut mener des recherches dans n’importe quel fichier qu’il peut lire en tant que fichier source. Voir le chapitre [\#file.filters](#file.filters) pour en savoir plus.

Les fichiers TMX sont exclus des recherches de fichiers, car OmegaT ne les reconnait pas en tant que format de fichier source malgré le fait qu’ils soient pris en charge en tant que mémoires de traduction.

Options de recherche MT  
Permet de choisir des critères supplémentaires tels que la personne qui a écrit ou modifié la traduction, la date et l’heure de la traduction (modification), ou si les segments orphelins doivent être exclus.

Les options de recherche MT ne s’appliquent qu’à la mémoire principale et non aux mémoires de référence.

Ignorer la différence entre pleine et demi-largeur de caractère  
Affiche les résultats qui correspondent à la fois aux formes pleine et demi-largeur (caractères CJC) des caractères dans les termes recherchés.

Nombre de segments correspondants :  
Définit le nombre maximum de correspondances affichées dans le champ de résultats de recherche.

Utiliser le bouton Masquer les options avancées pour cacher les options avancées.

## Affichage des résultats

Les correspondances sont affichées dans l’ordre de leur apparition dans le projet. Pour les segments traduits, le texte original est affiché au-dessus du texte traduit. Seul le texte source est affiché pour les segments non traduits.

Double-cliquer sur un segment pour l’ouvrir dans le volet [\#panes.editor](#panes.editor).

Vous pouvez aussi utiliser les raccourcis suivants dans les résultats de recherche :

<span class="keycombo">C+N</span>  
Passer au segment suivant

<span class="keycombo">C+P</span>  
Retourner au segment précédent

<span class="keycombo">C+J</span>  
Atteindre le segment actuel dans l’éditeur.

Le segment sélectionné est surligné en vert :

    -- 148> | language = [[日本語]]・[[ドイツ語]]
    ---------
    -- 177> [[2001年]]、ドイツの永住権を取得。
    ---------

Synchronisation automatique avec l’éditeur  
Le volet [\#panes.editor](#panes.editor) synchronise son affichage avec la sélection dans les résultats de recherche.

Revenir au segment initial à la fermeture de la fenêtre  
Lors de la fermeture de la fenêtre de recherche textuelle, le volet [\#panes.editor](#panes.editor) retourne automatiquement au segment affiché avant le début de la recherche.

## Filtre

Cliquer sur le bouton Filtre pour n’afficher que les segments correspondants aux résultats de la recherche dans le volet [\#panes.editor](#panes.editor). Pour supprimer le filtre, cliquer sur le bouton Supprimer le filtre en haut du volet [\#panes.editor](#panes.editor) ou recharger le projet.
