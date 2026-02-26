# Édition

Ce menu vous permet d’accéder aux commandes d’édition de segments.

Sur Windows et Linux : <span class="keycombo">Ctrl+Z</span>

Sur macOS : <span class="keycombo">commande+Z</span>

**Dans ce manuel :** <span class="keycombo">C+Z</span>

Annuler <span class="keycombo">C+Z</span>  
Annule une modification apportée au segment actuel. L’historique des modifications est perdu lorsque l’on quitte le segment.

Rétablir <span class="keycombo">C+Y</span>  
Rétablit une modification du segment actuel qui a été annulée. L’historique des modifications est perdu lorsque l’on quitte le segment.

Remplacer par la correspondance ou la sélection <span class="keycombo">C+R</span>  
Remplace le segment cible par la correspondance partielle sélectionnée (la première correspondance par défaut) ou par le texte sélectionné dans le volet [\#panes.fuzzy.matches](#panes.fuzzy.matches).

Le texte sélectionné a la priorité sur la correspondance sélectionnée.

Voir la description du volet [\#panes.fuzzy.matches](#panes.fuzzy.matches) pour en savoir plus.

Insérer la correspondance ou la sélection<span class="keycombo">C+I</span>  
Insère la correspondance partielle sélectionnée ou le texte sélectionné dans le volet [\#panes.fuzzy.matches](#panes.fuzzy.matches) à l’emplacement où se trouve le curseur. Si une partie du segment cible est sélectionnée, cette partie sera remplacée.

Le texte sélectionné à la priorité sur la correspondance sélectionnée.

Voir la description du volet [\#panes.fuzzy.matches](#panes.fuzzy.matches) pour en savoir plus.

Remplacer par la source <span class="keycombo">C+Maj+R</span>  
Remplace l’ensemble du segment cible par le segment source.

Insérer le texte source <span class="keycombo">C+Maj+I</span>  
Insère le segment source à l’emplacement où se trouve le curseur. Si une partie du segment cible est sélectionnée, cette partie sera remplacée.

Sélectionner le texte source <span class="keycombo">C+Maj+A</span>  
Sélectionne le texte source.

La sélection peut être utilisée directement dans OmegaT pour des [recherches internes](#windows.text.search), pour effectuer des [remplacements](#windows.text.replace), pour [entrer des termes de glossaires](#menus.edit.create.glossary.entry), pour des [recherches externes](#dialogs.preferences.external.searches), etc. Une fois la sélection copiée dans le presse-papier de votre système d’exploitation, elle peut aussi être utilisée dans des recherches internet ou ailleurs.

Remplacer par une traduction automatique <span class="keycombo">C+M</span>  
Remplace le segment cible par une traduction automatique fournie par le service de traduction automatique que vous avez choisi.

Si la préférence [\#dialogs.preferences.mt.automatically.fetch.translations](#dialogs.preferences.mt.automatically.fetch.translations) est désactivée, utilisez cette option une fois pour récupérer la traduction, et une seconde fois pour l’insérer.

Rien ne se passe si aucun service de traduction automatique n’a été activé dans le menu [\#menus.options](#menus.options)[\#menus.options.mt](#menus.options.mt). Voir les préférences [\#dialogs.preferences.mt](#dialogs.preferences.mt) pour en savoir plus.

Insérer les balises manquantes <span class="keycombo">C+Maj+T</span>  
Insère les balises sources manquantes à l’emplacement où se trouve le curseur.

Insérer la prochaine balise manquante <span class="keycombo">C+T</span>  
Insère la prochaine balise manquante à l’emplacement où se trouve le curseur.

Exporter la sélection <span class="keycombo">C+Maj+C</span>  
Exporte la sélection en cours vers un fichier texte pour la traiter. Si aucun texte n’a été sélectionné, c’est le segment source en cours qui sera envoyé vers ce fichier. Pour rester cohérent avec le comportement habituel du presse-papier, ce fichier n’est pas vidé lorsque vous quittez OmegaT. Le contenu exporté est copié dans le fichier [\#configuration.folder.default.contents.script.selection.title](#configuration.folder.default.contents.script.selection.title) situé dans le dossier [configuration](#configuration.folder).

Créer une entrée de glossaire… <span class="keycombo">C+Maj+G</span>  
Permet de créer une entrée dans le glossaire modifiable du projet (le fichier [\#project.folder.glossary.txt](#project.folder.glossary.txt)).

Il existe deux manières d’utiliser cette fonction.

-   La première consiste à ouvrir la boite de dialogue et ensuite manuellement remplir les différents champs.

-   La seconde consiste à sélectionner les termes dans un des volets d’OmegaT et ensuite lancer la boite de dialogue après chaque sélection pour qu’OmegaT les entre automatiquement dans les différents champs :

    1.  Sélectionnez une chaine de texte dans n’importe quel volet

    2.  Appuyez sur <span class="keycombo">C+Maj+G</span>

        La sélection est insérée dans le champ Terme source.

    3.  Sélectionnez une chaine de texte dans n’importe quel volet

    4.  Appuyez sur <span class="keycombo">C+Maj+G</span>

        La sélection est insérée dans le champ Terme cible.

    5.  \[Facultatif\] Sélectionnez une chaine de texte dans n’importe quel volet

    6.  \[Facultatif\] Appuyez sur <span class="keycombo">C+Maj+G</span>

        La sélection est insérée dans le champ Commentaire.

    7.  Appuyez sur la touche Entrée ou cliquez sur OK

Rechercher… <span class="keycombo">C+F</span>  
Ouvre une nouvelle fenêtre de [\#windows.text.search](#windows.text.search).

Si vous sélectionnez une chaine de texte (dans n’importe quel volet) avant d’ouvrir la fenêtre, le texte sera inséré par défaut dans le champ Rechercher :.

La combinaison de touches <span class="keycombo">C+Maj+F</span> réutilise la fenêtre de recherche la plus récente encore ouverte au lieu d’en ouvrir une nouvelle.

Remplacer… <span class="keycombo">C+K</span>  
Ouvre une nouvelle fenêtre de [\#windows.text.replace](#windows.text.replace).

Si vous sélectionnez une chaine de texte (dans n’importe quel volet) avant d’ouvrir la fenêtre, le texte sera inséré par défaut dans le champ Rechercher :.

Rechercher dans les dictionnaires <span class="keycombo">A+Maj+D</span>  
Si la préférence [\#dialogs.preferences.dictionary.automatically.search.segment](#dialogs.preferences.dictionary.automatically.search.segment) est désactivée, cette fonction vous permet de rechercher le mot sélectionné ou l’ensemble des termes du segment dans les dictionnaires.

Basculer la casse en  
Change la casse du texte sélectionné dans le segment cible en fonction de l’option sélectionnée, ou fait défiler les options. Si aucun texte n’est sélectionné, OmegaT sélectionne le mot qui commence par le caractère se trouvant immédiatement à la droite du curseur.

-   minuscules

    toutes les lettres en minuscules

-   MAJUSCULES

    TOUTES LES LETTRES EN MAJUSCULES

-   Casse de Titre

    Presque toutes les Lettres en Minuscules

-   Casse de phrase

    Uniquement la première lettre en majuscule.

-   Parcourir <span class="keycombo">Maj+F3</span>

    Sur macOS, la touche <span class="keycombo">F3</span> active le mode **remplacement** dans l’éditeur. Voir [\#panes.editor.overwriting](#panes.editor.overwriting) pour en savoir plus.

Choisir une correspondance  
Sélectionne la correspondance partielle précédente, suivante, ou `n`ième affichée dans la fenêtre des correspondances pour vous permettre d’effectuer un remplacement ou une insertion dans le segment.

-   Choisir la correspondance précédente <span class="keycombo">A+↑</span>

-   Choisir la correspondance suivante <span class="keycombo">A+↓</span>

-   Choisir la correspondance \#1 <span class="keycombo">C+1</span>

-   Choisir la correspondance \#2 <span class="keycombo">C+2</span>

-   Choisir la correspondance \#3 <span class="keycombo">C+3</span>

-   Choisir la correspondance \#4 <span class="keycombo">C+4</span>

-   Choisir la correspondance \#5 <span class="keycombo">C+5</span>

Insérer un caractère de contrôle Unicode  
Insère le caractère de contrôle directionnel Unicode sélectionné. Voir [Algorithme bidirectionnel Unicode](https://www.unicode.org/reports/tr9/#Directional_Formatting_Characters) pour en savoir plus.

-   Marque de gauche à droite (LRM U+200E)

-   Marque de droite à gauche (RLM U+200F)

-   Début de l’imbrication de gauche à droite (LRE U+202A)

-   Début de l’imbrication de droite à gauche (RLE U+202B)

-   Fin de formatage directionnel (PDF U+202C)

Utilisez [\#menus.view](#menus.view)[\#menus.view.mark.bidirectional.algorithm.control.character](#menus.view.mark.bidirectional.algorithm.control.character) pour afficher les caractères afin de faciliter la manipulation. Voir [\#app.bidi](#app.bidi) pour en savoir plus.

Utiliser comme traduction par défaut  
S’il existe plusieurs traductions possibles pour le segment actuel, vous pouvez définir la traduction choisie comme étant la traduction par défaut. S’il n’y a qu’une traduction possible, l’entrée sera grisée.

Créer une traduction alternative  
Deux segments parfaitement identiques peuvent, en fonction du contexte, avoir deux traductions différentes. Si la traduction actuelle ne convient pas, sélectionnez cet élément de menu et entrez la traduction alternative.

Pour faire la différence entre des segments identiques, OmegaT utilise soit un identificateur interne fourni par le type de fichier, soit les segments précédents et suivants. Dans ce cas, une traduction alternative nécessite que des segments identiques aient des segments précédents et suivants différents. Si des segments identiques ont également des segments précédents et suivants identiques, il ne vous sera pas possible de les traduire différemment et de faire de l'un d'entre eux une traduction alternative dans OmegaT.

Pour éviter ce problème, vous pouvez introduire une petite modification dans le segment qui précède ou dans celui qui suit, dans le fichier source, pour établir une distinction entre les différentes répétitions d'un ensemble de segments précédents et suivants.

Supprimer la traduction <span class="keycombo">C+Maj+X</span>  
Supprime la traduction actuelle et définit le segment comme non traduit.

Enregistrer une traduction vide  
Définit la traduction comme vide. Le document cible ne contiendra rien pour ce segment, tandis que l’Éditeur le marquera avec l’identifiant `<VIDE>`.

Enregistrer une traduction identique à la source <span class="keycombo">C+Maj+S</span>  
Utilisez cette option pour enregistrer une traduction identique à la source, même si la préférence [\#dialogs.preferences.editor.allow.translation.to.be.equal.to.source](#dialogs.preferences.editor.allow.translation.to.be.equal.to.source) n’est pas activée.
