# Lancer OmegaT

## Sur Windows

La façon la plus simple de lancer OmegaT est d’exécuter le programme `OmegaT.exe`. Les options de démarrage du programme sont lues depuis le fichier `OmegaT.l4J.ini`, qui se trouve dans le même dossier que le fichier exe. Ce fichier peut être modifié pour être adapté à votre installation. L’exemple suivant du fichier INI utilise 1 Go de mémoire, choisit le français comme langue et le Canada comme pays :

    # OmegaT.exe runtime configuration
        # To use a parameter, remove the '#' before the '-'
        # Memory
        -Xmx1024M
        # Language
        -Duser.language=FR
        # Country
        -Duser.country=CA

Conseil : si OmegaT fonctionne plus lentement dans des sessions de Bureaux à distance, vous pouvez utiliser cette option :

    -Dsun.java2d.noddraw=false

## Sur Linux

Vous pouvez lancer OmegaT à partir de la ligne de commande avec un script qui comprend des options de démarrage. Voir la section [\#launch.with.command.line](#launch.with.command.line) pour en savoir plus.

Vous pouvez aussi double-cliquer sur `OmegaT.jar` pour le lancer directement, si l’extension `.jar` est associée au programme de lancement Java du système.

Le paquet vous fournit le script Kaptain `omegat.kaptn`, que vous trouverez surement utile si vous êtes sous KDE, ainsi qu’un script bash `OmegaT` qui lance automatiquement la commande java requise pour le fonctionnement d’OmegaT.

## Sur macOS

Double-cliquez sur `OmegaT.app` ou cliquez sur son emplacement dans le Dock.

`OmegaT.app` est accompagné d’un exécutable `OmegaT` situé dans le dossier `OmegaT.app/Contents/MacOS/` que vous pouvez aussi utiliser pour lancer plusieurs instances d’`OmegaT.app`.

Et il est également accompagné du fichier générique `OmegaT.jar` situé dans le dossier `OmegaT.app/Contents/MacOS/Java/` que vous pouvez utiliser pour lancer OmegaT en ligne de commande. Voir la section [\#launch.with.command.line](#launch.with.command.line) pour en savoir plus.

Vous pouvez modifier le comportement du fichier OmegaT.app en modifiant le fichier `Configuration.properties` (configuration d’OmegaT) et le fichier`Info.plist` (configuration Java) qui se trouvent dans le paquet OmegaT.app.

Le fichier `Configuration.properties` se trouve dans le dossier `Contents/Resources/`.

Le fichier `Info.plist` se trouve dans le dossier `Contents/`.

Afin d’accéder aux fichiers dans le paquet `OmegaT.app`, faites un clic droit sur `OmegaT.app` et sélectionnez « Afficher le contenu du paquet ».

Il est également possible d’utiliser directement le fichier `OmegaT.app` pour lancer OmegaT depuis le terminal. Voir la section [\#launch.with.command.line.omegat.terminal.command.syntax](#launch.with.command.line.omegat.terminal.command.syntax) pour en savoir plus.

Utilisez l’éditeur de texte de votre choix pour modifier les fichiers.

Configuration.properties  
Pour les options prédéfinies, supprimez le symbole `#` devant un paramètre pour l’activer. Par exemple, `user.language=ja` (sans le `#`) lancera OmegaT avec l’interface en japonais.

Info.plist  
Par exemple, pour modifier la quantité de mémoire disponible, retirez la marque de commentaire en début de ligne

`<!-- <string>-Xmx6g</string> -->`

en supprimant les marqueurs `<!--` et `-->`.

Ceci lancera OmegaT avec une mémoire de 6 Go. Remplacez la valeur `6g` par celle que vous désirez.

`OmegaT.app` peut utiliser les Services de macOS. Vous pouvez également utiliser AppleScript, Automator ou Raccourcis pour créer des services ou des scripts qui vont automatiser des actions fréquentes.

## Sur d’autres plateformes

Les méthodes varient d’un système à l’autre, mais en général, une fois qu’OmegaT est installé, vous pouvez le lancer directement en ligne de commande. Voir la section [\#launch.with.command.line](#launch.with.command.line) pour en savoir plus.

Vous pouvez créer un script qui inclut les paramètres souhaités pour le lancement en ligne de commande. Si les fichiers `.jar` sont correctement associés avec l’environnement d’exécution Java 11 et que vos paramètres PATH sont corrects, vous pouvez également cliquer (ou double-cliquer) sur `OmegaT.jar` pour l’exécuter directement.

Consultez la documentation de votre système pour plus d’information.

## Lancement en ligne de commande

Utiliser une ligne de commande vous permet de définir diverses options qui contrôlent ou modifient le comportement de l’application. Vous pouvez aussi définir et enregistrer des groupes d’options dans des scripts que vous utiliserez ensuite pour lancer OmegaT dans un but particulier.

Lancer OmegaT en ligne de commande crée une nouvelle instance d’OmegaT à chaque lancement. Vous pouvez donc utiliser plusieurs projets simultanément, chacun avec ses propres paramètres.

### Présentation simplifiée

Avant que les interfaces graphiques ne deviennent courantes, on interagissait avec les ordinateurs via une interface en ligne de commande (ILC), qui nécessitait de taper des commandes pour donner des instructions à l’ordinateur. Sur les systèmes modernes, l’ILC est accessible à partir d’une application généralement appelée « terminal » ou « console ». Par souci de simplicité, ce manuel utilise le terme « terminal ».

Sur Windows, vous pouvez utiliser soit l’Invite de commandes soit Powershell en guise de terminal. Les deux sont disponibles à partir du Menu Démarrer.

L’équivalent pour macOS est l’application Terminal située dans le dossier `Utilitaires` du dossier principal `Applications`.

Sur Linux, l’application par défaut du terminal pour votre distribution devrait être disponible depuis le menu d’applications ou l’un de ses sous-menus.

Dans le terminal, il faut saisir des commandes et les paramètres associés pour exécuter des tâches. Ce procédé permet d’exécuter plus facilement certaines tâches difficiles à réaliser via une interface graphique.

La syntaxe utilisée pour spécifier l’emplacement d’une application ou d’un dossier dépend de la plateforme. Sous Windows, le caractère `\` est utilisé pour séparer les noms de dossiers et de fichiers, tandis que macOS et Linux utilisent la `/`.

Voici les emplacements par défaut du fichier OmegaT.jar pour chaque plateforme majeure :

Windows  
`C:\Programmes\OmegaT\OmegaT.jar`

MacOS  
`/Applications/OmegaT.app/Contents/Java/OmegaT.jar`

Linux  
`/opt/omegat/OmegaT.jar`

(L’emplacement peut varier en fonction de votre distribution.)

L’emplacement est présenté en tant que `chemin/à/OmegaT.jar` dans ce chapitre. Remplacez-le avec l’emplacement réel du fichier sur votre système.

### Syntaxe de commande

La syntaxe pour lancer OmegaT depuis le terminal est :

    java -jar <paramètres java> chemin/à/OmegaT.jar <options OmegaT> 

Sur macOS, il est également possible d’utiliser `OmegaT.app` directement dans le terminal, auquel cas les paramètres java ne peuvent pas être ajoutés :

    open chemin/vers/OmegaT.app
            -n --args <options OmegaT>

ici, `-n` est utilisé pour créer une nouvelle instance d’OmegaT.

`java -jar`  
Cette commande indique à la machine virtuelle Java d’exécuter un paquet Jar.

`<paramètres java>`  
Les paramètres optionnels acceptés par la commande `java`. Les paramètres relatifs au lancement OmegaT sont décrits [ci-dessous](#launch.with.command.line.java.parameters).

`chemin/vers/OmegaT.jar`  
L’emplacement de l’exécutable java OmegaT.

*`<options OmegaT>`*  
Les options spécifiques à OmegaT sont décrites [plus bas dans cette section](#launch.with.command.line.omegat.options).

### Paramètres java

La liste ci-dessous présente les paramètres pour la commande `java` qui peuvent être utiles lorsque vous travaillez avec OmegaT.

Langue de l’interface  
`-Duser.language=LL`

Remplacez `LL` par le code à deux lettres de la langue souhaitée de la liste [ISO 639.1](https://fr.wikipedia.org/wiki/Liste_des_codes_ISO_639-1).

L’utilisation de ce paramètre permet de lancer OmegaT avec l’interface dans la langue spécifiée, si elle est disponible (même partiellement). Si la langue n’est pas disponible, OmegaT sera par défaut en anglais, même si le système utilise une autre langue par défaut.

Pays d’utilisation  
`-Duser.country=PP`

Remplacez `PP` par le code à deux lettres du pays souhaité de la liste [ISO 3166-1 alpha-2](https://fr.wikipedia.org/wiki/ISO_3166-2).

Ce paramètre se combine avec le paramètre précédent de langue de l’interface pour spécifier une variante régionale. Si cette variante n’est pas disponible, l’interface adopte la même priorité que ci-dessus.

Affectation maximale de la mémoire  
`-XmxTAILLE`

Remplacez `TAILLE` par un nombre qui consiste d’un multiple de 1024 suivi d’un `k` pour kilooctets, d’un `m` pour mégaoctets, ou d’un `g` pour gigaoctets. Le nombre doit correspondre à au moins 2 Mo.

Adresse IP de l’hôte proxy  
`-Dhttp.proxyHost=<IP du proxy>`

Remplacez `<IP du proxy>` par l’adresse IP de votre serveur proxy, si votre système en utilise un.

Numéro de port de l’hôte proxy  
`-Dhttp.proxyPort=<numéro de port>`

Remplacez `<numéro de port>` par le numéro de port que votre système utilise pour accéder au serveur proxy.

### Options OmegaT

Vous pouvez également obtenir une liste de ces options dans le terminal avec la commande `java -jar OmegaT.jar --help`. L’interface graphique d’OmegaT se lance si aucune option n’est spécifiée.

Options générales :  
`-h`, `--help`  
Afficher les informations d’utilisation

*chemin vers un projet omegat*  
Lancer l’interface graphique et charger le projet spécifié

`--remote-project` `<chemin-vers-fichier-projet-omegat>`  
Télécharger le projet OmegaT depuis l’URL spécifiée dans *chemin-vers-fichier-projet-omegat*, et le charger.

`--no-team`  
Désactiver la fonctionnalité de projets en équipe. Utilisez cette option si vous souhaitez empêcher OmegaT de synchroniser le contenu du projet.

`team init` `LS` `LC`  
Initialiser un projet en équipe en utilisant les codes de langue à deux lettres *LS* et *LC* pour la langue source et la langue cible, respectivement.

`--disable-project-locking`  
Ne pas verrouiller le fichier omegat.project.

Sur certaines plateformes, le fichier omegat.project est verrouillé par défaut, et essayer d’ouvrir un projet qui est déjà ouvert sur une autre instance d’OmegaT produit une erreur. Cette option empêche cette erreur.

`--disable-location-save`  
Ne pas enregistrer le dernier dossier ouvert dans le sélecteur de fichiers.

`--ITokenizer=``<classname>`; `--ITokenizerTarget=``<nomdeclasse>`  
Spécifier le lemmatiseur source ou cible à utiliser (l’utilisation de cette option remplace les paramètres du projet). Consulter OmegaT.jar/META-INF/MANIFEST.MF pour les valeurs possibles.

`--config-dir=``<chemin>`  
Le dossier utilisé pour lire et écrire les fichiers de configuration d’OmegaT. Voir le chapitre [\#configuration.folder](#configuration.folder) pour en savoir plus.

`--config-file=``<chemin>`  
Fichier .properties écrit en Java, utilisé pour spécifier un ensemble d’options de ligne de commande.

Les options sont présentées comme une liste de paires `clé=valeur`. Les paramètres Java et les options OmegaT peuvent tous deux être utilisés.

Enlevez le `-D` ou le `-X` du début pour utiliser les paramètres Java :

    user.language=fr
    config-dir="chemin/vers/nouveau/configdir"

Presque tous les paramètres présentés dans cette section peuvent être utilisés dans un fichier de configuration. Avec une exception importante : `remote-project`.

Il est possible de combiner la commande`--config-file` avec d’autres options de lignes de commandes compatibles avec le lancement de l’interface graphique. Dans ces cas, les options définies dans le fichier de configuration ont la priorité sur toute option dont la fonctionnalité est dupliquée et transmise par la ligne de commande.

`--resource-bundle=``<chemin>`  
Un fichier .properties en Java à utiliser pour le texte de l’interface.

`--mode=[nom du mode de console]` `<chemin du projet>` `<option du mode>`  
Spécifier un mode différent de l’interface graphique par défaut. Les options suivantes sont disponibles :

`--mode=console-translate` `<chemin du projet>`  
Dans ce mode, OmegaT tente de traduire les fichiers du dossier source avec les mémoires de traduction disponibles.

Ce mode est utile si OmegaT est exécuté sur un serveur qui fournit automatiquement des fichiers TMX à un projet.

`--source-pattern=``<masque>`  
Liste d’expressions régulières acceptées qui définissent les fichiers source à traiter. N’oubliez pas que dans les expressions régulières, le point et la barre oblique inversée doivent être échappés : `\.` et `\\`.

Voici quelques exemples typiques :

`.*\.html`  
Traduire tous les fichiers HTML.

`test\.html`  
Traduire seulement le fichier `test.html` dans le dossier source même. Tout fichier aussi nommé test.html dans d’autres sous-dossiers sera ignoré.

`dir-10\\test\.html`  
Traduire seulement le fichier `test.html` dans le dossier `dir-10`.

Voir l’annexe [\#app.regex](#app.regex) pour en savoir plus.

`--mode=console-createpseudotranslatetmx` `<chemin du projet>`  
Dans ce mode, OmegaT crée un fichier TMX pour l’ensemble du projet en utilisant uniquement les fichiers source.

Spécifiez le fichier TMX à utiliser :

`--pseudotranslatetmx=``<chemin>`  
Le fichier TMX pseudotraduit produit.

`--pseudotranslatetype=[equal|empty]`  
Le contenu à inclure dans la TMX pseudotraduite.

`--mode=console-align` `<chemin du projet>`  
Dans ce mode, OmegaT aligne les fichiers du dossier /source du projet avec ceux qui se trouvent à l’emplacement spécifié dans le paramètre *--alignDir* ci-dessous.

`--alignDir=``<chemin du projet>`  
Le chemin qui contient les fichiers traduits en langue cible.

Ce dossier doit contenir une traduction dans la langue cible du projet. Par exemple, s’il s’agit d’un projet de l’anglais vers le français, le dossier spécifié doit contenir un ensemble de fichiers se terminant par `_fr`.

Le fichier TMX ainsi créé est enregistré dans le dossier `omegat/` avec le nom `align.tmx`. Les types de fichiers pouvant être alignés dépendent du filtre de fichiers et de sa capacité à gérer l’alignement. Les filtres pris en charge incluent : le fichier de langue ILIAS, les paquets de ressources Java(TM), texte clé=valeur, localisation CSV Magento CE, MoodlePHP, Mozilla DTD, Mozilla FTL, PO, RC, les sous-titres SubRip et les ressources Windows.

`--mode=console-stats` `<chemin du projet>`  
`--output-file=``[stats-output-file]`  
Envoie les informations vers ce fichier, ou vers la sortie standard si absent. Sans *--stats-type*, détecte le format à partir de l’extension du fichier. Le format de sortie par défaut est xml.

`--stats-type=[xml|text][txt][json]]]`  
Nécessite la commande *--output-file*. Spécifie le format de sortie.

Les données sont les mêmes que lors de l’utilisation de [\#menus.tools](#menus.tools)[\#menus.tools.statistics](#menus.tools.statistics).

Options non liées à l’interface graphique :  
`--quiet`  
Réduit les sorties affichées dans la ligne de commande.

`--script=``<chemin>`  
Un fichier script à exécuter lorsqu’un évènement survient dans un projet.

`--tag-validation=[abort|warn]`  
Vérifier les problèmes de balise.

-   Abort : quitter avec un message d’erreur s’il y a des problèmes de balise.

-   Warn : montrer les avertissements sans quitter s’il y a des problèmes de balise.

Les rapports sur les problèmes de balise sont affichés dans la fenêtre du terminal.
