# Raccourcis OmegaT

## Description

L’interface d’OmegaT ne s’appuie généralement pas sur des boutons pour donner accès à ces fonctions. Au lieu de cela, elles sont appelées à partir des menus, ou pour la majorité des fonctions, à partir du raccourcis qui leur est associé.

Apprendre les raccourcis les plus fréquents ne vous prendra pas longtemps une fois que vous commencerez à travailler avec OmegaT. Les raccourcis sont indiqués à côté de chaque élément du menu, ce qui leur permet d’apprendre de nouveaux raccourcis au fur et à mesure de l’utilisation du logiciel.

Vous pouvez personnaliser la plupart des raccourcis sur OmegaT. Voir la section [\#app.shortcuts.customization](#app.shortcuts.customization) pour en savoir plus.

OmegaT fonctionne sur toutes les plateformes qui utilisent un système d’exploitation Java ( Windows, macOS et Linux étant les plus courants). Les touches de modification qui forment les raccourcis varient légèrement selon les plateformes. Pour faciliter la lecture, nous avons adopté la convention suivante pour les touches de modification :

<table>
<caption>Identifiants des touches de modification</caption>
<thead>
<tr class="header">
<th>Linux/Windows</th>
<th>Identifiant de la touche</th>
<th>macOS</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Maj</td>
<td>S</td>
<td>Maj ou ⇧</td>
</tr>
<tr class="even">
<td>Ctrl ou Contrôle</td>
<td>C</td>
<td>commande ou ⌘</td>
</tr>
<tr class="odd">
<td>Alt</td>
<td>A</td>
<td>alt / option ou ⌥</td>
</tr>
<tr class="even">
<td></td>
<td>Ctrl</td>
<td>contrôle ou ⌃</td>
</tr>
</tbody>
</table>

Identifiants des touches de modification

Les **identifiants de clés** ci-dessus nous permettent d’éviter d’énumérer de multiples notations pour chaque raccourci.

Sous Windows et Linux : <span class="keycombo">Ctrl+Maj+N</span>

Sous macOS : <span class="keycombo">Maj+commande+N</span>

Dans ce manuel : <span class="keycombo">C+S+N</span>

## Personnalisation

OmegaT associe des raccourcis à la plupart des fonctions disponibles dans les menus [\#menus.project](#menus.project), [\#menus.edit](#menus.edit), et [\#menus.goto](#menus.goto) et à un certain nombre de fonctions du volet [\#panes.editor](#panes.editor) . Vous pouvez également ajouter ou modifier les raccourcis de la plupart des fonctions.

Pour ce faire, vous devez placer le fichier de définition du raccourci approprié dans le dossier de configuration d’OmegaT. Voir l’annexe [\#configuration.folder](#configuration.folder) pour en savoir plus.

Il existe deux fichiers de définition des raccourcis.

MainMenuShortcuts.properties  
Le fichier de définition des raccourcis pour les menus et quelques autres éléments.

EditorShortcuts.properties  
Le fichier de définition de raccourci pour l’éditeur.

OmegaT doit être redémarré après la modification d’un fichier de définition de raccourci pour que les nouveaux raccourcis soient pris en compte.

Vous pouvez copier les fichiers de raccourcis OmegaT par défaut du site de développement d’OmegaT sur Sourceforge vers [ votre dossier de configuration ](#configuration.folder) et les modifier selon vos besoins :

Raccourcis par défaut de Windows et Linux  
-   [MainMenuShortcuts.properties](https://github.com/omegat-org/omegat/tree/master/src/org/omegat/gui/main/MainMenuShortcuts.properties)

-   [EditorShortcuts.properties](https://github.com/omegat-org/omegat/tree/master/src/org/omegat/gui/main/EditorShortcuts.properties)

Raccourcis par défaut de macOS  
-   [MainMenuShortcuts.mac.properties](https://github.com/omegat-org/omegat/tree/master/src/org/omegat/gui/main/MainMenuShortcuts.mac.properties)

-   [EditorShortcuts.mac.properties](https://github.com/omegat-org/omegat/tree/master/src/org/omegat/gui/main/EditorShortcuts.mac.properties)

Les fichiers macOS doivent être renommés [\#MainMenuShortcuts.properties](#MainMenuShortcuts.properties) et [\#EditorShortcuts.properties](#EditorShortcuts.properties) pour qu’OmegaT les reconnaisse.

La section suivante décrit la syntaxe utilisée dans les fichiers de définition des raccourcis, et fournit un exemple de modification.

## Syntaxe

La syntaxe de base des fichiers de définition des raccourcis est simple :

`code de fonction = raccourci`

Utilisez les tableaux dans la section ci-dessous[\#app.shortcuts.lists](#app.shortcuts.lists) afin de trouver les valeurs pour `le code de la fonction`.

Le `raccourci` représente la combinaison de touches que vous saisissez. Cela prend la forme suivante :

-   0 ou plus `touche modificatrice`

-   suivi par 0 ou 1`évènement`

-   suivi par 1 `touche de clavier`

<!-- -->

-   où la `touche modificatrice` peut être : `shift`, `ctrl`, `meta`, `alt`, ou `altGraph`

    `meta` fait référence à la touche portant le logo Windows sur la plupart des claviers Windows ou Linux, et à la touche `commande` sur macOS.

    `altGraph` fait référence à la touche *Alt* à droite de la barre d’espace sur les claviers avec deux touches*Alt*

-   L’`évènement` peut être :`typed`, `pressed`, `released`

-   et `la touche`peut être n’importe quelle touche disponible sur le clavier. Vous pouvez vous référer au [ tableau présentant les différents éditeurs de raccourcis](#app.shortcuts.lists.function.codes.editor.table) pour trouver les valeurs des touches telles que `Accueil`, `Haut de page`, ou les touches fléchées.

Des lignes vides et des commentaires peuvent être ajoutés pour organiser la liste et la rendre plus facile à lire. Une ligne de commentaire commence par `#`, et tout ce qui suit est ignoré par l’application.

La façon la plus simple de modifier les raccourcis est de télécharger des copies des fichiers par défaut dans [votre fichier de configuration](#configuration.folder), comme indiqué ci-dessus, et d’effectuer les changements que vous souhaitez.

Le raccourci par défaut pour [fermer un projet](#menus.project.close) est défini sous Windows et Linus comme :

`projectCloseMenuItem=ctrl shift W`

et sous macOS comme :

`projectCloseMenuItem=meta shift W`

Cependant, vous voulez peut-être supprimer la touche S du raccourci pour qu’il se définisse uniquement par <span class="keycombo">Ctrl+W</span> (ou <span class="keycombo">commande+W</span> sous macOS) pour qu’il corresponde au raccourci que vous utilisez dans d’autres applications.

Pour ce faire, modifier le `MainMenuShortcuts.properties` de la manière suivante pour Windows ou Linux :

`projectCloseMenuItem=ctrl W`

ou de la manière suivante pour macOS :

`projectCloseMenuItem=meta W`

Si votre paire de langues nécessite l’utilisation fréquente de [traductions alternatives](#menus.edit.create.alternative.translation), vous voudrez peut-être associer un raccourci à cette fonction puisqu’elle n’en a pas par défaut.

Les étapes ci-dessous montrent comment associer le raccourci <span class="keycombo">Alt+X</span> au menu [\#menus.edit](#menus.edit)[\#menus.edit.create.alternative.translation](#menus.edit.create.alternative.translation).

1.  Ouvrez le fichier `MainMenuShortcuts.properties` que vous avez copié dans [votre dossier de configuration](#configuration.folder) dans un éditeur de texte.

2.  Comme le montre le [tableau du menu édition](#app.shortcuts.lists.function.codes.edit.menu.table) ci-dessous, le code de la fonction Créer une traduction alternative est `editMultipleAlternate`.

    En recherchant ce code dans le fichier, vous arriverez à la ligne suivante :

    `# editMultipleAlternate=`

3.  La ligne est actuellement un commentaire. Supprimez le caractère `#` en début de ligne pour qu’OmegaT reconnaisse le raccourci, et ajoutez `alt X` après le signe `=` en fin de ligne :

    `editMultipleAlternate=alt X`

4.  Enregistrez et fermer le fichier. Au prochain démarrage d’OmegaT, votre nouveau raccourci devrait être actif et s’afficher dans le menu à côté du nom de la fonction.

Enregistrez le fichier une fois que vous avez terminé vos modifications. Si OmegaT est ouvert, vous devrez le redémarrer pour que vos modifications soient prises en compte.

Vos raccourcis modifiés ou ajoutés devraient maintenant être affichés à côté des éléments de menu que vous avez modifiés. Ils seront désormais disponibles dans OmegaT, à condition qu’il n’y ait pas de conflit avec d’autres fonctions ou avec des raccourcis du système.

La section suivante présente des tableaux contenant les codes de fonction et les raccourcis par défaut qui leur correspondent pour chaque menu ou fonction de l’éditeur d’OmegaT.

## Listes des fonctions et des codes

### Menu des fonctions

Les fonctions qui peuvent être modifiées dans le fichier `MainMenuShortcuts.properties`, ainsi que leurs valeurs par défaut, sont présentées dans les tableaux ci-dessous. Les raccourcis entre parenthèses sont des alternatives pour la même fonction que l’on trouve dans le `EditorShortcuts.properties`.

<table>
<caption>Menu Projet</caption>
<thead>
<tr class="header">
<th style="text-align: left;">Élément du menu</th>
<th style="text-align: left;">Code de la fonction</th>
<th style="text-align: center;">Windows/Linux</th>
<th style="text-align: center;">macOS</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;">Nouveau…</td>
<td style="text-align: left;">projectNewMenuItem</td>
<td style="text-align: center;">ctrl shift N</td>
<td style="text-align: center;">meta shift N</td>
</tr>
<tr class="even">
<td style="text-align: left;">Télécharger projet en équipe…</td>
<td style="text-align: left;">projectTeamNewMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Ouvrir…</td>
<td style="text-align: left;">projectOpenMenuItem</td>
<td style="text-align: center;">ctrl O</td>
<td style="text-align: center;">meta O</td>
</tr>
<tr class="even">
<td style="text-align: left;">Ouvert récemment…</td>
<td style="text-align: left;">projectOpenRecentMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Recharger</td>
<td style="text-align: left;">projectReloadMenuItem</td>
<td colspan="2" style="text-align: center;">F5</td>
</tr>
<tr class="even">
<td style="text-align: left;">Fermer</td>
<td style="text-align: left;">projectCloseMenuItem</td>
<td style="text-align: center;">ctrl shift W</td>
<td style="text-align: center;">meta shift W</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Enregistrer</td>
<td style="text-align: left;">projectSaveMenuItem</td>
<td style="text-align: center;">ctrl S</td>
<td style="text-align: center;">meta S</td>
</tr>
<tr class="even">
<td style="text-align: left;">Ajouter des fichiers…</td>
<td style="text-align: left;">projectImportMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Ajouter une page MediaWiki…</td>
<td style="text-align: left;">projectWikiImportMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: left;">Envoyer les fichiers source</td>
<td style="text-align: left;">projectCommitSourceFiles</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Envoyer les fichiers cible</td>
<td style="text-align: left;">projectCommitTargetFiles</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: left;">Create Translated Files</td>
<td style="text-align: left;">projectCompileMenuItem</td>
<td style="text-align: center;">ctrl D</td>
<td style="text-align: center;">meta D</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Create Current Translated File</td>
<td style="text-align: left;">projectSingleCompileMenuItem</td>
<td style="text-align: center;">ctrl shift D</td>
<td style="text-align: center;">meta shift D</td>
</tr>
<tr class="even">
<td style="text-align: left;">Ouvrir un projet MED…</td>
<td style="text-align: left;">projectMedOpenMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Créer projet MED</td>
<td style="text-align: left;">projectMedCreateMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: left;">Propriétés…</td>
<td style="text-align: left;">projectEditMenuItem</td>
<td style="text-align: center;">ctrl E</td>
<td style="text-align: center;">meta E</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Fichiers sources…</td>
<td style="text-align: left;">viewFileListMenuItem</td>
<td style="text-align: center;">ctrl L</td>
<td style="text-align: center;">meta L</td>
</tr>
<tr class="even">
<td style="text-align: left;">Access Project Contents/Project Folder</td>
<td style="text-align: left;">projectAccessRootMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Accéder au contenu du projet/Dictionnaires</td>
<td style="text-align: left;">projectAccessDictionaryMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: left;">Accéder au contenu du projet/Glossaires</td>
<td style="text-align: left;">projectAccessGlossaryMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Accéder au contenu du projet/Fichiers source</td>
<td style="text-align: left;">projectAccessSourceMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: left;">Accéder au contenu du projet/Fichiers cible</td>
<td style="text-align: left;">projectAccessTargetMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Accéder au contenu du projet/MT</td>
<td style="text-align: left;">projectAccessTMMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: left;">Accéder au contenu du projet/Mémoires exportées</td>
<td style="text-align: left;">projectAccessExportTMMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Accéder au contenu du projet/Document source actuel</td>
<td style="text-align: left;">projectAccessCurrentSourceDocumentMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: left;">Accéder au contenu du projet/Document cible actuel</td>
<td style="text-align: left;">projectAccessCurrentTargetDocumentMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Accéder au contenu du projet/Glossaire modifiable</td>
<td style="text-align: left;">projectAccessWriteableGlossaryMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: left;">Redémarrer</td>
<td style="text-align: left;">projectRestartMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Quitter</td>
<td style="text-align: left;">projectExitMenuItem</td>
<td style="text-align: center;">ctrl Q</td>
<td style="text-align: center;">meta Q</td>
</tr>
</tbody>
</table>

Menu Projet

<table>
<caption>Menu Édition</caption>
<thead>
<tr class="header">
<th style="text-align: left;">Élément du menu</th>
<th style="text-align: left;">Code de la fonction</th>
<th style="text-align: center;">Windows/Linux</th>
<th style="text-align: center;">macOS</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;">Annuler</td>
<td style="text-align: left;">editUndoMenuItem</td>
<td style="text-align: center;">ctrl Z</td>
<td style="text-align: center;">meta Z</td>
</tr>
<tr class="even">
<td style="text-align: left;">Rétablir</td>
<td style="text-align: left;">editRedoMenuItem</td>
<td style="text-align: center;">ctrl Y</td>
<td style="text-align: center;">meta Y</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Remplacer par la correspondance ou la sélection</td>
<td style="text-align: left;">editOverwriteTranslationMenuItem</td>
<td style="text-align: center;">ctrl R</td>
<td style="text-align: center;">meta R</td>
</tr>
<tr class="even">
<td style="text-align: left;">Insérer la correspondance ou la sélection</td>
<td style="text-align: left;">editInsertTranslationMenuItem</td>
<td style="text-align: center;">ctrl I</td>
<td style="text-align: center;">meta I</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Remplacer par la source</td>
<td style="text-align: left;">editOverwriteSourceMenuItem</td>
<td style="text-align: center;">ctrl shift R</td>
<td style="text-align: center;">meta shift R</td>
</tr>
<tr class="even">
<td style="text-align: left;">Insérer le texte source</td>
<td style="text-align: left;">editInsertSourceMenuItem</td>
<td style="text-align: center;">ctrl shift I</td>
<td style="text-align: center;">meta shift I</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Sélectionner le texte source</td>
<td style="text-align: left;">editSelectSourceMenuItem</td>
<td style="text-align: center;">ctrl shift A</td>
<td style="text-align: center;">meta shift A</td>
</tr>
<tr class="even">
<td style="text-align: left;">Remplacer par une traduction automatique</td>
<td style="text-align: left;">editOverwriteMachineTranslationMenuItem</td>
<td style="text-align: center;">ctrl M</td>
<td style="text-align: center;">meta M</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Insérer les balises manquantes</td>
<td style="text-align: left;">editTagPainterMenuItem</td>
<td style="text-align: center;">ctrl shift T</td>
<td style="text-align: center;">meta shift T</td>
</tr>
<tr class="even">
<td style="text-align: left;">Insérer la prochaine balise manquante</td>
<td style="text-align: left;">editTagNextMissedMenuItem</td>
<td style="text-align: center;">ctrl T</td>
<td style="text-align: center;">meta T</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Exporter la sélection</td>
<td style="text-align: left;">editExportSelectionMenuItem</td>
<td style="text-align: center;">ctrl shift C</td>
<td style="text-align: center;">meta shift C</td>
</tr>
<tr class="even">
<td style="text-align: left;">Créer une entrée de glossaire</td>
<td style="text-align: left;">editCreateGlossaryEntryMenuItem</td>
<td style="text-align: center;">ctrl shift G</td>
<td style="text-align: center;">meta shift G</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Rechercher…</td>
<td style="text-align: left;">editFindInProjectMenuItem</td>
<td style="text-align: center;">ctrl F</td>
<td style="text-align: center;">meta F</td>
</tr>
<tr class="even">
<td style="text-align: left;">(Call Last Search Window)</td>
<td style="text-align: left;">findInProjectReuseLastWindow</td>
<td style="text-align: center;">ctrl shift F</td>
<td style="text-align: center;">meta shift F</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Remplacer…</td>
<td style="text-align: left;">editReplaceInProjectMenuItem</td>
<td style="text-align: center;">ctrl K</td>
<td style="text-align: center;">meta K</td>
</tr>
<tr class="even">
<td style="text-align: left;">Rechercher dans les dictionnaires</td>
<td style="text-align: left;">editSearchDictionaryMenuItem</td>
<td colspan="2" style="text-align: center;">alt shift D</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Basculer la casse en/minuscule</td>
<td style="text-align: left;">lowerCaseMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: left;">Basculer la casse en/MAJUSCULE</td>
<td style="text-align: left;">upperCaseMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Basculer la casse en/Première Lettre Des Mots En Majuscule</td>
<td style="text-align: left;">titleCaseMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: left;">Basculer la casse en/Casse de phrase</td>
<td style="text-align: left;">sentenceCaseMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Basculer la casse en/Parcourir</td>
<td style="text-align: left;">cycleSwitchCaseMenuItem</td>
<td colspan="2" style="text-align: center;">Maj+F3</td>
</tr>
<tr class="even">
<td style="text-align: left;">Choisir une correspondance/Choisir la correspondance précédente</td>
<td style="text-align: left;">editSelectFuzzyPrevMenuItem</td>
<td style="text-align: center;">ctrl UP</td>
<td style="text-align: center;">meta UP</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Choisir une correspondance/Choisir la correspondance suivante</td>
<td style="text-align: left;">editSelectFuzzyNextMenuItem</td>
<td style="text-align: center;">ctrl DOWN</td>
<td style="text-align: center;">meta DOWN</td>
</tr>
<tr class="even">
<td style="text-align: left;">Choisir une correspondance/Choisir la correspondance #1</td>
<td style="text-align: left;">editSelectFuzzy1MenuItem</td>
<td style="text-align: center;">ctrl 1</td>
<td style="text-align: center;">meta 1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Choisir une correspondance/Choisir la correspondance #2</td>
<td style="text-align: left;">editSelectFuzzy2MenuItem</td>
<td style="text-align: center;">ctrl 2</td>
<td style="text-align: center;">meta 2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Choisir une correspondance/Choisir la correspondance #3</td>
<td style="text-align: left;">editSelectFuzzy3MenuItem</td>
<td style="text-align: center;">ctrl 3</td>
<td style="text-align: center;">meta 3</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Choisir une correspondance/Choisir la correspondance #4</td>
<td style="text-align: left;">editSelectFuzzy4MenuItem</td>
<td style="text-align: center;">ctrl 4</td>
<td style="text-align: center;">meta 4</td>
</tr>
<tr class="even">
<td style="text-align: left;">Choisir une correspondance/Choisir la correspondance #5</td>
<td style="text-align: left;">editSelectFuzzy5MenuItem</td>
<td style="text-align: center;">ctrl 5</td>
<td style="text-align: center;">meta 5</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Insérer un caractère de contrôle Bidi/Marque de gauche à droite (LRM U+200E)</td>
<td style="text-align: left;">insertCharsLRM</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: left;">Insérer un caractère de contrôle Unicode/Marque de droite à gauche (RLM U+200F)</td>
<td style="text-align: left;">insertCharsRLM</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Insérer un caractère de contrôle Unicode/Début de l’imbrication de gauche à droite (LRE U+202A)</td>
<td style="text-align: left;">insertCharsLRE</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: left;">Insérer un caractère de contrôle Unicode/Début de l’imbrication de droite à gauche (RLE U+202B)</td>
<td style="text-align: left;">insertCharsRLE</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Insérer un caractère de contrôle Unicode/Fin de formatage directionnel (PDF U+202C)</td>
<td style="text-align: left;">insertCharsPDF</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: left;">Utiliser comme traduction par défaut</td>
<td style="text-align: left;">editMultipleDefault</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Créer une traduction alternative</td>
<td style="text-align: left;">editMultipleAlternate</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: left;">Supprimer la traduction</td>
<td style="text-align: left;">editRegisterUntranslatedMenuItem</td>
<td style="text-align: center;">ctrl shift X</td>
<td style="text-align: center;">meta shift X</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Enregistrer une traduction vide</td>
<td style="text-align: left;">editRegisterEmptyMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: left;">Enregistrer une traduction identique à la source</td>
<td style="text-align: left;">editRegisterIdenticalMenuItem</td>
<td style="text-align: center;">ctrl shift S</td>
<td style="text-align: center;">meta shift S</td>
</tr>
</tbody>
</table>

Menu Édition

<table>
<caption>Menu Atteindre</caption>
<thead>
<tr class="header">
<th style="text-align: left;">Élément du menu</th>
<th style="text-align: left;">Code de la fonction</th>
<th style="text-align: center;">Windows/Linux</th>
<th style="text-align: center;">macOS</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;">Segment non traduit suivant</td>
<td style="text-align: left;">gotoNextUntranslatedMenuItem</td>
<td style="text-align: center;">ctrl U</td>
<td style="text-align: center;">meta U</td>
</tr>
<tr class="even">
<td style="text-align: left;">Segment traduit suivant</td>
<td style="text-align: left;">gotoNextTranslatedMenuItem</td>
<td style="text-align: center;">ctrl shift U</td>
<td style="text-align: center;">meta shift U</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Segment suivant</td>
<td style="text-align: left;">gotoNextSegmentMenuItem</td>
<td style="text-align: center;">ctrl N (Enter/Tab)</td>
<td style="text-align: center;">meta N (Enter/Tab)</td>
</tr>
<tr class="even">
<td style="text-align: left;">Segment précédent</td>
<td style="text-align: left;">gotoPreviousSegmentMenuItem</td>
<td style="text-align: center;">ctrl P (ctrl Enter / ctrl Tab)</td>
<td style="text-align: center;">meta P (meta Enter / shift Tab)</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Segment numéro…</td>
<td style="text-align: left;">gotoSegmentMenuItem</td>
<td style="text-align: center;">ctrl J</td>
<td style="text-align: center;">meta J</td>
</tr>
<tr class="even">
<td style="text-align: left;">Note suivante</td>
<td style="text-align: left;">gotoNextNoteMenuItem</td>
<td style="text-align: center;">ctrl alt N</td>
<td style="text-align: center;">meta alt N</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Note précédente</td>
<td style="text-align: left;">gotoPreviousNoteMenuItem</td>
<td style="text-align: center;">ctrl alt P</td>
<td style="text-align: center;">meta alt P</td>
</tr>
<tr class="even">
<td style="text-align: left;">Segment unique suivant</td>
<td style="text-align: left;">gotoNextUniqueMenuItem</td>
<td style="text-align: center;">ctrl shift K</td>
<td style="text-align: center;">meta shift K</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Source de la correspondance sélectionnée</td>
<td style="text-align: left;">gotoMatchSourceSegment</td>
<td style="text-align: center;">ctrl shift M</td>
<td style="text-align: center;">meta shift M</td>
</tr>
<tr class="even">
<td style="text-align: left;">Segments autotraduits/Segment suivant venant de tm/auto/</td>
<td style="text-align: left;">gotoNextXAutoMenuItem</td>
<td style="text-align: center;">ctrl alt COMMA</td>
<td style="text-align: center;">meta alt COMMA</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Segments autotraduits/Segment précédent venant de tm/auto/</td>
<td style="text-align: left;">gotoPrevXAutoMenuItem</td>
<td style="text-align: center;">ctrl alt shift COMMA</td>
<td style="text-align: center;">meta alt shift COMMA</td>
</tr>
<tr class="even">
<td style="text-align: left;">Segments autotraduits/Segment suivant venant de tm/enforce/</td>
<td style="text-align: left;">gotoNextXEnforcedMenuItem</td>
<td style="text-align: center;">ctrl alt PERIOD</td>
<td style="text-align: center;">meta alt PERIOD</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Segments autotraduits/Segment précédent venant de tm/enforce/</td>
<td style="text-align: left;">gotoPrevXEnforcedMenuItem</td>
<td style="text-align: center;">ctrl alt shift PERIOD</td>
<td style="text-align: center;">meta alt shift PERIOD</td>
</tr>
<tr class="even">
<td style="text-align: left;">Segment précédent dans l’historique</td>
<td style="text-align: left;">gotoHistoryBackMenuItem</td>
<td style="text-align: center;">ctrl shift P</td>
<td style="text-align: center;">meta shift P</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Segment suivant dans l’historique</td>
<td style="text-align: left;">gotoHistoryForwardMenuItem</td>
<td style="text-align: center;">ctrl shift N</td>
<td style="text-align: center;">meta shift N</td>
</tr>
<tr class="even">
<td style="text-align: left;">Bloc-note</td>
<td style="text-align: left;">gotoNotesPanelMenuItem</td>
<td style="text-align: center;">ctrl alt 9</td>
<td style="text-align: center;">meta alt 9</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Éditeur</td>
<td style="text-align: left;">gotoEditorPanelMenuItem</td>
<td style="text-align: center;">ctrl alt 0</td>
<td style="text-align: center;">meta alt 0</td>
</tr>
</tbody>
</table>

Menu Atteindre

<table>
<caption>Menu Affichage</caption>
<thead>
<tr class="header">
<th style="text-align: left;">Élément du menu</th>
<th style="text-align: left;">Code de la fonction</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;">Surligner les segments traduits</td>
<td style="text-align: left;">viewMarkTranslatedSegmentsCheckBoxMenuItem</td>
</tr>
<tr class="even">
<td style="text-align: left;">Surligner les segments non traduits</td>
<td style="text-align: left;">viewMarkUntranslatedSegmentsCheckBoxMenuItem</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Afficher les délimitations de paragraphes</td>
<td style="text-align: left;">viewMarkParagraphStartCheckBoxMenuItem</td>
</tr>
<tr class="even">
<td style="text-align: left;">Afficher les segments sources</td>
<td style="text-align: left;">viewDisplaySegmentSourceCheckBoxMenuItem</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Colorer les segments répétés</td>
<td style="text-align: left;">viewMarkNonUniqueSegmentsCheckBoxMenuItem</td>
</tr>
<tr class="even">
<td style="text-align: left;">Surligner les segments avec notes</td>
<td style="text-align: left;">viewMarkNotedSegmentsCheckBoxMenuItem</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Afficher les espaces insécables</td>
<td style="text-align: left;">viewMarkNBSPCheckBoxMenuItem</td>
</tr>
<tr class="even">
<td style="text-align: left;">Afficher les caractères d’espacement</td>
<td style="text-align: left;">viewMarkWhitespaceCheckBoxMenuItem</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Afficher les caractères de contrôle de bidirectionnalité</td>
<td style="text-align: left;">viewMarkBidiCheckBoxMenuItem</td>
</tr>
<tr class="even">
<td style="text-align: left;">Surligner les segments autotraduits</td>
<td style="text-align: left;">viewMarkAutoPopulatedCheckBoxMenuItem</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Souligner les correspondances de glossaire</td>
<td style="text-align: left;">viewMarkGlossaryMatchesCheckBoxMenuItem</td>
</tr>
<tr class="even">
<td style="text-align: left;">Souligner les problèmes du vérificateur linguistique.</td>
<td style="text-align: left;">viewMarkLanguageCheckerCheckBoxMenuItem</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Utilisation intensive des polices de repli</td>
<td style="text-align: left;">viewMarkFontFallbackCheckBoxMenuItem</td>
</tr>
<tr class="even">
<td style="text-align: left;">Afficher les informations de modification/Aucune</td>
<td style="text-align: left;">viewDisplayModificationInfoNoneRadioButtonMenuItem</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Afficher les informations de modification/pour le segment actuel</td>
<td style="text-align: left;">viewDisplayModificationInfoSelectedRadioButtonMenuItem</td>
</tr>
<tr class="even">
<td style="text-align: left;">Afficher les informations de modification/pour tous les segments</td>
<td style="text-align: left;">viewDisplayModificationInfoAllRadioButtonMenuItem</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Réinitialiser la fenêtre d’OmegaT</td>
<td style="text-align: left;">viewRestoreGUIMenuItem</td>
</tr>
</tbody>
</table>

Menu Affichage

<table>
<caption>Menu Outils</caption>
<thead>
<tr class="header">
<th style="text-align: left;">Élément du menu</th>
<th style="text-align: left;">Code de la fonction</th>
<th style="text-align: center;">Windows/Linux</th>
<th style="text-align: center;">macOS</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;">Afficher les erreurs…</td>
<td style="text-align: left;">toolsCheckIssuesMenuItem</td>
<td style="text-align: center;">ctrl shift V</td>
<td style="text-align: center;">meta shift V</td>
</tr>
<tr class="even">
<td style="text-align: left;">Afficher les erreurs pour le document actuel</td>
<td style="text-align: left;">toolsCheckIssuesCurrentFileMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Statistiques</td>
<td style="text-align: left;">toolsShowStatisticsStandardMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: left;">Statistiques des correspondances</td>
<td style="text-align: left;">toolsShowStatisticsMatchesMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Statistiques des correspondances par fichier</td>
<td style="text-align: left;">toolsShowStatisticsMatchesPerFileMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: left;">Aligner les fichiers…</td>
<td style="text-align: left;">toolsAlignFilesMenuItem</td>
<td style="text-align: center;"></td>
<td style="text-align: center;"></td>
</tr>
</tbody>
</table>

Menu Outils

L’élément [\#windows.scripts](#windows.scripts) dans le menu [\#menus.tools](#menus.tools) est une exception.

Il n’est pas possible d’ajouter un raccourci pour ouvrir l’éditeur de script, ni de modifier les raccourcis associés aux scripts.

<table>
<caption>Menu Options</caption>
<thead>
<tr class="header">
<th style="text-align: left;">Élément du menu</th>
<th style="text-align: left;">Code de la fonction</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;">Préférences</td>
<td style="text-align: left;">optionsPreferencesMenuItem</td>
</tr>
<tr class="even">
<td style="text-align: left;">Traduction automatique/Récupérer automatiquement les traductions</td>
<td style="text-align: left;">optionsMTAutoFetchCheckboxMenuItem</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Glossaires/Utiliser la lemmatisation</td>
<td style="text-align: left;">optionsGlossaryFuzzyMatchingCheckBoxMenuItem</td>
</tr>
<tr class="even">
<td style="text-align: left;">Dictionnaires/Utiliser la lemmatisation</td>
<td style="text-align: left;">optionsDictionaryFuzzyMatchingCheckBoxMenuItem</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Saisie automatique/Afficher automatiquement les suggestions pertinentes</td>
<td style="text-align: left;">optionsAutoCompleteShowAutomaticallyItem</td>
</tr>
<tr class="even">
<td style="text-align: left;">Saisie automatique/Saisie à partir de l’historique</td>
<td style="text-align: left;">optionsAutoCompleteHistoryCompletionMenuItem</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Saisie automatique/Prédiction historique</td>
<td style="text-align: left;">optionsAutoCompleteHistoryPredictionMenuItem</td>
</tr>
<tr class="even">
<td style="text-align: left;">Filtres de fichiers généraux…</td>
<td style="text-align: left;">optionsSetupFileFiltersMenuItem</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Règles de segmentation générales…</td>
<td style="text-align: left;">optionsSentsegMenuItem</td>
</tr>
<tr class="even">
<td style="text-align: left;">Éditeur…</td>
<td style="text-align: left;">optionsWorkflowMenuItem</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Dossier de configuration</td>
<td style="text-align: left;">optionsAccessConfigDirMenuItem</td>
</tr>
</tbody>
</table>

Menu Options

<table>
<caption>Menu Aide</caption>
<thead>
<tr class="header">
<th style="text-align: left;">Élément du menu</th>
<th style="text-align: left;">Code de la fonction</th>
<th style="text-align: center;">Windows/Linux</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;">Manuel d’utilisation…</td>
<td style="text-align: left;">helpContentsMenuItem</td>
<td style="text-align: center;">F1</td>
</tr>
<tr class="even">
<td style="text-align: left;">À propos…</td>
<td style="text-align: left;">helpAboutMenuItem</td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Dernières modifications…</td>
<td style="text-align: left;">helpLastChangesMenuItem</td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: left;">Journal…</td>
<td style="text-align: left;">helpLogMenuItem</td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: left;">Rechercher des mises à jour…</td>
<td style="text-align: left;">helpUpdateCheckMenuItem</td>
<td style="text-align: center;"></td>
</tr>
</tbody>
</table>

Menu Aide

<table>
<caption>Fenêtre de recherche</caption>
<thead>
<tr class="header">
<th style="text-align: left;">Élément du menu</th>
<th style="text-align: left;">Code de la fonction</th>
<th style="text-align: center;">Windows/Linux</th>
<th style="text-align: center;">macOS</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;">Atteindre le segment numéro…</td>
<td style="text-align: left;">jumpToEntryInEditor</td>
<td style="text-align: center;">ctrl J</td>
<td style="text-align: center;">meta J</td>
</tr>
</tbody>
</table>

Fenêtre de recherche

### Fonctions de l’Éditeur

Les raccourcis qui peuvent être modifiés dans le fichier `EditorShortcuts.properties`, ainsi que leurs valeurs par défaut, sont présentés dans le tableau ci-dessous.

<table>
<caption>Éditeur</caption>
<thead>
<tr class="header">
<th style="text-align: left;">Fonction</th>
<th style="text-align: left;">Code de la fonction</th>
<th style="text-align: center;">Windows/Linux</th>
<th style="text-align: center;">macOS</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;">ouvrir le menu contextuel</td>
<td style="text-align: left;">editorContextMenu</td>
<td style="text-align: center;">CONTEXT_MENU</td>
<td style="text-align: center;">shift ESCAPE</td>
</tr>
<tr class="even">
<td style="text-align: left;">Atteindre le prochain segment</td>
<td style="text-align: left;">editorNextSegment</td>
<td colspan="2" style="text-align: center;">TAB</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Atteindre le segment précédent</td>
<td style="text-align: left;">editorPrevSegment</td>
<td colspan="2" style="text-align: center;">shift TAB</td>
</tr>
<tr class="even">
<td style="text-align: left;">Atteindre le prochain segment (non tabulé)</td>
<td style="text-align: left;">editorNextSegmentNotTab</td>
<td colspan="2" style="text-align: center;">ENTER</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Atteindre le segment précédent (non tabulé)</td>
<td style="text-align: left;">editorPrevSegmentNotTab</td>
<td style="text-align: center;">ctrl ENTER</td>
<td style="text-align: center;">meta ENTER</td>
</tr>
<tr class="even">
<td style="text-align: left;">Insérer un saut de ligne</td>
<td style="text-align: left;">editorInsertLineBreak</td>
<td colspan="2" style="text-align: center;">shift ENTER</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Tout sélectionner</td>
<td style="text-align: left;">editorSelectAll</td>
<td style="text-align: center;">ctrl A</td>
<td style="text-align: center;">meta A</td>
</tr>
<tr class="even">
<td style="text-align: left;">Supprimer l’élément qui précède</td>
<td style="text-align: left;">editorDeletePrevToken</td>
<td style="text-align: center;">ctrl BACK_SPACE</td>
<td style="text-align: center;">alt BACK_SPACE</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Supprimer l’élément qui suit</td>
<td style="text-align: left;">editorDeleteNextToken</td>
<td style="text-align: center;">ctrl DELETE</td>
<td style="text-align: center;">alt DELETE</td>
</tr>
<tr class="even">
<td style="text-align: left;">Atteindre le premier segment</td>
<td style="text-align: left;">editorFirstSegment</td>
<td style="text-align: center;">ctrl PAGE_UP</td>
<td style="text-align: center;">meta PAGE_UP</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Atteindre le dernier segment</td>
<td style="text-align: left;">editorLastSegment</td>
<td style="text-align: center;">ctrl PAGE_DOWN</td>
<td style="text-align: center;">meta PAGE_DOWN</td>
</tr>
<tr class="even">
<td style="text-align: left;">Passer l’élément suivant</td>
<td style="text-align: left;">editorSkipNextToken</td>
<td style="text-align: center;">ctrl RIGHT</td>
<td style="text-align: center;">alt RIGHT</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Passer l’élément précédent</td>
<td style="text-align: left;">editorSkipPrevToken</td>
<td style="text-align: center;">ctrl LEFT</td>
<td style="text-align: center;">alt LEFT</td>
</tr>
<tr class="even">
<td style="text-align: left;">Passer l’élément suivant avec sélection</td>
<td style="text-align: left;">editorSkipNextTokenWithSelection</td>
<td style="text-align: center;">ctrl shift RIGHT</td>
<td style="text-align: center;">alt shift RIGHT</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Passer l’élément précédent avec sélection</td>
<td style="text-align: left;">editorSkipPrevTokenWithSelection</td>
<td style="text-align: center;">ctrl shift LEFT</td>
<td style="text-align: center;">alt shift LEFT</td>
</tr>
<tr class="even">
<td style="text-align: left;">Verrouillage du curseur</td>
<td style="text-align: left;">editorToggleCursorLock</td>
<td colspan="2" style="text-align: center;">F2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Afficher la saisie</td>
<td style="text-align: left;">editorToggleOvertype</td>
<td style="text-align: center;">INSERT</td>
<td style="text-align: center;">F3</td>
</tr>
</tbody>
</table>

Éditeur

<table>
<caption>Saisie automatique</caption>
<thead>
<tr class="header">
<th style="text-align: left;">Fonction</th>
<th style="text-align: left;">Code de la fonction</th>
<th style="text-align: center;">Windows/Linux</th>
<th style="text-align: center;">macOS</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;">Ouvrir la saisie automatique</td>
<td style="text-align: left;">autocompleterTrigger</td>
<td style="text-align: center;">ctrl SPACE</td>
<td style="text-align: center;">ESCAPE</td>
</tr>
<tr class="even">
<td style="text-align: left;">Afficher les prochaines suggestions de la saisie automatique</td>
<td style="text-align: left;">autocompleterNextView</td>
<td style="text-align: center;">ctrl SPACE</td>
<td style="text-align: center;">ctrl DOWN</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Afficher les suggestions précédentes de la saisie automatique</td>
<td style="text-align: left;">autocompleterPrevView</td>
<td style="text-align: center;">ctrl shift SPACE</td>
<td style="text-align: center;">ctrl UP</td>
</tr>
<tr class="even">
<td style="text-align: left;">Valider et fermer la saisie automatique</td>
<td style="text-align: left;">autocompleterConfirmAndClose</td>
<td colspan="2" style="text-align: center;">ENTER</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Valider la saisie automatique sans la fermer</td>
<td style="text-align: left;">autocompleterConfirmWithoutClose</td>
<td colspan="2" style="text-align: center;">INSERT</td>
</tr>
<tr class="even">
<td style="text-align: left;">Fermer la saisie automatique</td>
<td style="text-align: left;">autocompleterClose</td>
<td colspan="2" style="text-align: center;">ESCAPE</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Aller en haut de la liste</td>
<td style="text-align: left;">autocompleterListUp</td>
<td colspan="2" style="text-align: center;">UP</td>
</tr>
<tr class="even">
<td style="text-align: left;">Aller en fin de liste</td>
<td style="text-align: left;">autocompleterListDown</td>
<td colspan="2" style="text-align: center;">DOWN</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Remonter d’une page</td>
<td style="text-align: left;">autocompleterListPageUp</td>
<td colspan="2" style="text-align: center;">PAGE_UP</td>
</tr>
<tr class="even">
<td style="text-align: left;">Descendre d’une page</td>
<td style="text-align: left;">autocompleterListPageDown</td>
<td colspan="2" style="text-align: center;">PAGE_DOWN</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Remonter dans le tableau</td>
<td style="text-align: left;">autocompleterTableUp</td>
<td colspan="2" style="text-align: center;">UP</td>
</tr>
<tr class="even">
<td style="text-align: left;">Descendre dans le tableau</td>
<td style="text-align: left;">autocompleterTableDown</td>
<td colspan="2" style="text-align: center;">DOWN</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Se déplacer à gauche dans le tableau</td>
<td style="text-align: left;">autocompleterTableLeft</td>
<td colspan="2" style="text-align: center;">LEFT</td>
</tr>
<tr class="even">
<td style="text-align: left;">Aller à droite dans le tableau</td>
<td style="text-align: left;">autocompleterTableRight</td>
<td colspan="2" style="text-align: center;">RIGHT</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Remonter d’une page dans le tableau</td>
<td style="text-align: left;">autocompleterTablePageUp</td>
<td colspan="2" style="text-align: center;">PAGE_UP</td>
</tr>
<tr class="even">
<td style="text-align: left;">Descendre d’une page dans le tableau</td>
<td style="text-align: left;">autocompleterTablePageDown</td>
<td colspan="2" style="text-align: center;">PAGE_DOWN</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Aller au premier tableau</td>
<td style="text-align: left;">autocompleterTableFirst</td>
<td style="text-align: center;">ctrl HOME</td>
<td style="text-align: center;">meta HOME</td>
</tr>
<tr class="even">
<td style="text-align: left;">Aller au dernier tableau</td>
<td style="text-align: left;">autocompleterTableLast</td>
<td style="text-align: center;">ctrl END</td>
<td style="text-align: center;">meta END</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Aller à la première ligne du tableau</td>
<td style="text-align: left;">autocompleterTableFirstInRow</td>
<td colspan="2" style="text-align: center;">HOME</td>
</tr>
<tr class="even">
<td style="text-align: left;">Aller à la dernière ligne du tableau</td>
<td style="text-align: left;">autocompleterTableLastInRow</td>
<td colspan="2" style="text-align: center;">END</td>
</tr>
</tbody>
</table>

Saisie automatique
