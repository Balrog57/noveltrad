# Scripts

Les scripts sont des programmes courts (similaires aux macros des applications Office) qui peuvent être utilisés pour automatiser des tâches et pour développer et personnaliser les fonctionnalités d’OmegaT. Ils peuvent être écrits dans n’importe quel langage compris par la machine virtuelle Java existante.

La fenêtre de Scripts vous permet de charger un script préexistant et de l’exécuter dans le projet en cours.

Utilisez [\#menus.tools](#menus.tools)[\#menus.tools.scripting](#menus.tools.scripting) pour accéder à la fenêtre.

## Dossier des fichiers scripts

Par défaut, les scripts sont stockés dans le dossier [\#application.folder.scripts](#application.folder.scripts) dans le dossier de l’application d’OmegaT.

Les nouveaux scripts ajoutés ici apparaitront dans la liste des scripts disponibles dans le panneau gauche de la fenêtre des scripts.

Si aucune liste de scripts n’est affichée dans la partie gauche de la fenêtre d’édition de scripts, utilisez le menu Fichier &gt; Définir le dossier des scripts… de la fenêtre de scripts pour définir l’emplacement des scripts.

Des scripts supplémentaires sont disponibles ici : [Scripts OmegaT](https://sourceforge.net/projects/omegatscripts/). Il suffit de copier le fichier dans le dossier [\#application.folder.scripts](#application.folder.scripts).

Certains scripts sont basés sur des *évènements*. Le dossier qui contient les scripts inclut des sous-dossiers qui correspondent aux évènements disponibles. Vous pouvez déclencher des scripts automatiquement en les plaçant dans le sous-dossier approprié :

application\_shutdown  
Les scripts contenus dans ce dossier sont exécutés avant la fermeture d’OmegaT.

application\_startup  
Les scripts contenus dans ce dossier sont exécutés dès que le moteur de script est disponible, peu après le démarrage d’OmegaT.

entry\_activated  
Les scripts contenus dans ce dossier sont exécutés lors de l’édition d’un nouveau segment. Le segment est dans la liaison `newEntry>`.

new\_file  
Les scripts contenus dans ce dossier sont exécutés lorsque l’éditeur passe au fichier suivant dans le projet. Le nouveau nom de fichier est dans la liaison `activeFileName`.

new\_word  
Les scripts contenus dans ce dossier sont exécutés lors de l’édition d’un nouveau mot dans la fenêtre Éditeur. Le nouveau mot est disponible à partir de la liaison `newWord`.

project\_changed  
Les scripts contenus dans ce fichier sont exécutés lorsque l’état du projet change. Un objet `eventType` est lié et peut prendre les valeurs suivantes : CLOSE, COMPILE, CREATE, LOAD, ou SAVE

Ces sous-dossiers sont déjà créés dans le dossier des scripts fourni avec la distribution.

Des scripts peuvent aussi être exécuteurs lorsque vous exécutez d’autres scripts. Par conséquent, dans un grand projet, un script `entry_activated` est souvent utilisé lorsqu’un script de type recherche/remplacement qui passe en boucle par tous les segments est utilisé, ce qui rend l’application peu réactive.

## Utilisation

-   Cliquer sur le nom d’un script dans la liste du panneau à gauche de la fenêtre de scripts. Le script est alors chargé dans l’éditeur.

-   Cliquer sur le bouton Exécuter en bas de la fenêtre ou appuyer sur les touches <span class="keycombo">C+R</span> pour exécuteur le script immédiatement.

-   Pour créer un raccourci à un script que vous utilisez fréquemment, faites un clic droit sur l’un des boutons de &lt;1&gt; à &lt;12&gt; en bas de la fenêtre et sélectionnez Ajouter le script pour assigner le script à ce numéro.

    Si vous souhaitez détacher le script du raccourci, faites un clic droit sur le bouton et sélectionnez Supprimer le script.

-   Vous pouvez alors cliquer sur le numéro pour exécuter le script qui lui est assigné. Vous pouvez aussi exécuter le script depuis le menu [\#menus.tools](#menus.tools)[\#menus.tools.scripting](#menus.tools.scripting) en sélectionnant l’élément de menu souhaité ou en appuyant sur le raccourci associé (<span class="keycombo">C+A+F1 à F12</span>).

Si vous utilisez Linux : en fonction de la configuration de votre système d’exploitation, il se peut que vous n’ayez pas la permission d’écrire dans le dossier des scripts par défaut.

Dans ce cas, vous devrez copier ou déplacer le dossier des scripts dans un emplacement où vous avez la permission d’écrire, comme le [dossier de configuration](#configuration.folder.location), si vous souhaitez écrire vos propres scripts, en ajouter de nouveaux, ou modifier ceux qui existent déjà.

Si vous avez la permission d’écrire dans le dossier par défaut, veillez à changer le nom ou à faire une sauvegarde de n’importe quel script que vous modifiez, étant donné qu’ils seront remplacés quand OmegaT sera mis à jour.

## Les scripts distribués

OmegaT est fourni avec un certain nombre de scripts développés par les contributeurs d’OmegaT. Utilisez l’éditeur de script pour ouvrir, exécuter, modifier les scripts directement, ou écrire de nouveaux scripts pour votre propre usage.

Les scripts fournis avec OmegaT sont inclus pour votre confort mais ne sont pas pris en charge par l’équipe de développement d’OmegaT.

Suivez les instructions fournies avec le script.

Adapter les balises standards  
Adapte les balises standards lorsque la commande Remplacer par la correspondance est utilisée.

Ouvrir automatiquement le dernier projet  
Ouvre automatiquement le dernier projet OmegaT utilisé.

Vérifier le même segment  
Vérifie s’il y a des segments identiques (sensible à la casse).

Conversion de devises  
Traduit la représentation des devises selon la source et la cible.

Une chaine de caractères comme “$123,399.99” sera traduite en “123 399,99 USD" par exemple.

Exemple : script d’interface graphique  
Exemple de script d’interface graphique

Exemple : liaison de touches  
Exemple d’utilisation d’un évènement de liaison de touches.

Exemple : modification d’un segment  
Exemple qui montre comment modifier un segment.

Exemple : recherche et remplacement  
Un script simple de recherche et remplacement.

Vérification orthographique externe  
Écrit tous les segments dans un fichier nommé `[nom_du_projet].doc` et l’ouvre dans l’éditeur de texte par défaut du système. Notez que le fichier est un fichier texte brut. L’extension `.doc` garantit simplement qu’il s’ouvre dans l’éditeur de texte.

Extraction du contenu textuel  
Extrait le contenu de l’ensemble du projet dans un seul fichier texte (une ligne par segment). Voir [RFE#182 Extracts the content of the projects to text file](https://sourceforge.net/p/omegat/feature-requests/182/).

Espace insécable  
Remplacer les espaces par des espaces insécables lorsque nécessaire en français

Ouvrir le fichier actuel  
Ouvre le fichier source actuel.

Ouvrir le glossaire  
Ouvre le glossaire modifiable dans un éditeur.

Ouvrir le dossier du projet  
Ouvre le dossier du projet dans le gestionnaire de fichier par défaut.

Ouvrir le dossier de la mémoire de traduction  
Ouvre le dossier `/tm`.

Ouvrir project\_save.tmx  
Ouvre le fichier project\_save.tmx dans un éditeur de texte.

AQ - Règles de vérification  
Script d’AQ

AQ - Segments identiques  
Vérifie s’il y a des segments identiques (sensible à la casse).

SVN - Nettoyage (récursif)  
Effectue un nettoyage SVN sur le projet actuel ou sur n’importe quel dossier (récursivement).

Afficher les mêmes segments  
Affiche une liste de segments dont le contenu est identique dans la source et la cible.

Vérification orthographique  
Vérification orthographique globale

Retirer les marques bidirectionnelles  
Supprime les marques bidirectionnelles dans la cible actuelle ou dans la sélection.

Retirer les balises  
Supprime les balises dans la cible actuelle ou dans la sélection.

Changer le thème de couleurs  
Change le thème de couleurs utilisé dans l’éditeur.

Correspondance sans balise  
Remplace la cible actuelle avec une correspondance sans balise.

Tagwipe  
Retire les balises superflues des documents docx.

issue\_provider\_sample.groovy  
(pas de description)

toolbar.groovy  
(pas de description)

## Références

Javadoc OmegaT  
La documentation de l’[API d’OmegaT](https://omegat.sourceforge.io/javadoc-latest/).

Groovy  
Un langage dynamique conçu pour la machine virtuelle de Java. Il s’appuie sur les ressources de Java et y rajoute de puissantes fonctions inspirées de langages tels que Python, Ruby et Smalltalk. Voir [Apache Groovy](https://groovy-lang.org/documentation.html) pour en savoir plus.

JavaScript  
Un langage de script à prototype qui est dynamique, à typage faible, et avec des fonctions de première classe. C’est un langage multiparadigme qui prend en charge les styles de programmation orientés objet, impératifs et fonctionnels. Voir [Practical Nashorn, Part 1: Introducing JavaScript, ECMAScript, and Nashorn](https://developer.oracle.com/databases/nashorn-javascript-part1.html) et [ECMAScript® 5.1 Language Specification](https://www.ecma-international.org/ecma-262/5.1/).

Tous les langages ont accès au modèle objet d’OmegaT, le projet étant l’objet principal. Par exemple, l’exemple de code suivant dans le langage Groovy examine tous les segments de chaque fichier du projet actuel et imprime le texte source et cible des segments qui contiennent une traduction.

    files = project.projectFiles;
    for (i in 0 ..< files.size())
    {
        for (j in 0 ..< files[i].entries.size())
        {
            currSegment = files[i].entries[j];
            if (project.getTranslationInfo(currSegment))
            {
                source = currSegment.getSrcText();
                target = project.getTranslationInfo(currSegment).translation;
                console.println(source + " >>>> " + target);
            }     
        }
    }
