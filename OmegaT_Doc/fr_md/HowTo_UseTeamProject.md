# Utiliser un projet en équipe

Les projets en équipe emploient des mécanismes de synchronisation entre les membres du projet.

Lorsque le projet en équipe OmegaT est installé sur un serveur, l’administrateur envoie aux membres les informations nécessaires pour y accéder ; soit une URL qui indique l’emplacement du projet, soit un fichier `omegat.project`.

Une fois le projet téléchargé, il est installé localement et il suffit de l’ouvrir localement pour le synchroniser avec le serveur.

Les identifiants de dépôt sont entreposés dans le fichier [\#configuration.folder.extra.contents.repositories](#configuration.folder.extra.contents.repositories) et peuvent être effacés à partir des préférences [\#dialog.preferences.team.title.repository.credentials](#dialog.preferences.team.title.repository.credentials).

Puisque la synchronisation se fait par défaut toutes les trois minutes, il arrive que des membres du projet traduisent ou modifient un segment qui a déjà été traduit par un autre membre, mais qui n’a pas encore été synchronisé. Dans une telle situation, les membres devront choisir la traduction appropriée.

Les membres peuvent se relayer afin de traduire et réviser les fichiers. La fonction de Recherche leur permet de filtrer le volet Éditeur pour afficher le contenu traduit par une personne spécifique, ou pour afficher le contenu traduit après ou avant une date spécifique, par exemple.

Télécharger le projet  
1.  Depuis une URL

    Utilisez [\#menus.project](#menus.project)[\#menus.project.download.team.project](#menus.project.download.team.project) pour afficher la boite de dialogue Télécharger projet en équipe.

    Entrez l’URL fournie par l’administrateur du projet en équipe dans le champ URL du dépôt en haut de la boite de dialogue et sélectionnez un dossier pour le projet dans le champ Nouveau dossier du projet local. Laissez l’option Branche par défaut cochée sauf si l’administrateur du projet a fourni des instructions pour utiliser une branche spécifique.

2.  Depuis un fichier `omegat.project`

    Mettez le fichier `omegat.project` dans un dossier vide, et ouvrez-le dans OmegaT. Le projet sera automatiquement téléchargé dans le dossier contenant ce fichier.

Les serveurs utilisent généralement deux types d’authentification principaux : la saisie d’un *identifiant/mot de passe* ou *SSH*.

Si le serveur recourt à une authentification par identifiant/mot de passe, OmegaT vous présentera une boite de dialogue Authentification afin d’entrer votre identifiant et votre mot de passe, soit lors du téléchargement initial du projet, soit plus tard dans le processus. OmegaT se souviendra alors de vos informations d’identification pour ce projet spécifique sauf si vous les supprimez formellement. Voir les préférences [\#dialog.preferences.team.title.repository.credentials](#dialog.preferences.team.title.repository.credentials) pour en savoir plus.

Si le serveur utilise une authentification SSH, veillez à mettre à jour votre configuration SSH afin d’inclure ce serveur avant d’essayer de télécharger le projet, sinon vous rencontrerez une erreur d’authentification et le chargement du projet échouera.

Si vous utilisez plusieurs projets sur un même serveur, les informations d’identification ne seront demandées qu’une fois pour ce serveur.

Synchronisation  
La synchronisation du projet intègre les traductions effectuées par tous les membres de l’équipe dans les copies locales du projet. Seul le contenu des deux fichiers suivants est synchronisé :

-   `project.save`

-   `glossary.txt`

Pendant la synchronisation, tous les autres fichiers locaux sont remplacés par les versions du serveur distant, à l’exception de `omegat.project` (voir ci-dessous).

OmegaT synchronise un projet en équipe lorsqu’il est ouvert, rechargé, fermé ou enregistré. Cela signifie que la fonctionnalité d’enregistrement automatique synchronise aussi régulièrement les versions locales avec la version sur le serveur aux intervalles spécifiés dans la préférence [\#dialog.preferences.saving.and.output.interval](#dialog.preferences.saving.and.output.interval).

Configuration du projet en équipe  
Comme pour les projets locaux classiques, la configuration du projet en équipe est définie par le contenu du fichier `omegat.project` et par l’utilisation facultative de fichiers spéciaux pour les filtres ou les règles de segmentation spécifiques au projet.

Lors du premier téléchargement du projet, OmegaT récupère le fichier `omegat.project` à partir du serveur. Ce fichier définit les paramètres suivants :

-   *Configuration de base du projet :* la source et les langues, les lemmatiseurs, la hiérarchie des dossiers du projet.

    Dans un projet en équipe, les paramètres de configuration de base du projet local sont toujours remplacés par la configuration présente sur le serveur, définie à l’origine par l’administrateur du projet.

-   *Mise en correspondance des dépôts*

    Voir le guide pratique [\#how.to.setup.team.project.mapping.parameters](#how.to.setup.team.project.mapping.parameters) pour en savoir plus.

    -   Si aucune mise en correspondance personnalisée n’a été définie pour le projet distant, mais que les mises en correspondance locales ont été personnalisées, les paramètres locaux sont conservés sans affecter les paramètres du serveur.

    -   Si le projet distant contient des mises en correspondance personnalisées, mais que le projet local n’en contient pas, les mises en correspondance du serveur sont appliquées au projet local.

    -   Si le projet distant précise un protocole URL et que vous le téléchargez en utilisant un protocole différent, votre configuration locale sera conservée.

        Par exemple, de nombreux services d’hébergement permettent l’accès au même dépôt en utilisant soit le protocole SSH + Git soit le protocole https. OmegaT se conforme au choix du protocole local.

    -   Si vous téléchargez d’abord le projet distant en utilisant un fichier `omegat.project` fourni par l’administrateur du projet, OmegaT utilisera les mises en correspondance de ce fichier, le cas échéant.

    -   S’il y a un conflit entre la version locale et la version distante du fichier `omegat.project`, et que la version locale est remplacée, OmegaT crée un fichier de sauvegarde appelé `omegat.project.AAAAMMJJhhmm.bak`. OmegaT peut créer jusqu’à dix fichiers de sauvegarde, et supprime automatiquement les sauvegardes les plus anciennes l’une après l’autre.

N’oubliez pas que les modifications apportées localement aux fichiers de configuration du projet sont remplacées par les versions du serveur dès que le projet est synchronisé.

Fichiers source  
Seul l’administrateur du projet devrait utiliser le menu [\#menus.project](#menus.project)[\#menus.project.commit.source.files](#menus.project.commit.source.files).

Fichiers cible  
Après avoir généré les fichiers cible, utilisez le menu [\#menus.project](#menus.project)[\#menus.project.commit.target.files](#menus.project.commit.target.files) pour les ajouter au serveur, si l’administrateur du projet vous a demandé de le faire.

Supprimer des fichiers  
Les fichiers d’un projet en équipe ne peuvent pas être supprimés à partir d’OmegaT ou du système de fichiers local. Ils seront restaurés lors de la prochaine synchronisation du projet. Cette tâche est normalement effectuée par l’administrateur du projet.

Travailler hors connexion  
Vous pouvez ouvrir un projet en équipe et travailler dessus hors ligne. Toutes les modifications seront synchronisées dès qu’une connexion sera disponible.

Il y a deux manières de travailler hors ligne :

-   Déconnectez-vous du réseau avant d’ouvrir le projet.

-   Ouvrez le projet en ligne de commande à l’aide de l’option `--no-team`. Voir la section [\#launch.with.command.line](#launch.with.command.line) pour en savoir plus.
