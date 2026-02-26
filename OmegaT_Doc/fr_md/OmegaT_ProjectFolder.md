# Racine du projet

## Structure par défaut

Un projet OmegaT se compose d’un ensemble de dossiers et de fichiers qui contiennent les ressources utilisées pour la traduction.

Par défaut, un projet nouvellement créé contiendra toutes les ressources nécessaires dans son dossier, et ces ressources se voient associer les noms par défaut ci-dessous.

-   [\#project.folder.source](#project.folder.source) contient les fichiers source

-   [\#project.folder.target](#project.folder.target) est l’emplacement où les fichiers cibles sont créés

-   [\#project.folder.glossary](#project.folder.glossary) contient les glossaires

-   [\#project.folder.glossary.txt](#project.folder.glossary.txt) est le glossaire modifiable du projet

-   [\#project.folder.tm](#project.folder.tm) contient les mémoires de traduction de référence

-   [\#project.folder.dictionary](#project.folder.dictionary) contient les dictionnaires de référence

Utilisez [\#menus.project](#menus.project)[\#menus.project.access.project.contents](#menus.project.access.project.contents) pour accéder au dossier du projet et à ses sous-dossiers.

Utilisez [\#menus.project](#menus.project)[\#menus.project.properties](#menus.project.properties) pour associer facilement aux différentes ressources des emplacements autres que ceux par défaut, soit lors de la création du projet, soit ultérieurement.

Par exemple, vous pouvez

-   créer les fichiers traduits dans un dossier partagé en dehors du dossier du projet, dans un endroit facilement accessible à votre réviseur, ou

-   utiliser un dossier de glossaire provenant d’un projet distinct mais connexe, ou

-   utiliser un dossier de mémoire de traduction de référence que vous avez créé pour des projets connexes, etc.

La création d’un projet lui confère une hiérarchie de base, mais sa structure finale n’est pas figée. Vous pouvez à tout moment supprimer ou ajouter des fichiers et des dossiers au projet.

Vous pouvez également créer des projets OmegaT manuellement ou à l’aide de scripts en copiant un ensemble de fichiers existants dans un nouveau dossier :

-   Tout dossier contenant un fichier `omegat.project` valide sera reconnu comme projet de traduction par OmegaT (même si des ajustements manuels sont nécessaires par la suite).

-   Si le dossier est un dépôt vide et que le fichier `omegat.project` contient des informations sur le dépôt distant, le projet sera reconnu par OmegaT comme un projet d’équipe :

        …
            <external_command></external_command>
            <repositories>
                <repository type="git" url="https://URL/DU/DÉPÔT/DU/PROJET/À/DISTANCE">
                    <mapping local="/" repository="/"/>
                </repository>
            </repositories>
        </project>
                  

    Voir le guide pratique [\#how.to.setup.team.project](#how.to.setup.team.project) pour en savoir plus.

## Contenu minimal

Un projet est un dossier contenant au minimum les éléments suivants:

omegat  
Il s’agit du dossier du projet qui contient toujours [\#project.folder.project.save.tmx](#project.folder.project.save.tmx), la mémoire de traduction du projet, et [\#project.folder.project.stats](#project.folder.project.stats), le fichier de données statistiques du projet.

D’autres fichiers seront ajoutés au cours de la traduction.

Voir [ci-dessous](#project.folder.omegat.folder) pour en savoir plus.

omegat.project  
Ce fichier contient les paramètres du projet définis dans les [propriétés du projet](#dialogs.project.properties), tels que les langues source et cible, leurs lemmatiseurs respectifs et le type de segmentation.

Il fait également office de *carnet d’adresses* indiquant où se trouvent les ressources du projet.

OmegaT crée également une sauvegarde de ce fichier (`omegat.project.bak`) et l’utilise automatiquement pour restaurer les paramètres du projet en cas de besoin.

## source

Le dossier source contient les fichiers à traduire.

Utilisez [\#menus.project](#menus.project)[\#menus.project.copy.files.to.source.folder](#menus.project.copy.files.to.source.folder) ou déposez des fichiers dans le volet [\#panes.editor](#panes.editor) pour ajouter des fichiers à tout moment.

Le contenu des fichiers dans un format pris en charge par OmegaT sera affiché dans le volet [\#panes.editor](#panes.editor) pour la traduction.

Vous pouvez ajouter des dossiers ou supprimer des fichiers à l’aide de votre gestionnaire de fichiers.

Si votre projet de traduction comporte plusieurs dossiers et que vous souhaitez travailler sur un dossier à la fois, utilisez [\#menus.project](#menus.project)[\#menus.project.properties](#menus.project.properties) pour accéder aux propriétés du projet et modifier le [dossier source](#dialogs.project.properties.file.locations.source.files) associé comme vous le souhaitez.

## target

À l’origine, ce dossier est vide.

Il sera alimenté par les fichiers traduits chaque fois que vous utiliserez [\#menus.project.create.translated.documents](#menus.project.create.translated.documents) ou [\#menus.project.create.current.translated.document](#menus.project.create.current.translated.document).

Les fichiers traduits correspondants au contenu du dossier [\#project.folder.source](#project.folder.source), qu’ils soient entièrement traduits ou non, sont alors créés ici, en utilisant la même hiérarchie que dans le dossier source.

Les fichiers créés ici reflètent l’état actuel de la traduction. Les segments non traduits resteront dans la langue source.

## tm

Ce dossier peut contenir un nombre quelconque de documents de référence bilingues (fichiers TMX, mais aussi tout fichier dans un format bilingue pris en charge par OmegaT, y compris les fichiers PO, etc.) et les fichiers TMX peuvent également être compressés au format gzip.

Il est possible de demander à OmegaT d’insérer automatiquement des correspondances. Pour vous rappeler qu’une correspondance a été insérée par OmegaT et non par vous, OmegaT ajoute le préfixe défini dans les paramètres [\#dialogs.preferences.editor.insert.the.best.fuzzy.match](#dialogs.preferences.editor.insert.the.best.fuzzy.match).

Les correspondances provenant des mémoires de référence sont affichées dans le volet [\#panes.fuzzy.matches](#panes.fuzzy.matches), tout comme les correspondances provenant de [\#project.folder.project.save.tmx](#project.folder.project.save.tmx), la mémoire de traduction du projet.

Ces correspondances sont par défaut limitées aux langues source et cible définies dans la boite de dialogue [\#dialogs.project.properties](#dialogs.project.properties), mais vous pouvez également ajouter des correspondances dans des langues autres que la langue cible. Voir les préférences [\#dialog.preferences.tm.matches.other.languages](#dialog.preferences.tm.matches.other.languages) pour en savoir plus.

Le dossier peut contenir un nombre illimité de sous-dossiers, dont certains ont des fonctions spéciales :

tm/auto  
Ce dossier est destiné aux fichiers de référence fiables qui peuvent remplir automatiquement les segments qui correspondent exactement et qui n’ont pas encore été traduits.

Les traductions des fichiers TMX placés dans ce dossier sont automatiquement insérées dans les segments correspondants sans le préfixe automatique, ce qui rend inutile la confirmation de ces segments.

Les traductions provenant de ce dossier sont considérées comme étant *aussi* fiables que la mémoire du projet.

Activez l’option [\#dialogs.preferences.editor.save.auto-populated.status](#dialogs.preferences.editor.save.auto-populated.status) pour qu’OmegaT se souvienne que les correspondances insérées proviennent de ce dossier.

1.  Placez les mémoires applicables dans le dossier `tm/auto`.

2.  Ouvrez le projet. Vous verrez que les segments identiques aux segments sources dans ces mémoires sont déjà remplis. Utilisez [\#menus.view](#menus.view)[\#menus.view.mark.auto.populated.segments](#menus.view.mark.auto.populated.segments) pour les surligner.

3.  Effectuez une modification mineure n’importe où dans le projet et enregistrez-la. Cela ajoutera les traductions chargées à partir du dossier tm/auto à la mémoire de traduction du projet.

Utilisez les menus de navigation qui se trouvent dans [\#menus.goto](#menus.goto)[\#menus.goto.auto.populated.segments](#menus.goto.auto.populated.segments) pour naviguer vers les segments insérés.

Si vous retirez un fichier TMX du dossier `tm/auto` avant l’étape 3, son contenu ne sera pas conservé.

tm/enforce  
Ce dossier est destiné aux fichiers de référence fiables qui ont également pour but d’écraser automatiquement les contenus précédemment traduits.

Les traductions des fichiers TMX placés dans ce dossier sont automatiquement insérées dans les segments correspondants sans le préfixe « correspondance partielle  », ce qui rend inutile la confirmation de ces segments.

Les traductions provenant de ce dossier sont considérées comme étant *plus* fiables que la mémoire actuelle du projet.

Si vous n’avez aucun doute sur le fait qu’un TMX donné contient des traductions plus précises que le fichier `project_save.tmx` actuel, placez ce TMX dans le dossier `tm/enforce` pour écraser les traductions existantes sans condition.

Activez l’option [\#dialogs.preferences.editor.save.auto-populated.status](#dialogs.preferences.editor.save.auto-populated.status) pour qu’OmegaT se souvienne que les correspondances insérées proviennent de ce dossier.

1.  Placez les mémoires applicables dans le dossier `tm/auto`.

2.  Ouvrez le projet. Vous verrez que les segments identiques aux segments sources dans ces mémoires sont déjà remplis.

3.  Effectuez une modification mineure n’importe où dans le projet et enregistrez-la. Cela met à jour la mémoire de traduction du projet.

4.  Prenez une décision concernant la pérennité des segments renforcés :

    -   S’ils *n’ont pas besoin* de rester immuables aux modifications ultérieures, supprimez la TMX de `tm/enforce`.

    -   S’ils *ont besoin* de rester immuables à d’autres changements, laissez le TMX dans `tm/enforce`. Toute modification des segments issus de ces mémoires ne sera *pas* prise en compte.

Utilisez les menus de navigation qui se trouvent dans [\#menus.goto](#menus.goto)[\#menus.goto.auto.populated.segments](#menus.goto.auto.populated.segments) pour naviguer vers les segments qui ont été insérés.

Si vous supprimez un fichier TMX de `tm/enforce` avant l’étape 3, aucune des traductions imposées ne sera conservée.

tm/mt  
Lorsqu’une correspondance est insérée à partir d’un TMX contenu dans ce dossier, la couleur d’arrière-plan du segment actuel devient rouge.

La couleur d’arrière-plan revient à la normale lorsque vous quittez le segment ou lorsque vous le modifiez.

tm/penalty-xxx  
`xxx` est un nombre de 0 à 100 qui agira comme une pénalité soustraite du pourcentage de concordance des segments provenant de ce dossier.

Par exemple, une correspondance de 100 % dans un TMX, stocké dans un dossier appelé `pénalité-30` devient une correspondance de 70 %. La pénalité s’applique aux trois pourcentages de correspondance. Les scores de 75, 80 et 90 pour une correspondance sont ramenés à 45, 50 et 60.

tm/tmx2source  
Vous pouvez afficher une troisième langue *directement sous* le segment source pour l’utiliser comme référence de troisième langue. Voir le guide pratique [\#how.to.tm.bridge.two.languages](#how.to.tm.bridge.two.languages) pour en savoir plus.

Vous pouvez combiner des dossiers pour créer de nouvelles fonctions. Par exemple, un dossier de pénalité de 10 % dans le dossier de traduction automatique : `tm/mt/penalty-010` ne génèrerait jamais de correspondances à 100 % qui pourraient autrement être insérées automatiquement par OmegaT, et placerait toujours un arrière-plan rouge sur la correspondance chaque fois qu’elle est insérée.

## dossier des mémoires de traduction exportées

Par défaut, ce dossier est le dossier du projet lui-même, mais vous pouvez modifier son emplacement pour rendre plus pratique le partage des fichiers TM exportés. Voir le guide pratique [\#how.to.tm.share.translation.memories](#how.to.tm.share.translation.memories) pour en savoir plus.

## dictionary

Ce dossier est initialement vide et sert à stocker tous les dictionnaires que vous ajoutez au projet.

Les termes du dictionnaire qui correspondent à des parties du segment sont affichés dans le volet [\#panes.dictionary](#panes.dictionary). Voir les préférences [\#dialogs.preferences.dictionary](#dialogs.preferences.dictionary) pour en savoir plus.

OmegaT prend en charge les dictionnaires au format StarDict ou Lingvo DSL. Vous pouvez trouver certains dictionnaires sur le [Wiki OmegaT](https://sourceforge.net/p/omegat/wiki/Reference%20Material/).

Pour installer les dictionnaires :

1.  Téléchargez le fichier. Ce devrait être un fichier d’archive tarball (extension `tar.bz` ou `tar.bz2`).

2.  extrayez son contenu dans ce dossier. Il devrait y avoir trois fichiers par dictionnaire, avec les extensions `dz`, `idx` et `ifo`.

Si vous souhaitez supprimer des mots des correspondances potentielles du dictionnaire, ajoutez un fichier `ignore.txt` codé en UTF-8 au dossier. Le fichier doit contenir un mot par ligne. Tous les mots contenus dans cette liste seront ignorés par OmegaT.

## glossary

À l’origine, ce dossier est vide. Il est utilisé pour stocker le glossaire modifiable par défaut et tout autre glossaire utilisé dans le projet.

Les termes du glossaire qui correspondent à des parties du segment sont affichés dans le volet [\#panes.glossary](#panes.glossary). Voir l’annexe [\#app.glossaries](#app.glossaries) pour en savoir plus.

glossary.txt  
C’est le glossaire modifiable du projet Il est créé la première fois que vous l’utilisez [\#menus.edit.create.glossary.entry](#menus.edit.create.glossary.entry).

Vous pouvez y accéder avec [\#menus.project.access.project.contents.title](#menus.project.access.project.contents.title), l’ouvrir dans un éditeur de texte, le modifier avec un éditeur de texte. Dès que vous aurez enregistré vos modifications, elles seront prises en compte par OmegaT.

## omegat

Le dossier `omegat` contient, au minimum, les fichiers [\#project.folder.project.save.tmx](#project.folder.project.save.tmx) et [\#project.folder.project.stats](#project.folder.project.stats). Il peut également contenir plusieurs autres fichiers.

project\_save.tmx  
Il s’agit du fichier le plus important du projet. Lorsque vous créez un nouveau projet, le fichier est vide et se remplit progressivement avec les traductions du texte dans les fichiers situés dans le dossier [\#project.folder.source](#project.folder.source).

Il constitue la mémoire de traduction de travail du projet.

OmegaT effectue régulièrement des sauvegardes de ce fichier.\* Voir le guide pratique [\#how.to.restore.your.data](#how.to.restore.your.data) pour en savoir plus.

project\_save.tmx.bak  
Ce fichier est une sauvegarde de `projet_save.tmx` et est automatiquement recréé chaque fois que `projet_save.tmx` a été modifié : soit après avoir utilisé [\#menus.project](#menus.project)[\#menus.project.save](#menus.project.save), soit en tant que sauvegarde régulière toutes les 3 minutes par défaut. Voir le paramètre [\#dialog.preferences.saving.and.output.interval](#dialog.preferences.saving.and.output.interval) pour en savoir plus.

project\_save.tmx.timestamp.bak  
Chaque fois qu’un projet est chargé, OmegaT crée une sauvegarde de `project_save.tmx` avec le nom `project_save.tmx.[horodatage].bak`. OmegaT conserve jusqu’à 10 de ces fichiers.

project\_stats.txt  
Il s’agit du fichier de statistiques pour l’ensemble du projet. Il est mis à jour à chaque fois que le projet est rechargé.

Utilisez [\#menus.tools](#menus.tools)[\#menus.tools.statistics](#menus.tools.statistics) pour le mettre à jour.

Le fichier project\_stats\_match.txt  
Ce fichier contient les dernières statistiques de correspondance du projet. Utilisez [\#menus.tools](#menus.tools)[\#menus.tools.match.statistics](#menus.tools.match.statistics) pour le générer.

project\_stats\_match\_per\_file.txt  
Ce fichier contient les dernières statistiques de correspondance du projet par fichier. Utilisez [\#menus.tools](#menus.tools)[\#menus.tools.match.statistics.per.file](#menus.tools.match.statistics.per.file) pour le générer.

ignored\_words.txt.; learned\_words.txt  
Ces fichiers sont créés et utilisés par le correcteur orthographique. Vous pouvez ajouter des termes dans le volet [\#panes.editor](#panes.editor) en cliquant avec le bouton droit de la souris sur un mot marqué comme incorrect et en sélectionnant Ignorer tout (pour les mots à ignorer pendant la vérification orthographique), ou Ajouter au dictionnaire (pour les mots à accepter comme corrects), respectivement, à partir du [menu contexte](#panes.editor.context.menu). Voir les préférences [\#dialog.preferences.spellchecker](#dialog.preferences.spellchecker) pour en savoir plus.

Si vous disposez déjà d’une collection de mots que vous souhaitez que le correcteur orthographique ignore ou accepte, il vous suffit de les enregistrer dans des fichiers texte portant les noms correspondants et de copier ces fichiers dans le dossier [\#project.folder.omegat.folder](#project.folder.omegat.folder) de votre projet en cours.

segmentation.conf  
Ce fichier contient les règles de segmentation spécifiques au projet.

filters.xml  
Ce fichier contient les filtres de fichiers spécifiques au projet.

uiLayout.xml  
Ce fichier contient les paramètres de l’interface graphique spécifiques au projet.

finder.xml  
Ce fichier contient les recherches externes spécifiques au projet.

files\_order.txt  
Ce fichier est créé si vous modifiez manuellement l’ordre des fichiers dans la fenêtre [\#windows.source.files.list](#windows.source.files.list).

last\_entry.properties  
Ce fichier conserve une trace du dernier segment visité, y compris son numéro, son contenu source, le nom du fichier et la date, afin que vous puissiez y revenir lorsque vous rechargez/relancez le projet.

## .repositories

Dans le cas d’un projet en équipe, ce dossier contient une copie versionnée de l’arborescence du projet, en liaison directe avec le serveur distant.

Vous pouvez apporter des modifications aux fichiers distants (comme les supprimer ou les remplacer) en effectuant vos modifications dans ce dossier et en utilisant un client Git ou SVN pour les synchroniser avec le serveur distant. Voir le guide pratique [\#how.to.setup.team.project](#how.to.setup.team.project) pour en savoir plus.

Dans certains systèmes d’exploitation, ce dossier est caché par défaut. Activez l’option d’affichage des fichiers cachés de votre système pour le rendre visible.
