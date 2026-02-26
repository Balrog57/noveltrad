# Remplacement de texte

Utilisez [\#menus.edit](#menus.edit)[\#menus.edit.search.and.replace](#menus.edit.search.and.replace) pour ouvrir une nouvelle fenêtre de remplacement de texte et saisissez le mot ou la phrase que vous souhaitez consulter dans le champ de recherche.

Vous pouvez également sélectionner un mot ou une phrase dans le volet [\#panes.editor](#panes.editor), [\#panes.fuzzy.matches](#panes.fuzzy.matches) ou [\#panes.glossary](#panes.glossary) et utiliser [\#menus.edit](#menus.edit)[\#menus.edit.search.and.replace](#menus.edit.search.and.replace). La sélection sera automatiquement entrée dans le champ de recherche.

Vous pouvez ouvrir plusieurs fenêtres de remplacement de texte en même temps.

Cliquez sur les flèches du menu déroulant des champs Rechercher : ou Remplacer par : pour accéder aux dix dernières saisies.

Saisissez la chaine de caractères que vous souhaitez insérer pour remplacer votre terme de recherche dans le champ Remplacer par : et cliquez sur Recherche, ou appuyez sur Entrée si le curseur se trouve toujours dans le champ.

Les résultats de la recherche sont affichés en caractères bleus gras et les chaines modifiées sont affichées en orange pour indiquer le résultat du remplacement.

    多和田葉子.UTF8
    -- 148> | language = [[日本語]]・[[ドイツ語]]
    <- | language = [[Japonais]]・[[Alllemand]]
    -> | language = [[Japonais]]・[[Allemand]]
    ---------

Ici, aucun remplacement n’a encore été effectué.

Cliquez sur l’une des options suivantes :

-   Remplacer tout : remplace chaque occurrence (après l’affichage d’une fenêtre de confirmation indiquant le nombre d’occurrences).

-   Remplacer filtre les entrées dans l’éditeur et surligne les parties qui seront remplacées.

    Cliquez sur le bouton Remplacer suivant ou Ignorer, puis cliquez sur le bouton Terminer pour finir l’opération de remplacement.

<!-- -->

-   Fermer : fermer la fenêtre sans apporter de modifications.

La fenêtre de remplacement de texte dispose de ses propres menus :

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

Les caractères génériques `*` et `?` peuvent être utilisés dans les recherches exactes :

-   Le caractère « \*  » correspond à zéro ou plusieurs caractères, partant de sa position actuelle jusqu’à la fin du mot. Le terme recherché `« jour* »`, par exemple, correspond à `« jour »`, `«jours »` et `«journée »`.

-   « ? » correspond à n’importe quel caractère unique. Par exemple, `« feu? »` correspond au mot `« feux »`, mais aussi à la partie `« feuille »` des mots `« feuilleton »` ou `« feuilleter »`.

Expressions régulières  
Considérez la chaine de caractères recherchée comme une expression régulière.

Les expressions régulières sont un moyen très efficace de rechercher des motifs généraux ou complexes plutôt que des chaines de caractères exactes. Voir l’annexe [\#app.regex](#app.regex) pour en savoir plus.

La chaine de caractères de remplacement prend en charge les références aux groupes définis dans la chaine de caractères de recherche. Utilisez `$n` (où `n` est un chiffre de 1 à 9) dans le champ de remplacement pour faire référence au `nième` groupe dans le champ de recherche.

## Options

Respecter la casse  
Seuls les résultats dont la casse est identique à celle des termes de la recherche sont affichés.

L’espace comprend l’espace insécable  
Les caractères d’espacement correspondent aux espaces normaux et aux espaces insécables (\u00A).

Non traduits  
Recherche également dans les segments non traduits.

Afficher les options avancées  
Permet de choisir des critères supplémentaires tels que la personne qui a écrit ou modifié la traduction, la date et l’heure de la traduction (modification), ou si les segments orphelins doivent être exclus.

Ignorer la différence entre pleine et demi-largeur de caractère  
Affiche les résultats qui correspondent à la fois aux formes pleine et demi-largeur (caractères CJC) des caractères dans les termes recherchés.

Utiliser le bouton Masquer les options avancées pour cacher les options avancées.

## Affichage des résultats

Les correspondances sont affichées dans l’ordre de leur apparition dans le projet. Pour les segments traduits, le texte original est affiché au-dessus du texte traduit. Seul le texte source est affiché pour les segments non traduits.

Double-cliquer sur un segment pour l’ouvrir dans le volet [\#panes.editor](#panes.editor).

Vous pouvez utiliser les raccourcis suivants dans les résultats de la recherche :

<span class="keycombo">C+N</span>  
Passer au segment suivant

<span class="keycombo">C+P</span>  
Retourner au segment précédent

<span class="keycombo">C+J</span>  
Atteindre le segment actuel dans l’éditeur.

Le segment choisi est surligné en vert.

Synchronisation automatique avec l’éditeur  
Le volet [\#panes.editor](#panes.editor) synchronise son affichage avec la sélection dans les résultats de recherche.

Revenir au segment initial à la fermeture de la fenêtre  
Lors de la fermeture de la fenêtre de recherche textuelle, le volet [\#panes.editor](#panes.editor) retourne automatiquement au segment affiché avant le début de la recherche.
