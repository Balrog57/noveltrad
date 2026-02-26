# Fichiers source

Cette fenêtre s’affiche automatiquement lors du chargement d’un projet par OmegaT et peut être consultée à tout moment via [\#menus.project](#menus.project)[\#menus.project.source.files.list](#menus.project.source.files.list).

La fenêtre affiche les informations suivantes :

-   Dans le titre de la fenêtre : le nombre total de fichiers traduisibles dans le projet.

    Il s’agit des fichiers présents dans le dossier [\#project.folder.source](#project.folder.source) dans un format reconnu par OmegaT.

-   Sous forme de liste : tous les fichiers traduisibles du projet.

    En cliquant sur un fichier, celui-ci s’ouvre dans le volet [\#panes.editor](#panes.editor) pour être traduit.

-   Chaque ligne indique le nom du fichier, le type de filtre, l’encodage et le nombre de segments qu’il contient.

-   Le nombre total de segments, le nombre de segments uniques dans l’ensemble du projet et le nombre de segments uniques déjà traduits sont affichés en bas de la fenêtre.

En tapant du texte, un champ Filtre s'ouvre en bas de la fenêtre dans lequel les noms de fichiers peuvent être saisis. Vous pouvez utiliser les flèches pour sélectionner un fichier et appuyer sur Entrée pour l’ouvrir afin de le traduire.

Les noms de fichiers (première colonne) peuvent être triés par ordre alphabétique en cliquant sur l’entête. Vous pouvez modifier la position d’un fichier en le sélectionnant et en cliquant sur l’un des boutons Glisser… à droite.

Un clic droit sur un nom de fichier fait apparaitre un menu contextuel qui vous permet d’ouvrir le fichier source ou le fichier cible (s’il existe).

Le nombre de segments **Uniques** est calculé en retirant le nombre de segments répétés du nombre total de segments.

La différence entre le « Nombre total de segments » et le « Nombre de segments uniques » donne une idée approximative du nombre de répétitions présentes dans le texte. Utilisez [\#menus.tools](#menus.tools)[\#menus.tools.statistics](#menus.tools.statistics) pour plus d’informations.

Modifier les règles de segmentation peut changer le nombre de segments/segments uniques. Toutefois, il est généralement préférable d’éviter de le faire une fois que vous avez commencé à traduire le projet. Voir l’annexe [\#app.segmentation](#app.segmentation) pour en savoir plus.

Les boutons situés en bas de la fenêtre permettent d’ajouter des fichiers à votre projet  :

Ajouter des fichiers…  
Copie les fichiers sélectionnés au dossier [\#project.folder.source](#project.folder.source) et recharge le projet pour prendre en compte les nouveaux fichiers.

Ajouter une page MediaWiki…  
Demande la saisie l’URL d’une page et la télécharge dans le dossier [\#project.folder.source](#project.folder.source).

Les deux actions sont équivalentes à l’utilisation des éléments de menu [\#menus.project](#menus.project)[\#menus.project.copy.files.to.source.folder](#menus.project.copy.files.to.source.folder) et [\#menus.project](#menus.project)[\#menus.project.download.mediawiki.page](#menus.project.download.mediawiki.page).

Vous pouvez éditer manuellement le fichier de configuration [\#configuration.folder.default.contents.omegat.prefs](#configuration.folder.default.contents.omegat.prefs) pour que la fenêtre de la liste des fichiers source ne s’ouvre pas automatiquement lors du chargement d’un projet.
