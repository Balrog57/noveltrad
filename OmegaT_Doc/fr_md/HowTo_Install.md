# Installer OmegaT

Il existe deux versions d’OmegaT.

Version standard : OmegaT 6.1.0  
Cette version est recommandée pour un usage quotidien.

Version de développement : OmegaT Nightly  
Cette version est générée automatiquement à chaque fois que du code nouveau est intégré à OmegaT. Elle est utilisée pour effectuer des tests.

Les fichiers sont téléchargeables directement à partir de [https://omegat.org/fr](https://omegat.org/fr/download).

Java 11 Runtime Environment (JRE) est nécessaire à l’exécution d’OmegaT 6.1.0.

Les paquets d’OmegaT sont disponibles à la fois dans des versions avec Java, et dans des versions sans. Les paquets sans Java nécessitent l’installation d’un environnement d’exécution Java 11 sur l’ensemble du système.

OmegaT 5.8.0 et les versions ultérieures peuvent aussi fonctionner avec l’environnement d’exécution Java 11 sur n’importe quelle plateforme.

Pour des raisons de licence, l’équipe d’OmegaT recommande l’environnement d’exécution Eclipse Temurin Java fourni avec le projet Adoptium de la Fondation Eclipse, mais n’importe quel environnement d’exécution compatible avec Java 8 devrait fonctionner. Voir [Le projet Eclipse Temurin™](https://projects.eclipse.org/projects/adoptium.temurin).

IBM fournit des environnements d’exécution Java JRE pour Linux PowerPC à l’adresse [](https://developer.ibm.com/languages/java/semeru-runtimes/downloads/).

## Sur Windows

Double-cliquez sur le paquet que vous avez téléchargé.

Vous pouvez choisir la langue utilisée pendant l’installation et la langue qui sera utilisée par OmegaT. Vous pouvez aussi changer ce paramètre plus tard en modifiant le fichier `OmegaT.l4J.ini`.

## Sur Linux

Certaines distributions de Linux proposent OmegaT dans leur gestionnaire de paquets. Les instructions ci-dessous s’appliquent aux personnes qui téléchargent le paquet depuis le site [https://omegat.org](https://omegat.org/fr/download) pour l’installer manuellement.

Décompressez/désarchivez le fichier que vous avez téléchargé. Un nouveau dossier du même nom que le paquet va être créé. Il contient tous les fichiers nécessaires à l’exécution d’OmegaT.

Bien qu’il soit possible de lancer OmegaT directement à partir des fichiers disponibles, vous pouvez aussi exécuter le script `linux-install.sh` qui s’y trouve pour installer OmegaT dans un emplacement plus approprié.

L’exécution du script vous demandera d’entrer votre mot de passe `sudo`.

Le script vérifie si la même version d’OmegaT est déjà installée dans le dossier `/opt/omegat/` et, dans le cas contraire, installe le programme dans `/opt/omegat/OmegaT_6.1.0` en le définissant comme version par défaut (dans `/opt/omegat/OmegaT-default`).

Une fois la décompression ou l’installation terminée, vous pouvez supprimer le fichier téléchargé, car il n’est plus utile.

## Sur macOS

Double-cliquez sur le paquet que vous avez téléchargé pour le décompresser. Un dossier nommé `OmegaT` va être créé. Il contient deux fichiers : `index.html` (le fichier d’entrée du manuel d’utilisation) et `OmegaT.app` (l’application). Copiez le dossier dans un emplacement approprié (ex .: `Applications`).

Si vous le souhaitez, vous pouvez faire glisser l’application `OmegaT.app` et la déposer dans le Dock pour un accès plus facile.

Quand vous avez terminé, vous pouvez supprimer le paquet téléchargé, car il n’est plus utile.

## Sur d’autres plateformes

Ces informations s’appliquent à tout système pour lequel une version de Java compatible avec Java 11 Runtime Environment est disponible. Cela inclut les plateformes décrites ci-dessus, mais aussi celles pour lesquelles aucun paquet spécifique d’OmegaT n’est fourni.

Téléchargez la version *Multiplateforme sans JRE*.

Décompressez le fichier que vous avez téléchargé. Un dossier contenant tous les fichiers nécessaires à l’exécution d’OmegaT va être créé.

Suivez les instructions de votre système pour installer des raccourcis d’OmegaT aux emplacements de votre choix.

## Mettre à jour

OmegaT peut vous informer quand une nouvelle version est disponible. Voir le paramètre [\#dialogs.preferences.updates](#dialogs.preferences.updates) pour en savoir plus.

Les changements entre votre version et la nouvelle sont documentés dans le fichier [changes.txt](https://sourceforge.net/p/omegat/code/ci/master/tree/release/changes.txt) sur le site du développement.

Si vous décidez d’installer une nouvelle version, gardez les éléments suivants à l’esprit :

-   Les préférences d’OmegaT sont stockées dans le dossier de configuration et ne sont *pas* modifiées par la nouvelle version. Voir le chapitre [\#configuration.folder](#configuration.folder) pour en savoir plus.

-   Les projets que vous avez créés auparavant ou que vous utilisez actuellement ne seront *ni modifiés ni supprimés*, car ils *ne sont pas* stockés à l’intérieur d’OmegaT. Ce sont des objets distincts qui n’ont pas de lien physique avec l’application OmegaT en elle-même.

-   Les fichiers de paramétrage inclus dans le paquet OmegaT téléchargé (en particulier, le fichier `OmegaT.l4J.ini` pour les paquets [Windows](#running.omegat.on.windows), ainsi que les fichiers `Configuration.properties` et `Info.plist` pour les paquets [macOS](#running.omegat.on.macos)) pourront être remplacés ou supprimés. Par conséquent, si vous utilisiez ces fichiers pour modifier les paramètres de lancement d’OmegaT, vous devez en faire une sauvegarde avant de procéder à la mise à jour.

-   Les dossiers des `extensions` et des `scripts` pourraient être remplacés, vous devriez donc en faire une sauvegarde avant de procéder à la mise à jour.

Par-dessus une version existante  
Pour ce faire, il suffit de sélectionner le même dossier d’installation que celui de l’installation existante lorsque vous installez la nouvelle version. « L’ancienne » version d’OmegaT sera remplacée, mais les réglages effectués à partir de l’interface d’OmegaT seront conservés dans les différents dossiers de configuration (voir ci-dessus).

Parallèlement à une version existante  
Cela vous permet de conserver côte à côte autant de versions que vous voulez, ce qui peut être utile jusqu’à ce que vous vous sentiez à l’aise avec la nouvelle version.

Tous les paramètres situés dans le dossier de configuration d’OmegaT seront partagés à moins que vous ne spécifiiez un dossier de configuration différent à l’aide de l’option `--config-dir=<path` sur la ligne de commande. Voir la section [\#launch.with.command.line.omegat.options](#launch.with.command.line.omegat.options).

Tous les paramètres situés dans un [dossier de projet](#chapter.project.folder) s’appliqueront à ce projet indépendamment de la version d’OmegaT avec laquelle vous l’ouvrez.

## Supprimer OmegaT

Utilisez la procédure standard de votre système d’exploitation pour supprimer OmegaT. Si vous souhaitez supprimer complètement OmegaT, vous devez aussi supprimer le dossier de configuration.

Si vous avez effectué une installation manuelle sur Linux, vous devez également supprimer manuellement les dossiers d’OmegaT dans `opt/`, ainsi que les liens symboliques placés dans le dossier `/usr/local/bin/` par le script d’installation.

## Compiler OmegaT

Le code source pour la version actuelle peut être téléchargé directement depuis la [page de téléchargement](https://omegat.org/fr/download) d’OmegaT, ou bien cloné depuis les dépôts [Sourceforge](https://git.code.sf.net/p/omegat/code) ou [GitHub](https://github.com/omegat-org/omegat.git).

Une fois le code téléchargé, ouvrez un terminal dans le dossier source (`omegat-code` si vous l’avez cloné de Sourceforge, ou `/omegat` si vous l’avez cloné de GitHub) et entrez :

    ./gradlew installDist

Cette commande crée une distribution d’OmegaT complète et prête à être lancée dans le dossier `build/install/OmegaT`.

Vous pouvez aussi lancer l’application directement avec la commande suivante :

    ./gradlew run

Pour obtenir la liste de toutes les tâches disponibles, utilisez la commande :

    ./gradlew tasks

Vous trouverez les informations détaillées concernant la compilation d’OmegaT dans le fichier [README.txt](https://sourceforge.net/p/omegat/svn/HEAD/tree/trunk/docs_devel/README.txt) situé dans le sous-dossier `docs_devel`.
