# Introduction à OmegaT

## Les principes

Bienvenue sur OmegaT, un outil de traduction assistée par ordinateur (TAO) offrant une grande flexibilité, des performances et une robustesse exceptionnelles, ainsi que des fonctionnalités dépassant celles proposées par les offres commerciales, même pour les traductaires débutants.

### Projet de traduction

Un projet de traduction OmegaT est constitué de plusieurs ressources stockées dans différents dossiers, ainsi que de deux fichiers : un fichier [`omegat.project`](#project.folder.omegat.project.file) qui indique où se trouvent toutes les ressources, et un fichier de mémoire de traduction [`project_save.tmx`](#project.folder.project.save.tmx) qui contient toutes les traductions effectuées pendant le travail sur ce projet.

Les traductaires peuvent facilement modifier le contenu ou l’emplacement de ces ressources à n’importe quel moment pendant la traduction.

Les ressources comprennent par défaut la mémoire de traduction du projet, qui est automatiquement créée lors de la création du projet, et des fichiers à traduire. Elles peuvent également inclure des mémoires de traduction de référence, des glossaires et d’autres fichiers de référence.

Voir le chapitre [\#chapter.project.folder](#chapter.project.folder) pour en savoir plus.

### Mémoires de traduction

Il n’est pas nécessaire pour les traductaires de *créer* une mémoire de traduction ou d’en *associer* une à un nouveau projet. OmegaT le fait *automatiquement*.

Les traductaires peuvent facilement réutiliser la mémoire de traduction (MT) d’un projet existant en ajoutant simplement de nouveaux fichiers à un projet existant ou en copiant une MT existante dans un nouveau projet.

Dans un projet de traduction, il est possible d’utiliser un nombre illimité de mémoires de traduction comme référence. OmegaT permet d’associer facilement différents niveaux de priorité à ces mémoires supplémentaires.

Voir le guide pratique [\#how.to.use.tm](#how.to.use.tm) pour en savoir plus.

### Collaboration

Les traductaires peuvent facilement partager des ressources et travailler à plusieurs sur un projet en utilisant des paramètres simples.

La fonctionnalité permettant le travail en équipe offre une robustesse de niveau professionnel et la flexibilité nécessaire pour synchroniser les ressources du projet entre les membres de l’équipe, tout en permettant de résoudre facilement les conflits entre les différentes traductions.

Voir le guide pratique [\#how.to.tm.share.translation.memories](#how.to.tm.share.translation.memories) pour en savoir plus.

### Conçu pour les traductaires

OmegaT est conçu non seulement pour faciliter le processus de traduction, mais aussi pour que les traductaires n’aient pas à s’inquiéter de la perte de données.

Vous n’avez pas encore utilisé OmegaT, mais vous vous souvenez des fois où vous traduisiez dans votre traitement de texte et où un problème informatique a fait disparaitre la traduction du livre sur lequel vous travailliez depuis six mois, ou le rapport que vous deviez rendre dans une heure.

Vous envisagez d’utiliser OmegaT, mais…

Comment OmegaT peut-il aider à éviter de tels problèmes  ?

Pas de panique. Grâce à la conception robuste d’OmegaT, il est *très peu* probable que vous ayez perdu plus de quelques minutes de travail.

Même si la situation semble très dégradée, ne paniquez pas. Il suffit de suivre les instructions décrites dans le guide pratique [\#how.to.restore.your.data](#how.to.restore.your.data).

Avant de suivre ces étapes, OmegaT vous permettra de vous concentrer sur votre travail de traduction et vous aidera, autant que possible, à améliorer vos compétences en traduction.

Si vous avez besoin d’aide concernant tout élément d’OmegaT, n’hésitez pas à rejoindre les [groupes de soutien d’OmegaT.](https://omegat.org/support)

## Conventions utilisées dans ce manuel

Cette section présente les conventions utilisées pour identifier les éléments de l’interface graphique d’OmegaT dans ce manuel. Ils sont présentés de manière à faciliter l’identification de leur fonction. L’action associée à un élément indique également sa fonction au cas où l’affichage ne permettrait pas de mettre en évidence les différences visuelles : *utiliser* un élément de menu, ou *cliquer* sur un bouton.

De même, les liens vers les différentes parties du manuel sont présentés de manière à identifier plus facilement la fonction de l’élément lié.

Éléments du menu avec un raccourci par défaut  
Utilisez [\#menus.project](#menus.project)[\#menus.project.new](#menus.project.new).

Éléments du menu sans raccourci par défaut  
Utilisez [\#menus.project](#menus.project)[\#menus.project.copy.files.to.source.folder](#menus.project.copy.files.to.source.folder).

Boutons  
Cliquez sur [\#windows.source.files.list.copy.files](#windows.source.files.list.copy.files).

Volets, fenêtres et boites de dialogue  
Le volet [\#panes.editor](#panes.editor).

Dossiers et fichiers  
Le fichier [`omegat.project`](#project.folder.omegat.project.file).

Paramètres de préférences et propriétés du projet  
La préférence de [\#dialogs.preferences.fonts](#dialogs.preferences.fonts)

Chapitres, guides pratiques et annexes  
Le chapitre [\#chapter.project.folder](#chapter.project.folder).

Liens vers les ressources externes  
La [Documentation Regex Java](https://docs.oracle.com/en/java/javase/11/docs/api/java.base/java/util/regex/Pattern.html).

Raccourcis  
Pour éviter de répéter les descriptions des raccourcis, nous utilisons des lettres simples comme identifiant commun pour les modificateurs. Voir le chapitre [\#chapter.menus](#chapter.menus) pour en savoir plus.

Sous Windows et Linux : <span class="keycombo">Contrôle+E</span>

Sous macOS : <span class="keycombo">commande+E</span>

**Dans ce manuel  :**<span class="keycombo">C+E</span>

## Créer un nouveau projet

Si vous n’avez pas encore installé OmegaT, consultez le guide pratique [\#how.to.installing.omegat](#how.to.installing.omegat).

Pour apprendre à lancer d’OmegaT, consultez le guide pratique [\#how.to.running.omegat](#how.to.running.omegat).

Pour commencer à utiliser OmegaT, vous devez d’abord créer un projet qui contiendra tous vos fichiers.

Utilisez [\#menus.project](#menus.project)[\#menus.project.new](#menus.project.new) et sélectionnez un dossier vide ou créez-en un nouveau avec le nom de votre projet.

Un projet OmegaT est simplement un ensemble de dossiers contenant toutes les ressources par défaut.

La boite de dialogue [\#dialogs.project.properties](#dialogs.project.properties) s’ouvre une fois que vous avez nommé votre projet.

Dans cette boite de dialogue, sélectionnez ou saisissez les langues de vos fichiers source et à traduire, définissez les différentes options et cliquez sur OK pour continuer.

OmegaT fournit une liste brève et pratique de codes de langue à deux lettres, mais vous pouvez saisir n’importe quel code conforme au [BCP-47](https://www.rfc-editor.org/rfc/bcp/bcp47.txt) (y compris les codes de langue à trois lettres) dans le champ de saisie.

Assurez-vous que les bonnes langues sont saisies et que tous les autres emplacements nécessitant un code de langue correspondent au code que vous indiquez ici. Voir la section [\#dialogs.project.properties.languages](#dialogs.project.properties.languages) pour en savoir plus.

Utilisez [\#menus.project](#menus.project)[\#menus.project.properties](#menus.project.properties) pour revenir à cette boite de dialogue après avoir créé le projet.

Vous pouvez modifier la structure d’un projet à tout moment après avoir commencé à traduire. Dans la boite de dialogue, il suffit d’indiquer à OmegaT les nouveaux dossiers de ressources à utiliser. Il vous demandera alors de recharger le projet et commencera à utiliser les nouveaux emplacements.

Ensuite, la boite de dialogue [\#windows.source.files.list](#windows.source.files.list) s’ouvre.

Cliquez sur [\#windows.source.files.list.copy.files](#windows.source.files.list.copy.files) ou [\#windows.source.files.list.download.page](#windows.source.files.list.download.page) et ajoutez les fichiers source.

Utilisez [\#menus.project](#menus.project)[\#menus.project.access.project.contents](#menus.project.access.project.contents) si vous ne vous souvenez pas de l’emplacement de votre projet.

Si vous ne voyez pas le contenu d’un fichier dans le volet [\#panes.editor](#panes.editor), le fichier est peut-être vide ou dans un format qui n’est pas pris en charge par OmegaT. Utilisez [\#menus.options](#menus.options)[\#menus.options.file.filters](#menus.options.file.filters) pour afficher la liste des formats de fichiers pris en charge. Si le format de votre fichier n’est pas répertorié, utilisez des extensions tierces ou convertissez le fichier dans un format pris en charge. Voir le guide pratique [\#how.to.translate.other.files](#how.to.translate.other.files) pour en savoir plus.

## Dictionnaires de vérification orthographique

Omegat fournit un système de vérification orthographique, mais il n’inclut pas les dictionnaires nécessaires pour vérifier l’orthographe de vos traductions. Vous devez installer les dictionnaires dont vous avez besoin vous-même.

Utilisez la section [\#dialog.preferences.spellchecker](#dialog.preferences.spellchecker) du dialogue général [\#chapter.dialogs.preferences](#chapter.dialogs.preferences) pour accéder aux préférences de vérification orthographique.

1.  Cliquez sur le bouton [\#dialog.preferences.spellchecker.install.new](#dialog.preferences.spellchecker.install.new) pour afficher la liste des dictionnaires disponibles à l’URL indiquée dans le champ URL des dictionnaires de vérification orthographique téléchargeables situé au-dessus de ce bouton.

2.  Sélectionnez autant de dictionnaires que vous le souhaitez et cliquez sur le bouton Installer. OmegaT les téléchargera et les copiera dans l’emplacement des dictionnaires de vérification orthographique spécifié en haut de la boite de dialogue (le dossier [configuration](#configuration.folder) par défaut). Cette étape peut prendre un certain temps.

3.  Cliquez sur le bouton Fermer. OmegaT affichera une liste des dictionnaires installés.

OmegaT ne reconnait pas les langues automatiquement et n’utilise un dictionnaire que si son nom correspond au code de la langue cible.

Si la langue cible du projet est **fr** et que le nom du dictionnaire est **fr\_fr** ou **fr-fr**, vous pouvez soit :

-   utiliser [\#menus.project](#menus.project)[\#menus.project.properties](#menus.project.properties) pour changer la langue cible du projet en **fr-fr**, ou

-   utiliser [\#menus.options](#menus.options)[\#menus.options.access.configuration.folder](#menus.options.access.configuration.folder) pour accéder au dossier [configuration](#configuration.folder) et changer les noms des fichiers du dictionnaire en **fr**.

## Gérer vos segments

Le paramètre par défaut d’un projet de traduction consiste à créer des *phrases* en divisant les *blocs de paragraphes* trouvés dans le document. Voir la propriété du projet [\#dialogs.project.properties.options.segmentation](#dialogs.project.properties.options.segmentation) pour en savoir plus.

Les segments d’un paragraphe peuvent être segmentés davantage ou « non segmentés  » (fusionnés). Ajoutez une règle de segmentation pour les segmenter davantage, ou une règle d’exception pour les fusionner avec la partie dont ils ont été séparés. Voir l’annexe [\#app.segmentation](#app.segmentation) pour en savoir plus.

Le caractère espace standard est souvent utilisé comme limite de segment. Vous pouvez suivre les étapes ci-dessous pour fusionner deux sections de texte séparées par un caractère espace :

1.  Accédez au fichier source avec [\#menus.project](#menus.project)[\#menus.project.access.project.contents](#menus.project.access.project.contents).

2.  Trouvez l’emplacement de cette espace.

3.  Remplacez-la par une espace insécable.

4.  Enregistrez le fichier.

5.  Retournez sur OmegaT et utilisez [\#menus.project](#menus.project)[\#menus.project.reload](#menus.project.reload) pour qu’OmegaT reconnaisse le changement.

## Pour le plaisir des yeux !

Une fois que tout cela est fait, les fichiers sources apparaissent dans OmegaT comme ceci :

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

## Traduire vos fichiers

Saisissez votre traduction dans le volet [\#panes.editor](#panes.editor).

Pour découvrir à quel point vous pouvez être efficace avec les raccourcis, consultez la section [\#app.shortcuts.streamline.workflow](#app.shortcuts.streamline.workflow).

Après avoir saisi la traduction d’un segment, utilisez [\#menus.goto](#menus.goto)[\#menus.goto.next.untranslated.segment](#menus.goto.next.untranslated.segment) pour passer au segment suivant non traduit.

Lorsque vous quittez le segment, sa traduction est automatiquement enregistrée dans le fichier [\#project.folder.project.save.tmx](#project.folder.project.save.tmx) et servira de référence pour le reste de votre traduction.

Voir le menu [\#menus.goto](#menus.goto) pour plus d’options de navigation.

OmegaT n’associe pas aux segments traduits des statuts différents. Soit un segment est traduit, soit il ne l’est pas.

Si vous avez besoin d’un processus de révision spécifique, vous pouvez par exemple :

-   Ajouter des rappels dans le volet [\#panes.notes](#panes.notes) pour les segments problématiques

    Utilisez [\#menus.goto](#menus.goto)[\#menus.goto.notes.pane](#menus.goto.notes.pane) pour entrer dans le Bloc-note et ajouter votre remarque.

    Utilisez [\#menus.goto](#menus.goto)[\#menus.goto.editor.pane](#menus.goto.editor.pane) pour revenir à l’Éditeur et reprendre votre traduction.

-   Utilisez [\#menus.edit](#menus.edit)[\#menus.edit.search.project](#menus.edit.search.project) pour filtrer les segments sur la base des critères que vous avez définis, et n’examiner que ceux-là.

Utilisez [\#menus.edit](#menus.edit)[\#menus.edit.create.glossary.entry](#menus.edit.create.glossary.entry) pour ajouter des termes à votre glossaire.

Utilisez les préférences [\#menus.view](#menus.view)[\#menus.view.mark.glossary.matches](#menus.view.mark.glossary.matches) et [\#dialog.preferences.auto.completion](#dialog.preferences.auto.completion) pour gérer les correspondances avec le glossaire.

Lorsque vous saisissez un segment contenant des termes qui correspondent à des entrées de vos glossaires, ces termes et leurs traductions sont affichés dans le volet [\#panes.glossary](#panes.glossary).

Lorsque vous saisissez un segment qui correspond à une partie du contenu des mémoires de traduction du projet, OmegaT affiche les correspondances dans le volet [\#panes.fuzzy.matches](#panes.fuzzy.matches).

Le menu [\#menus.edit](#menus.edit) permet de gérer les correspondances de la mémoire de traduction et d’exécuter d’autres fonctions utiles.

La fonction [\#menus.edit.search.project](#menus.edit.search.project) vous permet de rechercher des termes, des morceaux de phrases, etc. dans l’ensemble du projet, en utilisant des recherches exactes, par mots-clés ou par expressions régulières. Vous pouvez également restreindre le champ de la recherche en fonction d’informations telles que l’auteur ou la date.

Vous pouvez également vous concentrer uniquement sur les résultats en les filtrant dans l’Éditeur. Voir la section [\#windows.text.search](#windows.text.search) pour en savoir plus.

Vous pouvez remplacer des termes avec la fonction [\#menus.edit.search.and.replace](#menus.edit.search.and.replace) en utilisant une boite de dialogue similaire. Voir la section [\#windows.text.replace](#windows.text.replace) pour en savoir plus.

Vous pouvez laisser des notes à vous-même ou aux membres de l’équipe dans le volet [\#panes.notes](#panes.notes) pendant que vous traduisez, et revenir aux segments annotés avec [\#menus.goto.next.note](#menus.goto.next.note) ou [\#menus.goto.previous.note](#menus.goto.previous.note) dans le menu [\#menus.goto](#menus.goto), ou à partir de la fenêtre [\#windows.text.search](#windows.text.search).

La touche [\#panes.editor.context.menu](#panes.editor.context.menu) permet d’accéder facilement à diverses fonctions fréquemment utilisées. Le [\#panes.editor.auto.completion.menu](#panes.editor.auto.completion.menu) est également disponible dans le volet de l’Éditeur.

## Gérer vos balises

Si les documents que vous traduisez utilisent du gras, de l’italique ou d’autres éléments décoratifs, OmegaT convertit ces éléments en balises qui entourent le texte décoré. Ces fichiers comprennent par exemple les fichiers LibreOffice, les fichiers HTML et les fichiers Microsoft Office. Les documents contiennent souvent aussi des balises qui n’ont rien à voir avec les décorations, mais qui sont néanmoins importantes dans les fichiers sources (et, par conséquent, dans les fichiers traduits).

Voici à quoi peut ressembler une phrase dans son format d’origine :

OmegaT est un programme **facile à utiliser** pour les traductaires *sagaces*.

Cependant, selon le format d’origine, OmegaT présentera cette phrase de manière similaire à ceci :

OmegaT est un programme `<t0/>`facile à utiliser`<t1/>` pour les traductaires `<t2/>`sagaces`<t3/>`.

Les différents paramètres liés aux balises peuvent être très utiles pour gérer correctement les balises dans un document. Pour en savoir plus, consultez les options et les scripts suivants :

-   [\#dialogs.project.properties.hide.tags](#dialogs.project.properties.hide.tags)

-   [\#dialogs.preferences.tag.processing](#dialogs.preferences.tag.processing)

-   [\#windows.scripts.distribution.tagwipe](#windows.scripts.distribution.tagwipe)

-   [\#windows.scripts.distribution.adapt.standard.tags](#windows.scripts.distribution.adapt.standard.tags)

-   [\#windows.scripts.distribution.strip.tags](#windows.scripts.distribution.strip.tags)

-   [\#windows.scripts.distribution.tag.free.match](#windows.scripts.distribution.tag.free.match)

Les balises dans OmegaT sont grisées, ce qui permet de les reconnaitre facilement. Elles sont protégées pour vous empêcher de modifier leur contenu, mais vous pouvez les supprimer, les saisir à la main ou les déplacer dans la phrase cible.

Utilisez [\#menus.edit](#menus.edit) [\#menus.edit.insert.missing.source.tag](#menus.edit.insert.missing.source.tag) et [\#menus.edit.insert.next.missing.tag](#menus.edit.insert.next.missing.tag) pour insérer les balises à l’emplacement indiqué par le curseur.

Vous pouvez définir des balises personnalisées qui seront gérées de la même manière. Voir la section [\#dialogs.preferences.tag.processing.regular.expressions.for.custom.tags](#dialogs.preferences.tag.processing.regular.expressions.for.custom.tags) pour en savoir plus.

Vous pouvez également définir des chaines de caractères qu’OmegaT devrait vous signaler si vous les laissez dans une traduction. Voir la section [\#dialogs.preferences.tag.processing.regular.expressions.for.fragments.that.should.be.removed.from.translation](#dialogs.preferences.tag.processing.regular.expressions.for.fragments.that.should.be.removed.from.translation) pour en savoir plus.

Si vous faites des erreurs lors de la gestion des balises, vos fichiers traduits risquent de ne pas s’ouvrir. Utilisez [\#menus.tools](#menus.tools) [\#menus.tools.check.issues](#menus.tools.check.issues) pour vérifier vos balises avant de générer vos fichiers traduits.

Si un fichier refuse de s’ouvrir dans LibreOffice, Word ou une autre application, cela est souvent dû à des erreurs dans la gestion des balises OmegaT. Retournez sur OmegaT, vérifiez que votre document ne contient pas de problèmes de balises et recréez le fichier traduit.

## Réviser votre traduction

N’hésitez pas à modifier la présentation des [\#chapter.panes](#chapter.panes) et les options [\#menus.view](#menus.view) lors de la révision de la traduction.

Utilisez l’option [\#menus.tools.check.issues](#menus.tools.check.issues) pour effectuer divers contrôles sur le contenu de votre traduction.

## Créer les fichiers traduits

Pour voir à quoi ressemblera votre traduction dans son format final, utilisez [\#menus.project](#menus.project) [\#menus.project.create.translated.documents](#menus.project.create.translated.documents).

Chaque fois que vous créez des fichiers traduits, tous les fichiers créés précédemment et portant le même nom sont écrasés. Pour éviter que les fichiers que vous créez ne soient écrasés, renommez-les. Vous pouvez automatiser les changements de nom de fichier en utilisant l’option [\#edit.filter.dialog](#edit.filter.dialog) pour le filtre de fichier.

Vos traductions sont *toujours* stockées dans le fichier [\#project.folder.project.save.tmx](#project.folder.project.save.tmx), qui est la mémoire de traduction du projet, situé dans le dossier [\#project.folder.omegat](#project.folder.omegat) de votre projet.

La suppression du contenu du dossier [\#project.folder.target](#project.folder.target) n’impacte *jamais* le contenu de vos traductions.

Les documents sont créés dans le dossier [\#project.folder.target](#project.folder.target) de votre projet. Les fichiers créés auparavant sont écrasés par le processus, sauf si vous les avez renommés…

Une fois les fichiers traduits créés, vous pouvez les ouvrir dans leur application d’origine pour vérifier leur contenu et les modifier. Ces modifications externes ne seront *pas* reflétées dans OmegaT.

Les modifications effectuées en dehors d’OmegaT peuvent être réinsérées dans OmegaT (et donc dans la mémoire de traduction du projet, pour la maintenir à jour). Soit en les introduisant manuellement dans les segments concernés, soit en alignant le fichier original et le fichier final traduit pour créer un nouveau fichier de mémoire de traduction (TMX) qui sera placé dans le dossier [\#project.folder.tm.enforce](#project.folder.tm.enforce) du dossier de votre projet. Voir la section [\#windows.aligner](#windows.aligner) pour en savoir plus.

## Gérer vos projets

-   Les projets de traduction ne sont que des dossiers contenant des fichiers. Vous pouvez créer un nouveau projet pour chaque nouveau travail ou ajouter de nouveaux fichiers sources à un projet existant à tout moment.

-   Vous pouvez accéder aux paramètres du projet et les modifier en utilisant [\#menus.project](#menus.project) [\#menus.project.properties](#menus.project.properties). Pour voir la liste des fichiers du projet, utilisez [\#menus.project.source.files.list](#menus.project.source.files.list) à partir du même menu. Vous pouvez accéder au contenu de toutes les ressources à tout moment avec l’option [\#menus.project.access.project.contents](#menus.project.access.project.contents).

-   Chaque fois que vous créez des fichiers traduits (voir [\#introduction.generate.the.translated.file](#introduction.generate.the.translated.file), ci-dessus), OmegaT crée trois mémoires de traduction qui contiennent l’état de la traduction des fichiers se trouvant actuellement dans le dossier [\#project.folder.source](#project.folder.source). Voir la section [\#dialogs.project.properties.file.locations.exported.tms](#dialogs.project.properties.file.locations.exported.tms) pour en savoir plus.

## Fluidifier le travail grâce aux raccourcis

Vous pouvez fluidifier votre travail en gardant à l’esprit les principaux raccourcis d’édition et de navigation (ou en les [modifiant en fonction de vos besoins](#app.shortcuts.customization)).

Un exemple illustre mieux ce point :

Imaginez que vous soyez chargé de traduire une version actualisée d’un manuel rédigé dans le cadre d’un précédent emploi. Voir le guide pratique [\#how.to.use.tm.reuse.tm](#how.to.use.tm.reuse.tm) pour en savoir plus.

Puisque les premières pages n’ont pas été modifiées, lorsque vous ouvrez le projet, vous êtes face à un écran rempli de segments déjà traduits à partir de la mémoire du travail précédent.

Plutôt que de faire défiler les pages jusqu’à ce que vous trouviez le premier segment à traduire, vous appuyez rapidement sur <span class="keycombo">C+U</span> pour [se mettre immédiatement à l’œuvre](#menus.goto.next.untranslated.segment) et commencer à traduire. (Et répétez l’opération chaque fois que vous atteignez une partie inchangée).

Quelques segments plus tard, vous tombez sur un terme que vous devriez ajouter au glossaire. Au lieu de prendre la souris, vous déverrouillez le curseur avec [F2](#panes.editor.cursor.lock), en utilisant les touches du curseur et les raccourcis standards du système pour naviguer jusqu’au terme et le sélectionner. Puis appuyez sur <span class="keycombo">C+S+G</span> pour afficher [la boite de dialogue de saisie du glossaire](#menus.edit.create.glossary.entry) et y insérer le terme source. Ensuite, vous retournez à l’éditeur, vous verrouillez à nouveau le curseur avec [F2](#panes.editor.cursor.lock) et vous répétez le même processus pour saisir le terme cible.

Vous avez activé la [saisie automatique](#dialog.preferences.auto.completion) pour afficher automatiquement non seulement les prédictions de l’historique, mais aussi les termes du glossaire et les chaines de caractères courtes prédéfinies, qui peuvent être saisies à l’aide d’une simple flèche de navigation.

Vous arrivez ensuite à une partie révisée du texte où le volet [\#panes.fuzzy.matches](#panes.fuzzy.matches) affiche un certain nombre de segments similaires tirés du travail précédent.

Après avoir rapidement appuyé sur <span class="keycombo">C+I</span> pour insérer la correspondance, vous effectuez les modifications nécessaires pour correspondre au texte révisé.

L’opération se poursuit avec parfois la combinaison <span class="keycombo">C+2</span> (ou un autre chiffre) suivie de <span class="keycombo">C+I</span> lorsque l’une des correspondances de 2 à 5 est plus appropriée.

Certains segments devront être modifiés ultérieurement, vous utilisez donc <span class="keycombo">C+A+9</span> pour entrer dans le volet Bloc-note, vous laissez une note et revenez dans le volet Éditeur avec <span class="keycombo">C+A+0</span>.

Lorsque vous arrivez à la fin de la partie, vous avez également utilisé <span class="keycombo">C+R</span> une ou deux fois pour remplacer des correspondances déjà saisies automatiquement dans la traduction précédente par de meilleures correspondances trouvées précédemment dans la partie traitée.

Plus tard, vous trouvez une meilleure façon de formuler une expression quelque peu épineuse rencontrée plus tôt, vous la sélectionnez donc dans le texte source, vous appuyez sur <span class="keycombo">C+F</span> [pour la trouver](#windows.text.search), puis vous utilisez <span class="keycombo">C+J</span> pour passer immédiatement à ce segment à partir de la boite de dialogue de recherche.

Puisqu’OmegaT a enregistré votre historique de navigation, il vous suffit d’utiliser <span class="keycombo">C+S+J</span> pour reprendre immédiatement là où vous vous étiez arrêté.

Vous décidez à présent de réviser les segments annotés. Vous utilisez <span class="keycombo">C+F</span> pour les trouver et, dans la fenêtre de recherche, vous utilisez <span class="keycombo">C+N</span> et <span class="keycombo">C+P</span> pour parcourir les résultats. OmegaT synchronise le contenu de l’Éditeur avec le résultat sélectionné, ce qui vous permet d’éditer les segments immédiatement.

Il est temps de faire une pause. Tout en dégustant votre café, vous réfléchissez à la facilité avec laquelle vous avez pu utiliser les différentes fonctions d’OmegaT par rapport à l’époque où vous veniez de commencer, lorsque vous passiez beaucoup de temps à parcourir les menus.

La fluidité du travail vous a permis de mieux vous concentrer sur la traduction elle-même.

En même temps, vous vous rendez compte que pendant votre session, vous avez utilisé le menu [\#menus.edit](#menus.edit)[\#menus.edit.create.alternative.translation](#menus.edit.create.alternative.translation) et les touches du curseur à plusieurs reprises, et vous décidez [d’ajouter un nouveau raccourci](#example.shortcut.addition) pour faciliter cette partie du processus également.

Apprendre les raccourcis des fonctions que vous utilisez souvent en vaut la peine.
