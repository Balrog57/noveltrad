# Résoudre les problèmes

OmegaT est une application robuste et fiable, mais il est tout de même recommandé de l’utiliser en prenant quelques précautions pour éviter la perte de données, comme pour n’importe quelle autre application.

## Sauvegardes automatiques

OmegaT crée des sauvegardes des paramètres de votre projet afin de pouvoir les récupérer en cas de problème. Voir la section [\#project.folder.omegat.project.file](#project.folder.omegat.project.file) pour en savoir plus.

OmegaT enregistre régulièrement et automatiquement toute votre progression dans le fichier [\#project.folder.project.save.tmx](#project.folder.project.save.tmx), situé dans le dossier [\#project.folder.omegat](#project.folder.omegat) du projet. OmegaT crée également des sauvegardes régulières de ce fichier.

1.  Lorsque vous ouvrez un projet, OmegaT sauvegarde le fichier `project_save.tmx` dans un fichier de sauvegarde horodaté.

    OmegaT conserve jusqu’à dix de ces fichiers.

    Le nom du fichier de sauvegarde suit le modèle `projet_save.tmx.AAAAMMJJhhmm.bak`, dans lequel `AAAA` correspond aux 4 chiffres de l’année, `MM` au mois, `JJ` au jour, et `hh` et `mm` indiquent les heures et les minutes.

2.  À chaque modification du fichier `project_save.tmx` :

    -   soit lorsque vous enregistrez les données du projet (utiliser [\#menus.project](#menus.project)[\#menus.project.save](#menus.project.save)),

    -   soit lors d’un enregistrement régulier (toutes les 3 minutes par défaut),

    OmegaT crée un fichier de sauvegarde nommé `projet_save.tmx.bak`.

    Ce fichier est une copie de `project_save.tmx` *avant* sa modification.

3.  Chaque fois que vous enregistrez les données du projet (en utilisant [\#menus.project](#menus.project)[\#menus.project.save](#menus.project.save)), ou lors d’une sauvegarde régulière, OmegaT enregistre l’état le plus récent de la traduction dans `project_save.tmx`.

Le fichier `project_save.tmx` contient toujours les données les plus récentes.

Vous pouvez modifier la fréquence des enregistrements dans la rubrique [\#dialogs.preferences.saving.and.output](#dialogs.preferences.saving.and.output) des préférences.

## Vous avez perdu votre traduction

Même si vous craignez d’avoir perdu des données de traduction, elles sont surement stockées en toute sécurité dans la mémoire de sauvegarde la plus récente, qui n’a généralement pas plus de quelques minutes.

Procédez comme suit :

1.  Fermez le projet pour éviter toute modification de l’état des fichiers de sauvegarde.

2.  Renommez le fichier actuel `projet_save.tmx` (en `projet_save.tmx.tmp`, par exemple).

3.  Choisissez la sauvegarde de la mémoire de traduction la plus susceptible de contenir les données recherchées.

4.  Renommez-la en `project_save.tmx`.

5.  Rouvrez le projet.

Cette procédure permet de restaurer la traduction dans l’état dans lequel elle se trouvait au moment où la sauvegarde choisie a été créée. Vous pouvez répéter cette opération autant de fois que nécessaire pour trouver des sauvegardes plus anciennes. Pensez à conserver en lieu sûr tous les différents fichiers que vous renommez pour éventuellement les réutiliser. N’oubliez pas qu’il ne faut pas modifier la configuration du projet ou ajouter des fichiers TMX entretemps, car ces actions peuvent créer des obstacles à l’aboutissement de la procédure.

La prudence est de mise si vous voulez modifier les fichiers du dossier source, les règles de segmentation ou les filtres de fichiers au cours d’un projet. Modifier l’un de ces éléments après avoir commencé votre traduction peut provoquer la disparition ou l’apparition inopinée de certains segments.

## Votre projet est verrouillé

Dans le cas exceptionnel où votre ordinateur plante et où OmegaT n’a pas eu le temps de se fermer correctement, le système d’exploitation peut verrouiller le fichier `omegat.project` et vous empêcher de le rouvrir après le redémarrage de l’ordinateur.

Procédez comme suit :

1.  Identifiez le dossier du projet qu’OmegaT refuse d’ouvrir et ouvrez-le dans votre gestionnaire de fichiers. Le contenu du dossier doit être similaire à celui d’un dossier [projet](#chapter.project.folder) standard.

2.  Dans ce dossier, vous devriez trouver un fichier `omegat.project` ainsi qu’un fichier `omegat.project.bak`. Assurez-vous que les fichiers sont identiques.

3.  Renommez le fichier `omegat.project` (en `omegat.project.locked` par exemple).

4.  Renommez le fichier `omegat.project.bak` en `omegat.project`.

5.  Ouvrez le projet.

Cette procédure permet d’ouvrir le projet avec le fichier de sauvegarde `omegat.project` créé automatiquement.

## Votre projet ne s’ouvre pas

Dans le cas exceptionnel où votre ordinateur plante et où OmegaT n’a pas eu le temps de se fermer correctement, certains fichiers importants peuvent être corrompus et empêcher la réouverture du projet après le redémarrage de votre système.

Procédez comme suit :

1.  Créez un nouveau projet avec les mêmes paramètres.

2.  Copiez le contenu de vos différents dossiers à l’emplacement équivalent dans le nouveau projet (fichiers source, fichiers de mémoire de traduction de référence, fichiers de glossaire).

3.  Dans l’ancien projet, choisissez le fichier de mémoire de traduction (principal ou de sauvegarde) qui contient le plus probablement les données que vous recherchez.

4.  Renommez-le en `projet_save.tmx` si nécessaire.

5.  Copiez-le dans le dossier `omegat/` de votre nouveau projet.

6.  Ouvrez le nouveau projet.

Cette procédure permet d’utiliser la mémoire de traduction que vous avez choisie dans l’ancien projet pour récupérer l’état de votre traduction dans le nouveau projet.

## Votre fichier traduit ne s’ouvre pas

Très souvent, les fichiers de suites bureautiques contiennent des balises qui doivent être copiées dans la traduction pour que le fichier traduit puisse être ouvert dans l’application d’origine. Dans certains cas, les balises manquantes empêchent l’ouverture du fichier.

Procédez comme suit :

1.  Ouvrez le projet dans OmegaT.

2.  Utilisez [\#menus.tools](#menus.tools)[\#menus.tools.check.issues](#menus.tools.check.issues) et ciblez les Problèmes de balises.

3.  Corrigez tous les problèmes de balises trouvés dans vos documents.

4.  Utilisez [\#menus.project](#menus.project)[\#menus.project.create.translated.documents](#menus.project.create.translated.documents) pour recréer les documents.

5.  Rouvrez les documents dans l’application d’origine.

Cette procédure permet de résoudre les problèmes de cohérence interne des balises dus à une mauvaise insertion des balises lors de la saisie de la traduction dans OmegaT.

## OmegaT ne fonctionne pas correctement

Quelque chose s’est produit et OmegaT ne fonctionne plus correctement. Vous avez tout essayé et ne parvenez pas à résoudre le problème. Avant d’appeler à l’aide, tentez une dernière manipulation : redémarrez OmegaT avec les paramètres par défaut.

Procédez comme suit :

1.  Utilisez [\#menus.options](#menus.options)[\#menus.options.access.configuration.folder](#menus.options.access.configuration.folder) pour accéder au dossier de configuration.

    Si vous ne pouvez pas entrer dans les menus d’OmegaT, consultez le chapitre [\#configuration.folder](#configuration.folder) pour connaitre l’emplacement du dossier de configuration.

2.  Fermez OmegaT.

3.  Faites une sauvegarde du contenu et supprimez le dossier d’origine.

4.  Redémarrez OmegaT.

    Si OmegaT ne fonctionne toujours pas comme prévu, n’hésitez pas à nous contacter pour obtenir de l’aide.

5.  Fermez OmegaT.

6.  Copiez *un* des anciens fichiers dans le nouveau dossier de configuration.

7.  Redémarrez OmegaT.

    Si OmegaT ne fonctionne toujours pas comme prévu, cela signifie que vous avez identifié le fichier défectueux. Supprimez-le du dossier de configuration, redémarrez OmegaT et poursuivez votre travail.

8.  Revenez à l’étape 5. ci-dessus et continuez jusqu’à résoudre le problème.

## Résumé

-   Pour éviter de perdre des données importantes, faites des copies régulières du fichier `/omegat/project_save.tmx` sur un support de sauvegarde tel qu’une clé USB, un disque dur externe ou un service de stockage dans le nuage.

-   Entrainez-vous régulièrement à appliquer des « mesures d’urgence  » telles que la récupération de traductions d’un projet, de manière à éviter de perdre trop de temps le jour où vous aurez besoin de ces compétences.
