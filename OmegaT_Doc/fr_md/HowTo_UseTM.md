# Utiliser les mémoires de traduction

Lorsqu’un projet est créé, il comporte une mémoire de traduction vide, le fichier [\#project.folder.project.save.tmx.title](#project.folder.project.save.tmx.title), située dans le dossier [\#project.folder.omegat](#project.folder.omegat). Cette mémoire se remplit progressivement au fur et à mesure de l’avancement de la traduction.

Les traductions existantes sont utilisées pour accélérer le processus de traduction.

-   Si une phrase a déjà été traduite une fois, il n’est pas nécessaire de la retraduire. Voir les propriétés du projet [\#dialogs.project.properties.auto.propagation](#dialogs.project.properties.auto.propagation).

-   Si une ancienne traduction est similaire au contenu du segment sur lequel vous travaillez, vous pouvez la recycler dans votre traduction. Voir le volet [\#panes.fuzzy.matches](#panes.fuzzy.matches) pour en savoir plus.

-   Vous pouvez également utiliser des mémoires de traduction de référence en les plaçant dans le dossier [\#project.folder.tm](#project.folder.tm) de votre projet.

## Créer vos propres MT

Lorsque vous utilisez [\#menus.project](#menus.project)[\#menus.project.create.translated.documents](#menus.project.create.translated.documents) pour créer les documents cible d’un projet, OmegaT génère également trois mémoires de traduction qui reflètent l’état actuel de la traduction des fichiers du dossier source. Voir la propriété du projet [\#dialogs.project.properties.file.locations.exported.tms](#dialogs.project.properties.file.locations.exported.tms) pour en savoir plus.

Ces trois fichiers constituent chacun un fichier d’exportation bilingue du contenu actuel de votre traduction. Le contenu de ces fichiers provient de la mémoire du projet entier (le fichier [\#project.folder.project.save.tmx](#project.folder.project.save.tmx)) mais se *limite exclusivement* à ce que vous avez traduit jusqu’à présent.

Vous pouvez également utiliser l’outil [\#menus.tools](#menus.tools)[\#menus.tools.align.files](#menus.tools.align.files) pour créer une TMX à partir de deux fichiers au format pris en charge par OmegaT.

## Réutiliser les MT

Pour réutiliser les mémoires de traduction d’un projet précédent, il y a deux options :

-   Ouvrir l’ancien projet et placer les nouveaux fichiers source dans son dossier [\#project.folder.source](#project.folder.source).

    C’est la façon la plus simple de travailler sur la nouvelle version d’un document déjà traduit.

    Après le rechargement de l’ancien projet, sa mémoire de traduction sera appliquée aux nouveaux fichiers sources. Les segments identiques seront automatiquement traduits. Les segments similaires seront associés à des correspondances de la mémoire de traduction du projet au fur et à mesure que vous les saisissez.

-   L’autre option consiste à placer les mémoires de référence de l’ancien projet dans le dossier [\#project.folder.tm](#project.folder.tm) du nouveau projet.

    C’est la méthode à privilégier si vous souhaitez commencer votre traduction à partir de zéro.

    Selon la fiabilité de la mémoire, vous pouvez choisir de la placer dans l’un des sous-dossiers suivants :

    -   [\#project.folder.tm.enforce](#project.folder.tm.enforce),

    -   [\#project.folder.tm.auto](#project.folder.tm.auto),

    -   [\#project.folder.tm.penalty](#project.folder.tm.penalty),

    Les correspondances exactes provenant des sous-dossiers [\#project.folder.tm.enforce](#project.folder.tm.enforce) et [\#project.folder.tm.auto](#project.folder.tm.auto) seront automatiquement insérées dans la traduction, sans le préfixe ajouté par OmegaT lorsqu’il incorpore des correspondances au-delà d’un seuil prédéfini. Voir le paramètre [\#dialogs.preferences.editor.insert.the.best.fuzzy.match](#dialogs.preferences.editor.insert.the.best.fuzzy.match) pour en savoir plus.

    Activez l’option [\#dialogs.preferences.editor.save.auto-populated.status](#dialogs.preferences.editor.save.auto-populated.status) pour qu’OmegaT se souvienne que les correspondances insérées proviennent de ces dossiers.

    Utilisez les menus de navigation qui se trouvent dans [\#menus.goto](#menus.goto)[\#menus.goto.auto.populated.segments](#menus.goto.auto.populated.segments) pour atteindre un segment inséré automatiquement.

-   Pour les traductions de référence, OmegaT prend également en charge les documents bilingues qui ne sont pas des fichiers TMX. Les formats de fichiers pris en charge par OmegaT correspondent à tous les formats bilingues qu’OmegaT accepte comme fichiers source :

    -   Fichiers PO

    -   Fichiers TXML

    -   Fichiers XLIFF

    -   Fichiers SDLXLIFF

    Vous pouvez ajouter ces fichiers au dossier [\#project.folder.tm](#project.folder.tm) de votre projet ou à l’un de ses sous-dossiers, et les données traduites seront immédiatement disponibles pour la correspondance.

### Lire les MT d’autres outils

OmegaT peut lire des mémoires conformes à la norme TMX créées par d’autres outils.

Certains outils produisent des fichiers TMX non valides sous certaines conditions. Vous devez les corriger si vous souhaitez les utiliser comme mémoires de référence, sinon OmegaT signalera une erreur et ne pourra pas les ouvrir. En général, ces corrections sont simples, et le message d’erreur d’OmegaT vous aidera à identifier l’erreur. En cas de problème, vous pouvez également demander conseil au groupe de soutien.

### Gérer vos MT

Vous pouvez conserver les mémoires de traduction dans des dossiers distincts, par client ou par domaine de spécialisation, afin de pouvoir les réutiliser rapidement si nécessaire. Tout dossier modifiable peut être utilisé à la place du dossier [\#project.folder.tm](#project.folder.tm) du projet. Voir la section [\#dialogs.project.properties.file.locations](#dialogs.project.properties.file.locations) de la boite de dialogue des propriétés du projet.

### Créer une MT propre aux documents sélectionnés

Dans les cas où vous devez partager une TMX contenant uniquement le texte de certains fichiers et excluant tout autre contenu, suivez la procédure ci-dessous :

-   Copiez uniquement les documents dont vous souhaitez inclure le contenu dans le dossier `source` de votre projet.

-   Ouvrez le projet.

-   Utilisez [\#menus.goto](#menus.goto)[\#menus.goto.next.untranslated.segment](#menus.goto.next.untranslated.segment) pour trouver les segments non traduits (et les traduire, si nécessaire).

-   Utilisez [\#menus.tools](#menus.tools)[\#menus.tools.check.issues](#menus.tools.check.issues) pour détecter d’éventuels problèmes.

-   Utilisez [\#menus.project](#menus.project)[\#menus.project.create.translated.documents](#menus.project.create.translated.documents) pour créer les fichiers TMX correspondants au contenu actuel.

Les fichiers TMX situés dans le dossier de la mémoire de traduction exportée contiennent désormais uniquement le texte original et le texte traduit des fichiers que vous avez copiés dans le dossier source, dans la paire de langues choisie. Voir la propriété du projet [\#dialogs.project.properties.file.locations.exported.tms](#dialogs.project.properties.file.locations.exported.tms) pour en savoir plus.

## Partager les MT

Pour les travaux conséquents impliquant une équipe de traductaires, il est plus facile pour les personnes impliquées de partager des mémoires de traduction communes plutôt que de s’échanger leurs versions locales.

Il y a deux manières de partager les mémoires de traduction :

La méthode « suffisamment bonne »  
Voir la section [\#how.to.use.tm.create.your.tm](#how.to.use.tm.create.your.tm) ci-dessus.

Si vous écrivez le fichier TMX dans un dossier sur un disque partagé, vous pouvez demander à votre collègue de désigner ce dossier comme dossier [\#project.folder.tm](#project.folder.tm) pour la traduction en cours.

Réciproquement, vous pouvez demander à votre collègue d’écrire les fichiers TMX du projet dans un dossier sur un disque partagé que vous désignerez comme votre dossier [\#project.folder.tm](#project.folder.tm) pour la traduction en cours.

OmegaT reconnait instantanément les modifications apportées aux fichiers TMX. Par conséquent, chaque fois qu’une personne crée ou modifie une TMX en utilisant [\#menus.project](#menus.project)[\#menus.project.create.translated.documents](#menus.project.create.translated.documents), l’autre personne n’a rien à faire pour que cette TMX soit reconnue localement.

Cette méthode fonctionne également pour le partage de glossaires lorsque le glossaire modifiable du projet (avec un nom différent de celui par défaut pour éviter d’écraser le fichier) est situé dans un dossier de glossaire partagé. Voir l’annexe [\#app.glossaries](#app.glossaries) pour en savoir plus.

Cette méthode de partage fonctionne bien lorsque le décalage entre les mises à jour de la TMX n’a pas une grande importance : par exemple, si les données peuvent être envoyées à la révision seulement quelques fois par jour.

L’approche technique  
OmegaT utilise des logiciels de gestion de version collaboratifs pour partager les données.

Ces systèmes sont libres (utilisation, installation et gestion) et sont utilisés à grande échelle dans le monde du développement informatique, ce qui les rend extrêmement robustes.

Voir le guide pratique [\#how.to.setup.team.project](#how.to.setup.team.project) pour en savoir plus.

Faites preuve de prudence lorsque vous placez un projet entier dans un système de partage de fichiers tel que DropBox, OneCloud et autre.

*Ces systèmes ne sont pas conçus pour suivre les modifications internes d’un fichier donné.*

Un projet OmegaT est un ensemble complexe de fichiers. De tels systèmes ne sont pas toujours en mesure de fournir la version la plus récente de vos données, et peuvent même bloquer certains fichiers sans raison apparente, voire corrompre des fichiers liés à des projets d’équipe.

Assurez-vous d’avoir correctement testé l’agencement de votre projet et réalisé une sauvegarde séparées de vos données avant de les partager dans ce type de système.

## Faire le lien entre deux langues

OmegaT affiche les correspondances partielles dans le volet [\#panes.fuzzy.matches](#panes.fuzzy.matches). Par défaut, ces correspondances sont limitées aux langues source et cible définies dans la boite de dialogue [\#dialogs.project.properties](#dialogs.project.properties).

Vous pouvez ajouter des correspondances dans des langues qui ne sont pas la langue cible. Voir le paramètre [\#dialog.preferences.tm.matches.other.languages](#dialog.preferences.tm.matches.other.languages) pour en savoir plus.

Si vous avez une TMX qui correspond à votre document source et qui contient sa traduction dans une autre langue, vous pouvez également afficher cette langue *juste en dessous* du segment source pour l’utiliser comme langue de référence supplémentaire.

Pour appliquer cette option, il faut :

1.  Copier la mémoire de traduction qui contient la langue de référence supplémentaire dans le sous-dossier `tmx2source` qui se trouve dans le dossier [\#project.folder.tm](#project.folder.tm).

2.  Renommer le fichier TMX de la manière suivante :

    -   `LL_PP.tmx`,

    -   `LL-PP.tmx`, ou

    -   `LL.tmx`,

    où *LL* est le code interne de la langue que vous voulez afficher comme référence et *PP* est un code arbitraire à 2 lettres.

    -   Toutes les lettres doivent être en majuscule.

    -   Seuls les segments qui correspondent **exactement** à la source sont affichés.

Si vous avez une TMX qui contient la traduction japonaise d’un document anglais que vous traduisez vers le français, par exemple, vous pouvez utiliser la traduction japonaise en tant que référence alternative exacte en l’affichant sous le texte anglais à traduire.

Il vous suffit de mettre le fichier TMX anglais-japonais dans `tm/tmx2source` sous le nom `JA-JP.tmx`. OmegaT va maintenant afficher le texte japonais correspondant au segment source anglais :

    — ¶ —————————————————————
    A whitespace character: [ \t\n\x0B\f\r]
    ja-JP: 空白文字：[ \t\n\x0B\f\r]
    Un caractère d’espacement : [ \t\n\r\f\x0B]<segment 3075 ¶>
    — ¶ —————————————————————

La première ligne est l’original anglais, la seconde est la langue de raccord (japonais), que vous avez jugée utile à votre travail de traduction, et la troisième correspond à l’état actuel de la traduction en français.

Vous pouvez utiliser autant de fichiers TMX contenant autant de paires de langues de raccord différentes que vous le souhaitez.
