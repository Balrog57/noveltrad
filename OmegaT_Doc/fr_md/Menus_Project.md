# Projet

Ce menu vous permet d’accéder aux commandes de gestion de projet.

Sur Windows et Linux : <span class="keycombo">Ctrl+Maj+N</span>

Sous macOS : <span class="keycombo">Maj+commande+N</span>

**Dans ce manuel :** <span class="keycombo">C+Maj+N</span>

Nouveau <span class="keycombo">C+Maj+N</span>  
Crée et ouvre un nouveau projet. Voir la section [\#introduction.create.and.open.new.project](#introduction.create.and.open.new.project) pour en savoir plus.

Télécharger projet en équipe…  
Crée une copie locale d’un projet distant OmegaT. Voir le guide pratique [\#how.to.use.team.project](#how.to.use.team.project) pour en savoir plus.

Ouvrir… <span class="keycombo">C+O</span>  
Ouvre un projet préexistant.

Ouvert récemment…  
Donne accès aux dix derniers projets modifiés. Cliquer sur l’un d’entre eux enregistrera votre projet actuel, le fermera et ouvrira le projet sélectionné.

Utiliser la fonction Effacer le menu pour supprimer la liste des projets récents.

Recharger <span class="keycombo">F5</span>  
Recharge le projet pour prendre en compte les changements extérieurs affectant les fichiers sources et les paramètres du projet.

Les nouvelles mémoires de traduction placées dans le dossier [\#project.folder.tm](#project.folder.tm) pendant la traduction sont automatiquement prises en compte dès que le curseur bouge d’un segment à un autre. De la même manière, le contenu du dossier [\#project.folder.glossary](#project.folder.glossary) est automatiquement reconnu et ne nécessite pas de recharger le projet.

Lorsqu’un projet en équipe est rechargé, OmegaT recharge les propriétés distantes, plutôt que locales.

Fermer <span class="keycombo">C+Maj+W</span>  
Enregistre la mémoire de traduction du projet ([\#project.folder.project.save.tmx](#project.folder.project.save.tmx)) et ferme le projet.

Enregistrer <span class="keycombo">C+S</span>  
Enregistre la mémoire de traduction du projet ([\#project.folder.project.save.tmx](#project.folder.project.save.tmx)) et synchronise les projets en équipe.

OmegaT enregistre automatiquement les traductions toutes les trois minutes, ainsi que lorsque vous fermez le projet ou quittez le logiciel. Voir le paramètre [\#dialog.preferences.saving.and.output.interval](#dialog.preferences.saving.and.output.interval) pour en savoir plus.

Ajouter des fichiers…  
Copie les fichiers sélectionnés au dossier [\#project.folder.source](#project.folder.source) et recharge le projet pour prendre en compte les nouveaux fichiers.

Ajouter une page MediaWiki…  
Ouvre une boite de dialogue où vous pouvez coller l’URL de la page MediaWiki que vous souhaitez traduire. Les données source de la page seront copiées dans le dossier [\#project.folder.source](#project.folder.source), en tant que fichier texte, avec l’extension `.utf8`.

Envoyer les fichiers source  
Cette fonction est spécifique aux projets en équipe. *Seul le responsable du projet en équipe devrait utiliser cette fonction*. Voir le guide pratique [\#how.to.use.team.project](#how.to.use.team.project) pour en savoir plus.

Envoie les fichiers ajoutés ou modifiés localement à partir du dossier `source` au dépôt du projet en équipe.

Envoyer les fichiers cible  
Cette fonction est spécifique aux projets en équipe. *N’utilisez cette fonction que si le responsable du projet en équipe vous l’a demandé*. Voir le guide pratique [\#how.to.use.team.project](#how.to.use.team.project) pour en savoir plus.

Envoie les fichiers traduits créés localement à partir du dossier [\#project.folder.target](#project.folder.target) au dépôt du projet en équipe.

Créer les documents traduits <span class="keycombo">C+D</span>  
Crée les fichiers cible sur la base de votre traduction. Les fichiers cible créés sont situés dans le dossier [\#project.folder.target](#project.folder.target).

Vous pouvez empêcher la création de fichiers cibles s’il y a des problèmes de balises. Voir le paramètre [\#dialogs.preferences.tag.processing.do.not.allow.creating.translated.documents.with.tag.issues](#dialogs.preferences.tag.processing.do.not.allow.creating.translated.documents.with.tag.issues) pour en savoir plus.

Chaque fois que vous créez des fichiers traduits, OmegaT enregistre le projet (voir l’élément de menu [\#menus.project.save](#menus.project.save) plus haut) et crée des mémoires de traduction de référence qui contiennent les segments traduits de l’ensemble de fichiers source actuel.

Créer le document actuel traduit <span class="keycombo">C+Maj+D</span>  
Crée le fichier cible qui correspond au fichier source actuellement en traduction. Le fichier créé se trouve dans le dossier [\#project.folder.target](#project.folder.target).

Chaque fois que vous créez le fichier actuel traduit, OmegaT enregistre le projet (voir l’élément de menu [\#menus.project.save](#menus.project.save) plus haut) et crée des mémoires de traduction de référence qui contiennent les segments traduits de l’ensemble de fichiers source actuel.

Ouvrir un projet MED…  
Ouvre un projet empaqueté au format MED défini par la direction générale de la traduction de l’Union européenne.

Créer projet MED…  
Permet de transformer le projet en paquet MED.

Propriétés… <span class="keycombo">C+E</span>  
Affiche la boite de dialogue [\#dialogs.project.properties](#dialogs.project.properties) pour modifier les langues du projet les emplacements des dossiers.

Fichiers du projet… <span class="keycombo">C+L</span>  
Ouvre la fenêtre [\#windows.source.files.list](#windows.source.files.list).

Accéder au contenu du projet  
Donne accès aux différents dossiers du projet. Voir le chapitre [\#chapter.project.folder](#chapter.project.folder) pour en savoir plus.

De plus, il y a trois entrées de menu qui ouvrent directement les fichiers source ou cible actuels, ou le glossaire modifiable. Les fichiers sont ouverts dans l’application par défaut définie par le système d’exploitation. Les options sont grisées si les fichiers n’existent pas.

[Racine du projet](#chapter.project.folder)  
Ouvre le dossier dans votre gestionnaire de fichiers par défaut.

[Dictionnaires](#project.folder.dictionary)  
Ouvre le dossier dans votre gestionnaire de fichiers par défaut.

[Glossaires](#project.folder.glossary)  
Ouvre le dossier dans votre gestionnaire de fichiers par défaut.

[Fichiers source](#project.folder.source)  
Ouvre le dossier dans votre gestionnaire de fichiers par défaut.

[Fichiers cible](#project.folder.target)  
Ouvre le dossier dans votre gestionnaire de fichiers par défaut.

[Mémoires de traduction](#project.folder.tm)  
Ouvre le dossier dans votre gestionnaire de fichiers par défaut.

[Mémoires exportées](#project.folder.exported.tm)  
Ouvre le dossier dans votre gestionnaire de fichiers par défaut.

Fichier source actuel  
Le fichier source actuel est situé dans le dossier [\#project.folder.source](#project.folder.source).

Ouvre le fichier dans l’application associée.

Fichier cible actuel  
Le fichier cible actuel est situé dans le dossier [\#project.folder.target](#project.folder.target).

Ouvre le fichier, s’il existe, dans l’application associée.

Glossaire modifiable  
Le glossaire modifiable est situé dans le dossier [\#project.folder.glossary](#project.folder.glossary).

Ouvre le fichier, s’il existe, dans l’application associée.

Redémarrer  
Enregistre le projet et redémarre OmegaT. Il vous est demandé de confirmer si vous souhaitez réellement quitter si vous n’avez pas encore enregistré votre projet.

Quitter <span class="keycombo">C+Q</span>  
Enregistre le projet et ferme OmegaT. Il vous est demandé de confirmer si vous souhaitez réellement quitter si vous n’avez pas encore enregistré votre projet.

Sur macOS, cet élément de menu se trouve dans le menu OmegaT.
