# Volets

## Présentation par défaut

Lorsque vous lancez OmegaT pour la première fois, la fenêtre principale affiche par défaut la présentation suivante :

<figure id="default.omegat.layout">
<img src="images/defaultOmegaTLayout.png" />
<figcaption>Présentation par défaut d’OmegaT sur macOS</figcaption>
</figure>

1.  Le volet [\#panes.editor](#panes.editor)

2.  Le volet [\#panes.notes](#panes.notes)

3.  Le volet [\#panes.fuzzy.matches](#panes.fuzzy.matches)

4.  Le volet [\#panes.glossary](#panes.glossary)

5.  Le volet [\#panes.segment.properties](#panes.segment.properties)

6.  Le volet [\#panes.comments](#panes.comments)

7.  Le volet [\#panes.multipletranslations](#panes.multipletranslations)

8.  Les volets [\#panes.dictionary](#panes.dictionary) et [\#panes.machinetranslation](#panes.machinetranslation) sont ancrés

9.  La [\#panes.statusbar](#panes.statusbar) (à droite), contenant des informations sur le projet

Utilisez les différentes options du menu [\#menus.view](#menus.view) et déplacez les différents [volets](#chapter.panes) pour obtenir la présentation qui vous convient le mieux.

Utiliser [\#menus.view](#menus.view)[\#menus.view.restore.main.window](#menus.view.restore.main.window) si vous rencontrez des problèmes lors de la réorganisation de la disposition des fenêtres.

## Les principes

Manipulation  
La fenêtre principale est composée de différents volets décrits ici, différents menus décrits dans le chapitre [\#chapter.menus](#chapter.menus), et une barre d’état décrite [plus bas](#panes.statusbar). Vous pouvez cliquer et maintenir le nom d’un volet pour le faire glisser vers une nouvelle position, ou même le détacher en tant que fenêtre distincte.

Le coin supérieur droit de chaque volet affiche différentes icônes en fonction du type de volet et de son état actuel :

<table>
<caption>Éléments graphiques des volets</caption>
<tbody>
<tr class="odd">
<td><img src="images/Settings.png" style="width:60.0%" /></td>
<td>Liste les différentes <strong>actions</strong> supplémentaires disponibles dans le volet.</td>
</tr>
<tr class="even">
<td><img src="images/Minimize.png" style="width:60.0%" /></td>
<td><strong>Réduit</strong> le volet dans un onglet en bas de la fenêtre.</td>
</tr>
<tr class="odd">
<td><img src="images/Maximize.png" style="width:60.0%" /></td>
<td><strong>Agrandit</strong> le volet</td>
</tr>
<tr class="even">
<td><img src="images/Restore.png" style="width:60.0%" /></td>
<td><strong>Rétablit</strong> la taille d’un volet agrandi à sa disposition précédente.</td>
</tr>
<tr class="odd">
<td><img src="images/Undock.png" style="width:60.0%" /></td>
<td><strong>Détache</strong> le volet de la fenêtre principale.</td>
</tr>
<tr class="even">
<td><img src="images/Dock.png" style="width:60.0%" /></td>
<td><strong>Rattache</strong> le volet à la fenêtre principale.</td>
</tr>
</tbody>
</table>

Éléments graphiques des volets

Vous pouvez regrouper des volets dans la même zone de la fenêtre. Les volets se présenteront alors sous la même zone, mais sous des onglets différents portant le nom du volet. Les volets peuvent être redimensionnés en faisant glisser les séparateurs entre eux.

Utiliser [\#menus.view](#menus.view)[\#menus.view.restore.main.window](#menus.view.restore.main.window) pour rétablir la présentation par défaut si vous perdez notion des modifications apportées à l’interface graphique et que vous ne pouvez plus voir certains volets.

Menus contextuels  
Certains volets disposent d’un menu contextuel. Vous pouvez appeler ce menu en utilisant la méthode standard de votre système d’exploitation ou les raccourcis définis par OmegaT :

-   Sous Windows et Linux : Menu

-   Sous macOS : <span class="keycombo"> +S+ +Esc+ </span>.

Glisser-déplacer  
Les fichiers peuvent être glissés et déposés sur certains volets, avec les résultats suivants :

Volet Éditeur  
En déposant un fichier de projet OmegaT (`omegat.project`) ou un projet complet ici, on ouvre le projet correspondant après avoir fermé le projet actuellement ouvert, le cas échéant.

Le dépôt d’autres fichiers les copiera dans le dossier `source`. Ceci s’applique également à la fenêtre [\#windows.source.files.list](#windows.source.files.list).

Volet Correspondances    
Les fichiers `.tmx` déposés ici sont copiés dans le dossier `tm`.

Volet Glossaires  
Les fichiers déposés ici avec une extension de glossaire reconnue (`.txt`, `.tab`, etc.) sont copiés dans le dossier `glossary`.

Notifications  
Si un volet est fermé, mais que son contenu doit être affiché, OmegaT peut temporairement surligner l’onglet du volet en orange lorsque vous entrez dans le segment.

Les notifications sont activées par défaut dans les volets Commentaires et Bloc-note.

Pour activer ou désactiver les notifications,

-   Entrez dans le volet

-   Cliquez sur le widget Actions et paramètres en haut à droite.

-   Sélectionnez M’avertir lorsqu’un segment comporte des… (où … varie en fonction du volet pour lequel vous activez les notifications).

Les volets suivants peuvent envoyer des notifications :

-   Commentaires

-   Dictionnaires

-   Correspondances

-   Glossaires

-   Traductions multiples

-   Bloc-note

-   Propriétés du segment

    Le volet Propriétés du segment permet de définir les paramètres de notification pour chacun de ses éléments.

    Dans Affichage tabulaire, faites un clic droit sur l’élément et sélectionnez M’avertir lorsq’un segment comporte… (où … varie en fonction de la notification choisie).

    Dans Affichage liste, faites un clic droit sur le widget Actions et paramètres à droite de la ligne de propriété choisie et sélectionnez M’avertir lorsqu’un segment comporte… (où … varie en fonction de la notification choisie).

## Éditeur

C’est ici que vous saisissez et éditez vos traductions.

Le texte est divisé en segments numérotés. Vous pouvez faire défiler le document et double-cliquer sur n’importe quel segment pour l’ouvrir et le modifier.

    — ¶ —————————————————————

    Hide Tags
    |Dissimuler les balises<segment 2148 ¶>

    — ¶ —————————————————————

    Lorsque cette option est activée, toutes les mises en forme des segments source sont dissimulées.

-   La première ligne, en caractères gras sur fond vert, est le texte source à traduire.

-   Le **champ de traduction** est la deuxième ligne, entre le bord gauche et le marqueur de segment à droite. Le **champ de traduction** est l’endroit où vous saisissez votre traduction.

-   Le marqueur de segment est ici `<segment 2148 ¶>`.

    `2148` est le numéro du segment dans le projet et le symbole `¶` indique que le segment est le premier segment d’un paragraphe.

-   Le curseur est verrouillé par défaut dans le champ de traduction.

    Utilisez F2 pour le déverrouiller et le déplacer librement entre le champ de traduction et d’autres parties du volet.

-   La ligne située sous le champ de traduction est un segment différent.

-   Utilisez [\#menus.goto](#menus.goto)[\#menus.goto.next.untranslated.segment](#menus.goto.next.untranslated.segment) ou d’autres commandes de navigation pour :

    -   enregistrer le contenu du champ de traduction dans la mémoire de traduction du projet, et

    -   entrer dans le segment suivant à traduire.

    Voir le menu [\#menus.goto](#menus.goto) pour plus de détails.

Modifier l’affichage de l’éditeur pour l’adapter à votre flux de travail.

Les modifications peuvent inclure :

-   Changer la police de caractères comme décrit dans les préférences [\#dialogs.preferences.fonts](#dialogs.preferences.fonts).

-   Afficher ou dissimuler les délimitations de paragraphe en utilisant [\#menus.view](#menus.view)[\#menus.view.mark.paragraph.delimitations](#menus.view.mark.paragraph.delimitations).

-   Modifier le format de délimitation des paragraphes, défini dans la préférence [\#dialogs.preferences.editor.paragraph.delimitation.format](#dialogs.preferences.editor.paragraph.delimitation.format).

-   Afficher des informations sur la modification des segments à l’aide de [\#menus.view](#menus.view)[\#menus.view.modification.info](#menus.view.modification.info).

-   Afficher ou dissimuler des segments source à l’aide de [\#menus.view](#menus.view)[\#menus.view.display.source.segments](#menus.view.display.source.segments).

-   Mettre en évidence des segments traduits à l’aide de [\#menus.view](#menus.view)[\#menus.view.mark.translated.segments](#menus.view.mark.translated.segments).

-   Insérer automatique du texte source dans le champ de traduction en désactivant la préférence [\#dialogs.preferences.editor.leave.the.segment.empty](#dialogs.preferences.editor.leave.the.segment.empty).

-   Insérer la meilleure correspondance au-delà du seuil défini dans la préférence [\#dialogs.preferences.editor.insert.the.best.fuzzy.match](#dialogs.preferences.editor.insert.the.best.fuzzy.match).

-   Définir le texte que vous souhaitez exclure de la traduction, activé dans la préférence [\#dialogs.preferences.tag.processing.regular.expressions.for.fragments.that.should.be.removed.from.translation](#dialogs.preferences.tag.processing.regular.expressions.for.fragments.that.should.be.removed.from.translation).

Voir les préférences [\#dialogs.preferences.editor](#dialogs.preferences.editor) et le menu [\#menus.view](#menus.view) pour en savoir plus.

Traductions vides  
Si vous laissez le champ de traduction vide, OmegaT traitera le segment comme non traduit et le conservera dans la langue d’origine lors de la création des documents traduits.

Traductions équivalentes à la source  
OmegaT peut enregistrer des traductions identiques au texte source. Cela peut s’avérer utile pour les documents contenant des marques, des noms ou d’autres noms propres, ou des sections dans une troisième langue qui ne nécessitent pas de traduction.

Déplacer du texte  
Il est possible de déplacer un texte depuis n’importe quel endroit de la fenêtre principale et de le déposer dans le champ de traduction. Le texte glissé depuis l’extérieur du champ de traduction est copié, tandis que le texte glissé depuis l’intérieur du champ de traduction est déplacé.

Remplacement  
Par défaut, la saisie de texte insère le nouveau texte après le curseur dans le sens de la saisie. Pour remplacer le texte existant, utilisez les touches suivantes :

-   Sous Windows et Linux : <span class="keycombo"> +INSERT+ </span>

-   Sous macOS : F3

Le mode d’écriture (écraser - ECR ou insérer - INS) est indiqué à droite de la [barre d’état](#panes.statusbar). La même touche permet de passer d’un mode à l’autre.

Verrouillage du curseur  
Par défaut, le curseur est verrouillé dans le champ de traduction et les touches fléchées ne peuvent pas être utilisées pour se déplacer dans le texte source.

En appuyant sur F2, le curseur est déverrouillé et il est possible d’utiliser les touches fléchées pour se déplacer dans le texte source (ou n’importe où ailleurs dans l’éditeur). Cela vous permet de sélectionner du texte à l’aide du clavier.

L’état du curseur (verrouillé - VER ou libre - LIB) est indiqué à droite de la [barre d’état](#panes.statusbar). La même touche permet de basculer entre le verrouillage et le déverrouillage du curseur.

Menu contextuel  
Raccourci par défaut :

-   Sous Windows et Linux : Menu

-   Sous macOS : <span class="keycombo">S+Esc</span>

Vous pouvez également faire apparaitre le menu en cliquant avec le bouton droit de la souris (C + clic sur macOS).

Le menu contextuel du volet éditeur offre diverses fonctions disponibles à partir du menu [\#menus.edit](#menus.edit), notamment :

-   Éléments de glossaire appariés, avec des commentaires, le cas échéant présentés sous forme d’infobulle. Utilisez [\#menus.view](#menus.view)[\#menus.view.mark.glossary.matches](#menus.view.mark.glossary.matches) pour activer cette fonction.

-   Fonctions Couper, Copier, Coller,

-   Aller au segment (pour aller au segment sous le curseur).

-   Recherche dans les dictionnaires (pour rechercher le terme sélectionné dans un dictionnaire installé).

-   Ajouter une entrée de glossaire (équivalent à l’utilisation de [\#menus.edit](#menus.edit)[\#menus.edit.create.glossary.entry](#menus.edit.create.glossary.entry)).

Si vous avez sélectionné du texte et des entrées définies dans les préférences [\#dialogs.preferences.external.searches](#dialogs.preferences.external.searches), ils seront également affichés dans ce menu (tout comme les recherches locales).

Menu de saisie automatique  
Raccourci par défaut :

-   Sous Windows et Linux : <span class="keycombo">C+Espace</span>

-   Sous macOS : Esc

Ce menu propose les options de saisie automatique définies dans les préférences [\#dialog.preferences.auto.completion](#dialog.preferences.auto.completion).

Navigation  
Utilisez [\#menus.goto](#menus.goto)[\#menus.goto.notes.pane](#menus.goto.notes.pane) pour entrer dans le volet et ajouter ou modifier une note.

Utilisez [\#menus.goto](#menus.goto)[\#menus.goto.editor.pane](#menus.goto.editor.pane) pour revenir à l’éditeur.

## Correspondances

La fenêtre de correspondances affiche les segments de vos mémoires de traduction qui sont les plus similaires au segment que vous êtes en train de traduire.

Les correspondances proviennent à la fois de la mémoire de traduction interne du projet, créée en temps réel au fur et à mesure que vous traduisez le projet, et des mémoires externes que vous avez importées de projets précédents ou reçues de tiers. Voir le guide pratique [\#how.to.use.tm](#how.to.use.tm) pour en savoir plus.

Lorsque vous saisissez un segment, la première correspondance partielle (celle dont le pourcentage de correspondance est le plus élevé) est automatiquement sélectionnée. Vous pouvez appuyer sur <span class="keycombo">C+2, 3, 4, ou 5+ </span>, ou utiliser [\#menus.edit](#menus.edit)[\#menus.edit.select.match](#menus.edit.select.match), pour sélectionner une autre correspondance.

<table>
<tbody>
<tr class="odd">
<td><table>
<tbody>
<tr class="odd">
<td><pre><code>— ¶ —————————————————————
&#10;Application Folder
|&lt;segment 1879 ¶&gt;
&#10;— ¶ —————————————————————</code></pre></td>
</tr>
</tbody>
</table></td>
<td><table>
<tbody>
<tr class="odd">
<td><pre><code>1. Top Folder
Dossier racine
&lt;50/50/66% Orphan segments (+1 more)&gt;</code></pre>
<pre><code>2. Configuration Folder
Dossier de configuration
&lt;50/50/66% &gt;</code></pre></td>
</tr>
</tbody>
</table></td>
</tr>
</tbody>
</table>

La correspondance sélectionnée est mise en évidence en **gras**. Les mots manquants dans le segment que vous traduisez sont affichés en **bleu**, et les parties adjacentes en **vert** (lorsque la partie adjacente est une espace, comme ci-dessus, la partie n’est pas colorée).

La correspondance affiche également trois pourcentages de correspondance.

Ces pourcentages signifient, dans l’ordre, ce qui suit :

-   Pourcentage calculé **avec lemmatisation** basé sur le lemmatiseur de la langue source, et **ignorant les balises et les nombres** (généralement le plus élevé).

-   Pourcentage calculé **sans lemmatisation**, tout en continuant à **ignorer les balises et les nombres** (généralement légèrement inférieur).

-   Pourcentage calculé sur **le texte entier, y compris les balises et les chiffres** (généralement le plus bas).

    Si le segment ne contient que des chiffres ou des symboles, ce pourcentage sera le plus élevé.

Vous pouvez modifier la façon dont les correspondances sont affichées ou triées. Voir le paramètre [\#dialog.preferences.tm.matches](#dialog.preferences.tm.matches) pour en savoir plus.

Utilisez [\#menus.edit](#menus.edit)[\#menus.edit.replace.with.match.or.selection](#menus.edit.replace.with.match.or.selection) pour remplacer le champ de traduction par la correspondance, ou [\#menus.edit](#menus.edit)[\#menus.edit.insert.match.or.selection](#menus.edit.insert.match.or.selection) pour l’insérer à la position du curseur.

## Glossaires

Ce volet affiche les termes de vos fichiers de glossaire qui correspondent aux termes du segment en cours. Les fichiers de glossaire sont situés dans le dossier [\#project.folder.glossary](#project.folder.glossary) du projet.

Le terme source est affiché avant le signe « = » et les termes cibles après. Si la saisie contient des commentaires, ceux-ci sont numérotés et affichés sur des lignes séparées sous les termes. Les termes figurant dans le glossaire modifiable sont affichés en gras, tandis que ceux provenant d’autres glossaires sont présentés sous forme de texte normal.

    Project = Projet
    1. Projet de traduction

    Folder = Dossier

Le nom du fichier du glossaire est affiché sous forme d’infobulle lorsque l’on survole les termes.

Le champ de commentaire d’une entrée peut contenir des hyperliens sur lesquels il est possible de cliquer pour obtenir des références supplémentaires.

Les liens vers des fichiers locaux (`file:///PATH/filename`) s’ouvrent dans le programme associé. Les adresses Web (`https://…`) s’ouvrent dans le navigateur par défaut.

Vous pouvez sélectionner un terme dans le panneau des glossaires et cliquer dessus avec le bouton droit de la souris pour l’insérer dans la traduction.

Utilisez [\#menus.view](#menus.view)[\#menus.view.mark.glossary.matches](#menus.view.mark.glossary.matches) pour souligner les correspondances dans le glossaire.

Vous pouvez ensuite faire un clic droit sur le mot souligné dans le segment source pour ouvrir un menu contextuel répertoriant les traductions disponibles dans vos glossaires. Sélectionnez-en une pour l’insérer à la position actuelle du curseur dans le segment.

Vous pouvez utiliser les préférences du glossaire pour affiner l’affichage des glossaires. Voir le paramètre [\#dialogs.preferences.glossary](#dialogs.preferences.glossary) pour en savoir plus.

Les modifications apportées à un fichier de glossaire dans le dossier glossaire sont immédiatement reconnues par OmegaT et affichées dans le volet des glossaires.

OmegaT comprend un fichier de glossaire modifiable par projet. Utilisez [\#menus.edit](#menus.edit)[\#menus.edit.create.glossary.entry](#menus.edit.create.glossary.entry) pour ajouter des termes à ce fichier.

Voir l’annexe [\#app.glossaries](#app.glossaries) pour en savoir plus.

## Dictionnaires

Ce volet affiche les termes de vos fichiers de dictionnaire qui correspondent aux termes du segment en cours. Les fichiers du dictionnaire sont situés dans le dossier [\#project.folder.dictionary](#project.folder.dictionary) du projet. Voir les préférences [\#dialogs.preferences.dictionary](#dialogs.preferences.dictionary) pour en savoir plus.

## Traductions automatiques

Ce volet, lorsqu’il est ouvert, affiche les suggestions pour le segment en cours produites par chaque moteur de traduction activé. Lorsque des suggestions provenant de plusieurs moteurs sont disponibles, le nom du moteur apparait après le texte traduit,

-   le nom du moteur apparait après le texte traduit,

-   les résultats sont triés par ordre alphabétique du nom du moteur, et

-   la traduction actuellement sélectionnée est surlignée.

Utilisez [\#menus.edit](#menus.edit)[\#menus.edit.replace.with.mt.title](#menus.edit.replace.with.mt.title) pour remplacer la traduction du segment actuel par le moteur de traduction sélectionné.

Le nom du moteur sélectionné est affecté à la propriété `Origin` du segment en cours.

En cas d’erreur de connexion ou d’authentification avec un moteur de traduction automatique, la barre d’état située en bas de la fenêtre affiche brièvement un message d’état.

Assurez-vous que le service est activé et que vos informations d’identification ont été saisies correctement. Si c’est le cas, vous devrez peut-être contacter le fournisseur du service pour obtenir de l’aide. De même, une erreur telle que `Impossible d’analyser la réponse du service de traduction` suggère qu’il peut y avoir un problème de communication entre votre système et le serveur du fournisseur.

Voir le paramètre [\#dialogs.preferences.mt](#dialogs.preferences.mt) pour en savoir plus.

## Traductions multiples

Un segment source qui apparait à plusieurs endroits dans le projet peut nécessiter plusieurs traductions différentes en fonction du contexte.

Utilisez [\#menus.edit](#menus.edit)[\#menus.edit.create.alternative.translation](#menus.edit.create.alternative.translation) pour enregistrer une traduction alternative si la traduction actuelle du segment ne convient pas. La traduction saisie sera alors traitée comme une traduction alternative du segment source.

Utilisez [\#menus.edit](#menus.edit)[\#menus.edit.use.as.default.translation](#menus.edit.use.as.default.translation) pour définir l’une des alternatives - la plus courante ou la plus probable, par exemple - comme traduction par défaut.

## Bloc-note

Ce panneau est un espace *éditable* dans lequel vous pouvez ajouter des notes au segment actif.

Cela vous permet d’y revenir plus tard pour réviser la traduction, vérifier que les traductions alternatives sont correctes ou, dans le cadre de projets partagés, demander l’avis de collègues, par exemple.

Utilisez [\#menus.goto](#menus.goto)[\#menus.goto.next.note](#menus.goto.next.note) et [\#menus.goto](#menus.goto)[\#menus.goto.previous.note](#menus.goto.previous.note) pour parcourir les notes.

Utilisez [\#menus.goto](#menus.goto)[\#menus.goto.notes.pane](#menus.goto.notes.pane) pour entrer dans le volet et ajouter ou modifier une note.

Utilisez [\#menus.goto](#menus.goto)[\#menus.goto.editor.pane](#menus.goto.editor.pane) pour revenir à l’éditeur.

Les notes sont stockées dans la mémoire de traduction du projet. Elles ne sont *pas* stockées dans les fichiers traduits.

## Commentaires

Certains formats de fichiers, comme le format PO, peuvent contenir des commentaires qui vous permettront de mieux comprendre le contexte de la traduction. Ces commentaires sont affichés ici.

Le volet Commentaires n’est *pas* modifiable. Il affiche uniquement les informations contenues dans le fichier.

Utilisez le volet [\#panes.notes](#panes.notes) pour saisir vos propres commentaires sur une traduction.

## Propriétés du segment

Tous les segments ont des propriétés. Les propriétés sont affichées dans ce volet.

Les propriétés les plus courantes sont les suivantes :

Est un doublon   
Indique qu’un segment est une répétition et précise s’il s’agit de la PREMIÈRE instance.

Fichier  
Indique quel fichier contient le segment.

Le volet propriétés n’est *pas* modifiable. Il n’affiche que les informations relatives au segment.

## Barre d’état

La barre d’état se trouve en bas de la fenêtre principale.

La partie gauche de la barre d’état affiche des informations sur les actions du projet ou des messages d’erreur.

`Synchronisation des dépôts`

→ OmegaT ouvre un projet d’équipe et se synchronise avec le dépôt distant.

`Déplacement vers le dernier segment modifié…`

→ OmegaT ouvre le dernier segment modifié de la dernière session.

`Projet enregistré automatiquement à 22:48`

→ OmegaT a récemment enregistré le projet.

`Les fichiers traduits sont créés`

→ Les fichiers ont été créés par OmegaT et sont disponibles dans le dossier des fichiers traduits.

La partie droite de la barre d’état indique si le curseur est bloqué dans le segment (voir le paramètre [\#panes.editor.cursor.lock](#panes.editor.cursor.lock)) et si le curseur écrase le texte existant (voir le paramètre [\#panes.editor.overwriting](#panes.editor.overwriting)). Il affiche également des informations sur la progression.

Cliquez sur les chiffres pour alterner entre l’affichage de la progression sous forme de nombres ou de pourcentages.

`VER | ECR 257/271 (12292/154896, 177692) 35/0`

État du curseur  
`VER` indique que le curseur est verrouillé à l’intérieur du segment.

`ECR` indique que le curseur écrase le texte existant.

Dans le fichier  
**257** = nombre de segments traduits / **271** = nombre total de segments

Dans le projet  
**12292** = nombre de segments uniques traduits / **154896** = nombre total de segments uniques, **(177692)** = nombre total de segments

Dans le segment  
**35** = nombre de caractères dans la source / **0** = nombre de caractères dans la zone cible jusqu’à présent

`LIB | INS 94.8% (encore 14) / 7.9% (encore 142,604), 177,692 35/0`

État du curseur  
`LIB` indique que le curseur n’est pas bloqué à l’intérieur du segment et qu’il peut naviguer dans la fenêtre de l’éditeur à l’aide des commandes de navigation standard.

`INS` indique que le curseur insère du texte.

Dans le fichier  
**94.8%** = % de segments traduits / **14** = nombre de segments non traduits

Dans le projet  
**7.9%** = % de segments traduits / **142.604** = nombre de segments non traduits, **(177.692)** = nombre total de segments.

Dans le segment  
**35** = nombre de caractères dans la source / **0** = nombre de caractères dans la zone cible jusqu’à présent
