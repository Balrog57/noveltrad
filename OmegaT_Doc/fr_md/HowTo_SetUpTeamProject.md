# Préparation d’un projet en équipe

La gestion d’un projet en équipe demande une certaine maitrise de l’un ou l’autre des logiciels de gestion de version : *SVN* ou *Git*.

Étant donné que les informations sur ces sujets sont faciles à trouver, ce manuel se limite à décrire leur utilisation dans le contexte d’un projet en équipe OmegaT.

Un projet en équipe OmegaT synchronise la mémoire de traduction du projet [\#project.folder.project.save.tmx](#project.folder.project.save.tmx) et le glossaire modifiable du projet [\#project.folder.glossary.txt](#project.folder.glossary.txt) entre le serveur d’hébergement et tous les membres de l’équipe. Le projet en équipe gère aussi tous les conflits possibles entre eux.

## Préparations

Voici les étapes à suivre afin de mettre en place un projet en équipe :

1.  Créez un dépôt vide sur votre serveur d’hébergement du logiciel de gestion de version

    Cela peut normalement se faire par l’intermédiaire d’une interface web, d’une application graphique, ou en ligne de commande. Consultez la documentation de votre serveur ou de votre service d’hébergement pour en savoir plus.

2.  Utilisez le logiciel de gestion de version local pour créer une copie locale (clone).

    Cette version locale contient votre copie du projet OmegaT qui servira de *gestionnaire de projet*. Utilisez-la pour effectuer des modifications qui se répercutent sur l’ensemble de l’équipe.

    Le dépôt local est utilisé pour ajouter le projet initial au serveur, et peut aussi servir à effectuer des tâches de maintenance qui ne peuvent pas être réalisées directement dans OmegaT, comme la suppression de fichiers.

    Nous vous recommandons d’éviter d’utiliser ce dossier pour des tâches de traduction. Si vous avez besoin d’effectuer des traductions ou des tâches de révisions sur ce projet, utilisez OmegaT pour télécharger une copie séparée du projet en équipe et travaillez à partir de celle-ci. Voir le guide pratique [\#how.to.use.team.project](#how.to.use.team.project) pour en savoir plus.

3.  Remplissez la copie locale vide avec un vrai projet OmegaT.

    -   Créez la structure du projet

        Si vous créez un nouveau projet vide, vous pouvez suivre la [procédure via interface graphique](#introduction.create.and.open.new.project), ou directement le créer avec la commande : `java -jar OmegaT.jar team init <langue source> <langue cible>`

        Cette commande permet aussi d’enregistrer automatiquement le projet dans le logiciel de gestion de version.

    -   Choisissez les paramètres appropriés

        Apportez les changements nécessaires aux propriétés du projet à ce stade, filtres de fichiers locaux et paramètres de segmentation inclus. Voir la boite de dialogue [\#dialogs.project.properties](#dialogs.project.properties) pour en savoir plus.

    -   Ajoutez les fichiers nécessaires

        Ajoutez également toute liste de fichiers de vérification orthographique pertinente que vous souhaitez mettre à la disposition de toutes les personnes qui travaillent sur le projet. Voir [fichiers de vérification orthographique](#project.folder.omegat.spellcheck) pour en savoir plus.

        Si vous convertissez un projet existant, veillez à supprimer tous les fichiers du projet dont vous n’avez pas besoin ou que vous ne souhaitez pas envoyer au serveur avant de passer à la prochaine étape.

        Copiez les fichiers à traduire dans le dossier source/ et utilisez votre client SVN ou Git, ou une ligne de commande, pour les ajouter et les publier dans le dépôt. Utilisez [\#menus.project](#menus.project)[\#menus.project.commit.source.files](#menus.project.commit.source.files) pour ajouter les fichiers à partir d’OmegaT.

        Vous devez utiliser votre client SVN ou Git, ou la ligne de commande, pour ajouter et publier tout dictionnaire, glossaire, mémoire de traduction, ou autre fichier que vous souhaitez inclure dans le projet.

        Cette étape peut être réalisée avant d’enregistrer et de publier le projet pour la première fois, et peut aussi être utilisée pour ajouter de nouveaux fichiers, ou même mettre à jour les fichiers existants après la création du projet.

    Dans les projets en équipe qui utilisent une simple mise en correspondance entre le dépôt local et le dépôt distant (par défaut), **et seulement dans ces projets**, les fichiers source et cible peuvent être modifiés localement et envoyés vers le serveur en utilisant [\#menus.project](#menus.project)[\#menus.project.commit.source.files](#menus.project.commit.source.files) et [\#menus.project](#menus.project)[\#menus.project.commit.target.files](#menus.project.commit.target.files).

    L’administrateur du projet en équipe doit utiliser le logiciel de gestion de version local pour **modifier** ou **supprimer** ces fichiers. Certaines extensions peuvent faciliter cette tâche. Voir le paramètre [\#dialogs.preferences.plugins](#dialogs.preferences.plugins) pour en savoir plus.

4.  Enregistrez les fichiers du projet dans le logiciel de gestion de version local

    Si vous avez créé le projet à partir de l’interface graphique, vous devrez alors explicitement l’ajouter au logiciel de gestion de version (`add` dans SVN et Git).

5.  Placez les fichiers enregistrés dans le serveur d’hébergement

    Enfin, publiez votre projet sur le serveur distant (`commit` sur SVN, `commit` et `push` sur Git).

6.  Donnez les droits d’accès à votre équipe.

    Si vous utilisez plusieurs projets sur un même serveur, les informations d’identification ne seront demandées qu’une fois pour ce serveur.

    Une fois le projet prêt et téléchargé sur le serveur, l’administrateur du projet en équipe doit configurer l’accès des membres de l’équipe de traduction. L’accès à un projet en équipe nécessite les informations suivantes :

    1.  Projets sur un service d’hébergement

        Les membres de l’équipe de traduction doivent créer un compte pour ce service et envoyer leur identifiant à l’administrateur du projet en équipe.

        L’administrateur va alors accorder à ces comptes un accès en écriture au dépôt.

    2.  Projets sur un serveur autohébergé

        Si le serveur est autohébergé et ne permet pas aux membres de l’équipe d’ouvrir un compte directement, l’administrateur du projet en équipe devra créer des comptes avec un accès en écriture pour les membres.

        Après avoir créé les comptes, l’administrateur doit envoyer aux membres leurs identifiants individuels.

7.  Demandez à tout le monde de télécharger le projet à partir d’OmegaT

    Les administrateurs ont deux options pour envoyer l’emplacement du projet aux membres :

    1.  Envoyer l’URL et demander aux membres d’utiliser [\#menus.project](#menus.project)[\#menus.project.download.team.project](#menus.project.download.team.project) pour créer une copie locale du projet sur leur propre système.

    2.  Envoyer un fichier `omegat.project` qui contient l’URL du projet, et ensuite demander aux membres de le copier dans un dossier vide et l’ouvrir dans OmegaT. Cette option peut être utile si le projet est paramétré pour utiliser des [mises en correspondance](#how.to.setup.team.project.mapping.parameters) différentes pour chaque membre.

    Une fois que l’administrateur du projet en équipe a confirmé que les membres ont réussi à ouvrir le projet en équipe, il est préférable de veiller à ce que les [statistiques du projet](#menus.tools.statistics) soient les mêmes pour l’administrateur (sur le serveur) et pour les membres (localement).

    Si elles ne correspondent pas, vérifiez que les fichiers `filters.xml` et `segmentation.conf` sont partagés correctement.

8.  Si vous devez aussi travailler sur le projet, téléchargez le projet à cet usage à un emplacement local différent de celui du projet en équipe local.

9.  Vous pouvez maintenant travailler sur le projet avec votre équipe.

## Mise en correspondance des dépôts

Il est possible de mettre en correspondance différents emplacements distants avec des fichiers locaux via l’interface d’OmegaT en utilisant l’élément [\#dialogs.project.properties.repository.mapping.title](#dialogs.project.properties.repository.mapping.title) dans la boite de dialogue [\#dialogs.project.properties](#dialogs.project.properties), ou en modifiant le fichier [\#project.folder.omegat.project.file.title](#project.folder.omegat.project.file.title). Bien que la fonctionnalité de mise en correspondance soit d’abord conçue pour rassembler les fichiers source provenant de différents emplacements, elle peut aussi être utilisée pour d’autres types de fichiers.

Une liste des paramètres de mise en correspondance est présentée ci-dessous, avec des exemples de leur utilisation dans la section suivante.

repository type  
Il peut s’agir de *http* (ce qui inclut https), *svn*, *git*, ou *file*.

repository url  
Emplacement ou dossier distant des fichiers à traduire.

mapping local  
Nom du dossier ou fichier local, par rapport à la racine du projet OmegaT.

mapping repository  
Nom du dossier ou fichier distant, par rapport à l’URL du dépôt.

excludes  
Utilisez des caractères joker (suivant le style Apache Ant : \*,?,\*\*) pour ajouter des masques pour les fichiers qui doivent être exclus de la mise en correspondance. Utilisez un point-virgule pour séparer différents masques.

Par exemple, le masque `**/dossier_exclu/**;*.txt` exclut les fichiers dont le chemin contient /dossier\_exclu/, ainsi que les fichiers avec l’extension `.txt`.

includes  
Même chose que précédemment, mais pour les fichiers qui doivent faire partie de la mise en correspondance. Vu que les fichiers sont inclus par défaut à moins d’être exclus expressément, cette option n’est nécessaire que pour spécifier les exceptions à un masque d’exclusion.

Par exemple, le masque `**/*.docx` ajoute tous les fichiers .docx au projet, même s’ils se trouvent dans un dossier exclu.

## Exemples de mises en correspondance

Mise en correspondance par défaut du projet :

    <repository type="svn" url="https://dépôt_du_projet_OmegaT_en_équipe">
        <mapping local="" repository=""/>
    </repository>

La totalité du contenu du `https://dépôt_du_projet_OmegaT_en_équipe` est mise en correspondance avec le projet OmegaT local.

Mise en correspondance pour des projets dans le sous-dossier d’un dépôt :

    <repository type="svn" url="https://dépôt_de_tous_les_projets_OmegaT_en_équipe">
        <mapping local="" repository="EN-US_FR_project"/>
    </repository>

La totalité du contenu du `https://dépôt_de_tous_les_projets_OmegaT_en_équipe/Projet_En-US_FR` est mise en correspondance avec le projet OmegaT local.

Mise en correspondance de sources supplémentaires en provenance de dépôts distants, avec des filtres :

    <repository type="svn" url="https://dépôt_de_toutes_les_sources_des_projets_OmegaT_en_équipe">
        <mapping local="source/subdir" repository="">
            <excludes>**/*.bak</excludes>
            <includes>readme.bak</includes>
        </mapping>
    </repository>

La totalité du contenu du `https://dépôt_de_toutes_les_sources_des_projets_OmegaT_en_équipe` est mise en correspondance avec le dossier source du projet OmegaT, à l’exception des fichiers portant l’extension `.bak`. Cependant, le fichier `readme.bak` est aussi inclus.

Mise en correspondance de sources supplémentaires provenant du web :

    <repository type="http" url="https://github.com/omegat-org/omegat/raw/master/">
        <mapping local="source/Bundle.properties" repository="src/org/omegat/Bundle.properties"/>
    </repository>

Le fichier distant `https://github.com/omegat-org/omegat/raw/master/src/org/omegat/Bundle.properties` est mis en correspondance avec le fichier local `source/Bundle.properties`.

Mise en correspondance avec renommage :

    <repository type="http" url="https://github.com/omegat-org/omegat/raw/master/">
        <mapping local="source/readme_fr.txt" repository="release/readme.txt"/>
    </repository>

Le fichier distant `https://github.com/omegat-org/omegat/raw/master/release/readme.txt` est mis en correspondance avec le fichier local `source/readme_tr.txt`.

Ceci permet de renommer le fichier à traduire.

Mise en correspondance d’un fichier local :

    <repository type="file" url="/dossier/de/mes/fichiers">
        <mapping local="source/file.txt" repository="mon/fichier.txt"/>
        <mapping local="source/file2.txt" repository="un/autre/fichier.txt"/>
    </repository>

Le fichier local `/dossiers/de/mes/fichiers/mon/fichier.txt` est mis en correspondance avec le fichier local `source/fichier.txt` et `/dossiers/de/mes/fichiers/un/autre/fichier.txt` est mis en correspondance avec le fichier local `source/fichier2.txt`.

Le projet ne se charge pas si un fichier spécifié dans une mise en correspondance n’existe pas.

Vous pouvez ajouter autant de mises en correspondance que vous le souhaitez, mais l’une d’elles doit contenir le fichier `omegat.project`.

## Partage sélectif

Le processus ci-dessus décrit le scénario le plus courant, dans lequel l’administrateur du projet en équipe a le contrôle total sur le projet et où tous les fichiers (et statistiques) sont identiques sur toutes les instances du projet, aussi bien sur le serveur que sur les systèmes locaux des membres de l’équipe.

Il est également possible d’utiliser une configuration de projet en équipe dans laquelle plusieurs membres partagent le fichier `project_save.tmx`, et seulement un sous-ensemble d’autres fichiers.

La procédure de base est essentiellement la même, sauf que l’administrateur du projet en équipe n’ajoute pas chaque fichier au projet géré par version sur le serveur. Les fichiers restants sont copiés par les membres, ou bien des mises en correspondance permettant de synchroniser des fichiers à partir d’autres emplacements sont définies.
