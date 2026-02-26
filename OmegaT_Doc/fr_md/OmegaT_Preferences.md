# Préférences

Utilisez [\#menus.options](#menus.options)[\#menus.options.preferences](#menus.options.preferences) pour accéder à cette boite de dialogue (le menu `OmegaT` sur macOS).

Utilisez le champ de recherche en haut de la liste des préférences pour rechercher des éléments spécifiques.

Les préférences définies dans cette boite de dialogue sont enregistrées dans le [dossier de configuration](#configuration.folder) par défaut et s’appliquent à tous les projets de traduction, sauf si vous avez spécifié un dossier de configuration différent.

Il est possible de demander à OmegaT d’utiliser un dossier de configuration différent pour définir des configurations spécifiques à un projet. Voir la section [\#launch.with.command.line](#launch.with.command.line) pour en savoir plus. Si vous sélectionnez un tel dossier de configuration, toutes les modifications effectuées dans cette boite de dialogue y seront stockées.

## Paramètres généraux

`Utiliser TAB pour valider`  
La touche par défaut pour valider et quitter un segment est Entrée.

Cette option définit la touche de validation de segment comme étantTab.

Cette option est utile avec certains systèmes de saisie de caractères chinois, japonais ou coréens.

`Quitter toujours confirmé`  
Le programme demandera une confirmation avant la fermeture.

`Accéder au dossier de configuration`  
Ouvrir le dossier local où sont stockés les fichiers de configuration d’OmegaT.

L’emplacement dépend du système d’exploitation et des options de lancement. Voir l’annexe [\#configuration.folder](#configuration.folder) pour en savoir plus.

## Traduction automatique

`Récupérer automatiquement les traductions`  
Si vous désactivez cette option, les traductions automatiques ne seront récupérées que lorsque vous utiliserez [\#menus.edit](#menus.edit)[\#menus.edit.replace.with.mt](#menus.edit.replace.with.mt) dans le segment actuel. Vous devrez alors appuyer à nouveau sur cette combinaison pour insérer la suggestion.

`Uniquement les segments non traduits`  
Cochez cette case pour envoyer seulement des segments non traduits aux services de traduction automatique.

`Liste des fournisseurs`  
Dans la liste des traducteurs automatiques disponibles dans OmegaT, cochez la case Activé pour chaque fournisseur auquel vous souhaitez accéder. Utilisez le bouton Configurer pour gérer vos informations d’authentification pour ce fournisseur.

La plupart des fournisseurs exigent une certaine forme d’enregistrement avant d’utiliser leurs services. Assurez-vous que vous disposez des informations d’identification nécessaires avant d’utiliser cette fonction.

<table>
<caption><code>Références requises</code></caption>
<thead>
<tr class="header">
<th style="text-align: left;">Moteur</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;">Belazar</td>
</tr>
<tr class="even">
<td style="text-align: left;">DeepL</td>
</tr>
<tr class="odd">
<td style="text-align: left;">MyMemory (traduction automatique)</td>
</tr>
<tr class="even">
<td style="text-align: left;">Apertium</td>
</tr>
<tr class="odd">
<td style="text-align: left;">MyMemory (traduction humaine)</td>
</tr>
<tr class="even">
<td style="text-align: left;">IBM Watson</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Google Translate v2</td>
</tr>
</tbody>
</table>

`Références requises`

## Glossaires

`Afficher la description du contexte des glossaires TBX (TBX 2)`  
Décochez cette option si la description du contexte donné pour chaque entrée de glossaire est inutile ou trop longue.

`Faire correspondre des groupes de termes même si les termes apparaissent séparément`  
Lorsqu’un terme du glossaire est un mot composé, le terme correspondra même si les mots apparaissent séparément dans le texte source.

`Utiliser la lemmatisation`  
OmegaT utilisera le lemmatiseur associé pour trouver des correspondances.

`Remplacer les correspondances lors de l’insertion d’un texte source`  
Quand vous utilisez

-   [\#menus.edit](#menus.edit)[\#menus.edit.replace.with.source](#menus.edit.replace.with.source),

-   [\#menus.edit](#menus.edit)[\#menus.edit.insert.source](#menus.edit.insert.source) ou

-   la préférence [\#dialogs.preferences.editor.insert.the.source.text](#dialogs.preferences.editor.insert.the.source.text), etc.

pour insérer le contenu source dans le segment cible, les mots ayant une entrée dans le glossaire seront automatiquement remplacés par leur traduction.

`Ignorer les correspondances dont la casse est très différente (par exemple, OMEGAT vs omegat)`  
Les correspondances avec des cas sans similitudes ne sont pas affichées.

`Mise en page`  
Sélectionnez une mise en page pour le volet des glossaires. Des mises en page supplémentaires peuvent être ajoutées sous forme d’extensions.

`Fusionner les définitions alternatives d’un même terme`  
Si un élément de glossaire comporte plusieurs définitions, celles-ci seront affichées sur la même ligne.

## Dictionnaires

Les préférences définissent ici la manière dont le contenu du dossier [\#project.folder.dictionary](#project.folder.dictionary) est affiché dans le volet [\#panes.dictionary](#panes.dictionary).

`Recherche automatique`  
Lorsque l’option est désactivée, utilisez [\#menus.edit](#menus.edit)[\#menus.edit.search.dictionaries](#menus.edit.search.dictionaries) pour rechercher les correspondances dans la sélection ou de tous les termes dans la source du segment.

Lorsque l’option est activée, OmegaT recherche automatiquement dans tous les dictionnaires les correspondances avec les termes qu’il a identifiés dans le segment, au fur et à mesure de sa progression dans le segment.

`Utiliser la lemmatisation`  
OmegaT utilisera le lemmatiseur associé pour trouver des correspondances.

`Vue condensée`  
Certains pilotes de dictionnaires fournis sous forme de modules d’extension ne prennent pas en charge cette fonctionnalité.

## Apparence

`Thème`  
Sélectionner un thème pour l’interface graphique d’OmegaT.

Des thèmes supplémentaires peuvent être ajoutés sous forme de modules d’extensions. Les thèmes fournissent également un ensemble prédéfini de couleurs par défaut.

Tous les thèmes Java fournis de base ne sont pas compatibles avec le fonctionnement d’OmegaT.

`Réinitialiser la fenêtre d’OmegaT`  
Rétablit la disposition par défaut des fenêtres d’OmegaT.

Utilisez cette fonction lorsque vous ne parvenez pas à rétablir la disposition souhaitée après avoir supprimé, déplacé ou masqué une ou plusieurs fenêtres. Vous pouvez l’utiliser lorsque les fenêtres n’apparaissent pas comme prévu après une mise à jour d’OmegaT.

### Police

Sélectionnez la police et la taille de la police utilisées pour afficher le texte dans les volets de la fenêtre principale.

OmegaT utilise la même police de caractères pour la langue source et la langue cible. Si vous travaillez dans une paire de langues utilisant des systèmes d’écriture différents, veillez à choisir une police qui permet d’afficher correctement les deux langues. Les caractères qui ne sont pas pris en charge apparaissent sous forme de carrés.

`Appliquer cette police aux données tabulaires (fichiers de projet, statistiques, etc.)`  
Les données tabulaires sont affichées par défaut dans une police de caractères unique qui permet d’aligner correctement les colonnes. L’utilisation d’une police proportionnelle rompra cette disposition.

`Appliquer une taille de police différente à la fenêtre des dictionnaires`  
Par défaut, la fenêtre des dictionnaires utilise la même taille de police que la fenêtre principale.

### Couleurs

Vous pouvez associer des couleurs différentes aux diverses parties de l’interface graphique.

Les scripts peuvent être utilisés pour définir des thèmes prédéfinis. OmegaT est livré avec un script appelé [\#windows.scripts.distribution.switch.colour.theme](#windows.scripts.distribution.switch.colour.theme) qui fournit un thème sombre par défaut. Voir la fenêtre [\#windows.scripts](#windows.scripts) pour en savoir plus.

La détection automatique des thèmes sombres est disponible sur les systèmes Linux avec la présentation Gnome/GTK pour les personnes qui exécutent OmegaT sur OpenJDK. Cette fonction dépend d’une fonctionnalité Java qui n’est pas encore disponible sur d’autres plates-formes.

## Filtres de fichiers généraux

Cette boite de dialogue répertorie les filtres de fichiers disponibles pour les projets qui n’utilisent pas de filtres de fichiers locaux.

Le contenu de cette préférence est identique au contenu de la boite de dialogue [filtres de fichiers locaux](#dialogs.project.properties.filters). Voir l’annexe [\#file.filters](#file.filters) pour en savoir plus.

Si des filtres de fichiers locaux sont utilisés, la modification des filtres de fichiers généraux n’aura aucun effet sur le projet.

## Règles globales de segmentation

Voir l’annexe [\#app.segmentation](#app.segmentation) pour une explication générale de la segmentation (globale ou locale, paragraphe ou phrase, etc.)

Cette boite de dialogue ne permet d’accéder qu’aux règles de segmentation globales. Si vous avez défini des règles locales dans la boite de dialogue [\#dialogs.project.properties](#dialogs.project.properties), les modifications apportées ici ne seront pas prises en compte.

### Règles par langue

Seules les règles associées aux modèles de langue qui correspondent à la langue source de votre projet sont appliquées. Voir les propriétés du projet [\#dialogs.project.properties.languages](#dialogs.project.properties.languages).

Dans le cas d’une traduction à partir du japonais, *seuls* l’ensemble de règles associé au masque `JA.*` et les ensembles de règles génériques associés au motif `.*` seront pris en compte.

Lorsque vous cliquez sur un masque de langue dans la partie supérieure de la boite de dialogue, une liste de règles associées s’affiche dans la partie inférieure de la boite de dialogue.

Tous les ensembles de règles de segmentation pour un modèle de langue correspondant sont actifs et sont appliqués dans l’ordre. Les règles pour des langues spécifiques doivent être plus élevées que les règles par défaut.

Les règles pour *FR-CA* doivent être plus élevées que celles pour *FR.\**, qui doivent elles-mêmes être plus élevées que l’ensemble générique *.\**.

Ainsi, lors d’une traduction à partir du français canadien, les règles pour le français canadien - s’il y en a - s’appliqueront en premier, suivies par les règles pour le français et, enfin, par les règles génériques.

Pour créer un nouvel ensemble de règles :

1.  Cliquez sur ajouter. Une ligne vide apparait en bas du tableau.

2.  Modifiez le nom de l’ensemble de règles et du masque linguistique en fonction de l’étiquette souhaitée et du masque correspondant. Le masque linguistique est une expression régulière.

3.  Utilisez le bouton Glisser vers le haut pour définir la priorité de l’ensemble de règles.

### Contenu des règles

Les règles d’exception doivent être listées *au-dessus* des règles de segmentation.

Lors de la lecture des fichiers, OmegaT place un marqueur de non-rupture à chaque emplacement d’exception. Les endroits qui n’ont pas de tels marqueurs et qui correspondent à des règles de rupture seront des emplacements de rupture.

`Exceptions`  
Pour définir une règle d’exception, ne cochez pas la case Segmentation/Exception .

Indiquez les combinaisons de textes qui constituent des exceptions à une règle de segmentation. Par exemple, *Mrs. Dalloway* ne doit pas être divisé en deux segments, même si une règle de césure pour un *point suivi d’une espace* définit généralement une phrase.

`Segmentations`  
Pour définir une règle de segmentation, cochez la case Segmentation.

Sépare le texte source en segments. Par exemple, un *point suivi d’une espace* définit généralement une fin de phrase en anglais.

Ajouter  
Le masque **Avant** identifie les parties qui se trouvent avant le point de segmentation ou d’exception.

Le masque **Après** identifie les parties qui se trouvent après le point de segmentation ou d’exception.

Les masques **Avant** et **Après** sont des expressions régulières. Voir l’annexe [\#app.regex](#app.regex) pour en savoir plus.

Les règles existantes constituent toujours un bon point de départ.

## Saisie automatique

Le menu de saisie automatique est disponible dans le volet [\#panes.editor](#panes.editor). Voir la section [\#panes.editor.auto.completion.menu](#panes.editor.auto.completion.menu) pour en savoir plus.

Cliquez sur Glossaire pour configurer l’affichage du glossaire de la saisie automatique.

Cliquez sur Texte automatique pour configurer les options du texte automatique et pour ajouter ou supprimer des entrées.

Cliquez sur Table de caractères pour définir les options de la table de caractères de la saisie automatique.

Cliquez sur Activer la saisie historique ou Activer la prédiction de l’historique pour définir des saisies basées sur l’historique.

Aucune de vos données (historique, etc.) n’est *jamais* envoyée par OmegaT à un serveur externe pour y être traitée. Tous les résultats de prédiction/saisie sont traités localement.

Si l’option Afficher automatiquement les suggestions pertinentes est cochée, la saisie automatique s’ouvre automatiquement en saisissant la première lettre de la traduction d’une entrée de glossaire ou un entrant `<` dans le cas des balises.

## Vérificateur orthographique

OmegaT dispose d’un vérificateur d’orthographe intégré, mais nécessite l’installation de dictionnaires de vérification orthographique basés sur les langues cibles.

OmegaT utilisera le dictionnaire de langue qui porte le même nom que le code de la langue cible défini dans la propriété de projet [\#dialogs.project.properties.languages](#dialogs.project.properties.languages). Un dictionnaire *FR-FR* ne vérifiera pas l’orthographe des segments cibles *FR*. Si nécessaire, modifiez le nom du dictionnaire ou changez les paramètres linguistiques de votre projet.

`Vérifier l’orthographe de la traduction`  
Activé après l’installation d’un dictionnaire de vérification orthographique. OmegaT souligne les fautes d’orthographe par des lignes rouges ondulées.

Utilisez le [menu contextuel de l’éditeur](#panes.editor.context.menu) pour corriger l’erreur, Ignorer tout ou pour Ajouter au dictionnaire. Voir [fichiers de vérification orthographique](#project.folder.omegat.spellcheck) pour en savoir plus.

`Emplacement des dictionnaires de vérification orthographique`  
Le dossier dans lequel OmegaT installera et recherchera des dictionnaires d’orthographe. Il se trouve généralement dans le dossier [\#configuration.folder](#configuration.folder).

`Langues disponibles`  
La liste des dictionnaires présents dans le dossier ci-dessus.

Si aucun n’est affiché, cela signifie que vous n’avez pas encore installé de dictionnaire orthographique ou que votre projet utilise un dossier de configuration spécifique qui ne contient pas encore de dictionnaire orthographique.

`URL des dictionnaires orthographiques téléchargeables :`  
L’URL par défaut où OmegaT cherchera les dictionnaires à installer.

Vous pouvez également télécharger des dictionnaires à partir d’autres emplacements ou copier des dictionnaires installés localement.

Installer un nouveau dictionnaire…  
Affiche la liste des dictionnaires disponibles à partir de l’URL ci-dessus.

Cette action nécessite une connexion internet

Sélectionnez les dictionnaires que vous souhaitez installer et cliquez sur Installer. Selon votre connexion internet, l’installation du dictionnaire peut prendre un certain temps.

## LanguageTool

`Type de service`  
Choisissez l’emplacement du vérificateur linguistique.

En utilisant un autre vérificateur linguistique (différent de celui fourni avec OmegaT) sur votre machine locale, vous pouvez personnaliser les règles de vérification.

`Règles`  
Cochez ou décochez les règles en fonction de leur pertinence dans le type de texte que vous traduisez.

## Recherches externes globales

Les recherches externes sont des recherches sur le web ou des commandes locales qui prennent comme paramètre la chaine de caractères sélectionnée dans l’Éditeur. Les recherches sur le web sont ouvertes dans le navigateur par défaut et les commandes sont équivalentes aux éléments lancés sur la ligne de commande.

`Autoriser les commandes de recherche externes locales`  
Pour des raisons de sécurité, les [recherches externes locales](#dialogs.project.properties.external.searches) sont désactivées par défaut.

Les commandes de recherche externe locale sont enregistrées dans le fichier [\#project.folder.omegat.filters](#project.folder.omegat.filters). N’activez cette option que si vous avez confiance en la source de ce fichier.

`Priorité du menu contextuel`  
Cette option vous permet de modifier l’ordre des commandes dans le [menu contextuel](#panes.editor.context.menu) du volet Éditeur. Les valeurs autour de 100 affichent les commandes en haut, celles autour de 900 les affichent en bas.

Redémarrer OmegaT pour appliquer cette modification.

`Configurations`  
Chaque configuration représente un groupe de recherches sur le web ou de commandes locales lancées simultanément.

Chaque configuration doit être nommée. Le nom apparaitra à la fin du menu [\#menus.tools](#menus.tools).

Si vous cochez la case Afficher dans le menu contextuel de l’Éditeur, le nom de la configuration sera également affiché dans le [menu contextuel](#panes.editor.context.menu) si une chaine de caractères est sélectionnée.

Les recherches par URL ainsi que les commandes doivent contenir la chaine `{target}` pour être acceptées. Le caractère générique `{target}` sera remplacé par la chaine sélectionnée dans l’Éditeur.

Les URL sont ouvertes avec le navigateur web par défaut, un par onglet.

    https://duckduckgo.com/?q=%22{target}%22+site%3A.fr+-linguee

Cela ouvre une recherche pour le terme {target} sur DuckDuckGo avec un certain nombre de paramètres de recherche.

Les commandes sont ouvertes sur la ligne de commande. Le Séparateur définit le séparateur entre les paramètres de commande. Le séparateur par défaut est `|`.

    /usr/bin/open|dict://{terme}

Cela ouvre l’application du dictionnaire qui met en œuvre le protocole `dict` sur votre ordinateur, à la recherche du terme {terme}.

## Éditeur

En entrant dans un segment vide :

`Insérer le texte source`  
Utilisez cette option temporairement pour les parties de la traduction qui ne nécessitent pas beaucoup de transformation.

`Laisser le segment vide`  
Vous pouvez entrer votre traduction immédiatement.

`Insérer la meilleure correspondance partielle`  
OmegaT insère la traduction dont le pourcentage de correspondance est le plus élevé par rapport à la valeur définie dans cette boite de dialogue.

Le préfixe identifie les traductions insérées en tant que correspondances partielles. Vous pouvez également enregistrer le préfixe dans la préférence [\#dialogs.preferences.tag.processing.regular.expressions.for.fragments.that.should.be.removed.from.translation](#dialogs.preferences.tag.processing.regular.expressions.for.fragments.that.should.be.removed.from.translation) pour l’inclure dans le processus de vérification des balises et vous assurer de ne pas l’oublier dans votre traduction.

<!-- -->

`Tenter de remplacer les chiffres des correspondances`  
Lorsqu’une correspondance est insérée, OmegaT tente de remplacer les chiffres de la correspondance par les chiffres du texte source.

Seuls les nombres entiers et les nombres flottants simples (par exemple, 5,4) sont pris en compte.

2001 dans la source :

    [[2001年]]、ドイツの永住権を取得。

2003 dans la correspondance partielle :

    [[2003年]]、ドイツの永住権を取得。
    [[2003]], elle acquiert la nationalité allemande.

Lorsque la correspondance est insérée, OmegaT convertit 2003 en 2001 :

    [[2001]], elle acquiert la nationalité allemande.

`Autoriser une traduction identique à la source`  
Une traduction identique au texte source n’est pas reconnue comme une traduction par défaut. OmegaT l’effacera et considérera le segment comme non traduit.

Cette option permet de forcer OmegaT à enregistrer ces entrées et à les compter comme traduites.

`Exporter le segment dans un fichier texte`  
Lorsque OmegaT entre dans un segment,

-   le contenu de la partie source est copié dans le fichier [\#configuration.folder.default.contents.script.source](#configuration.folder.default.contents.script.source),

-   le contenu de la partie cible (le cas échéant) est copié dans le fichier [\#configuration.folder.default.contents.script.target](#configuration.folder.default.contents.script.target),

tous deux situés dans le [dossier de script](#windows.scripts.folder).

Cette fonction n’a aucun rapport avec la fonction [\#windows.scripts](#windows.scripts).

Les fichiers sont écrasés lorsque OmegaT entre dans un nouveau segment.

Le script [\#windows.scripts.distribution.extract.text.content](#windows.scripts.distribution.extract.text.content) fait quelque chose de similaire, mais pour l’ensemble du projet en une seule fois. Voir la fenêtre [\#windows.scripts](#windows.scripts).

`Arrêt sur les traductions non traduites et alternatives`  
[\#menus.goto](#menus.goto)[\#menus.goto.next.untranslated.segment](#menus.goto.next.untranslated.segment) s’arrête également sur les segments comportant des traductions alternatives.

`Autoriser la modification des balises`  
Les balises ne devraient généralement pas être modifiées, mais cela est possible lorsque cette option est activée.

`Vérifier les problèmes en quittant un segment`  
OmegaT effectue une vérification des problèmes sur le segment lorsque vous le quittez. Cette option est équivalente à l’utilisation de [\#menus.tools](#menus.tools)[\#menus.tools.check.issues](#menus.tools.check.issues).

`Enregistrer l’état autotraduit`  
Les mémoires de traduction situées dans [\#project.folder.tm.auto](#project.folder.tm.auto) et [\#project.folder.tm.enforce](#project.folder.tm.enforce) peuvent alimenter automatiquement la mémoire du projet. Les segments qui reçoivent une traduction automatique à ce moment-là peuvent être marqués dans le volet Éditeur en utilisant [\#menus.view](#menus.view).[\#menus.view.mark.auto.populated.segments](#menus.view.mark.auto.populated.segments).

Voir le guide pratique [\#how.to.use.tm.reuse.tm](#how.to.use.tm.reuse.tm) pour en savoir plus.

`Enregistrer l’origine de la traduction`  
Lorsque la traduction automatique est activée, OmegaT enregistre le nom du moteur qui a été utilisé pour remplir un segment donné.

`Nombre initial de segments chargés`  
L’éditeur charge et affiche initialement 2 000 segments et en charge progressivement davantage à mesure que vous défilez vers le haut ou vers le bas. Modifiez ce nombre en fonction des performances de votre machine.

`Format de la délimitation des paragraphes`  
Utilisez [\#menus.view](#menus.view)[\#menus.view.mark.paragraph.delimitations](#menus.view.mark.paragraph.delimitations) pour identifier les segments qui appartiennent au même paragraphe.

## Traitement des balises

`Vérifier les variables de la fonction printf`  
Vérifier les variables printf dans les formats de fichiers autres que le format PO. Le filtre PO traite déjà les variables marquées avec `%`.

Vous pouvez sélectionner

`Aucun`  
Aucun des modèles de variables n’est vérifié.

`Variables simples (par exemple, %s, %d)`  
Seuls les modèles de variables simples sont vérifiés.

`Toutes les variables (par exemple, %s, %-s)`  
Cela peut entrainer des faux positifs dans certains fichiers.

`Vérifier les caractères de remplacement Java MessageFormat simples`  
Vérifier les caractères génériques Java MessageFormat dans les formats de fichiers autres que le format Java Bundles. Le filtre Java Bundles traite déjà les caractères génériques marqués par `{#}` où `#` est un nombre.

`Autoriser un ordre différent pour les balises traduites`  
Les balises dont l’ordre est différent de celui de la source n’apparaitront pas dans la liste des questions relatives aux balises. Voir le menu [\#menus.tools](#menus.tools)[\#menus.tools.check.issues](#menus.tools.check.issues) pour plus de détails.

`Bloquer la création de fichiers traduits avec des problèmes de balises`  
Si vous essayez de créer les fichiers traduits, OmegaT affichera la boite de dialogue des problèmes jusqu’à ce qu’aucun problème ne soit trouvé. Voir le menu [\#menus.tools](#menus.tools)[\#menus.tools.check.issues](#menus.tools.check.issues) pour plus de détails.

`Compter les textes signalés et les balises personnalisées dans les statistiques`  
Contrairement aux balises d’OmegaT, les textes signalés et les balises personnalisées sont par défaut pris en compte dans les statistiques. Voir le menu [\#menus.tools](#menus.tools)[\#menus.tools.statistics](#menus.tools.statistics) pour plus de détails.

`Balises personnalisées`  
Utilisez des expressions régulières pour définir des balises personnalisées. Pour définir une liste de balises, regroupez chaque balise entre parenthèses et séparez les groupes par `|` (équivalent à "OU" dans les expressions régulières).

Par exemple, utilisez `\d+` pour traiter tous les nombres comme des balises, ce qui vous permet de vérifier que les nombres n’ont pas été modifiés accidentellement dans la traduction.

De même, utilisez `</ ?[^>]+>` pour vous assurer que les balises HTML (ou similaires) introduites dans le texte source sont conservées sans modification dans la traduction.

Utilisez des parenthèses et `|` pour qu’OmegaT prenne en compte les deux balises : `(\d+)|(</ ?[^>]+>)`.

Voir l’annexe [\#app.regex](#app.regex) pour en savoir plus.

`Texte signalé`  
Le texte dans le segment cible qui correspond à cette expression est coloré en rouge et est identifié comme étant une balise superflue dans le cadre de l’affichage des erreurs. Voir le menu [\#menus.tools](#menus.tools)[\#menus.tools.check.issues](#menus.tools.check.issues) pour plus de détails.

## Équipe

Le nom que vous saisissez ici sera attaché à tous les segments que vous traduisez.

`Informations d’identification du dépôt`  
Liste des projets pour lesquels les données de connexion ont été enregistrées dans OmegaT. Supprimez un projet de cette liste si vous souhaitez qu’OmegaT vous demande ses identifiants lors de votre prochain accès.

## `Correspondances`

`Trier les correspondances partielles par :`  
Par défaut, la lemmatisation est utilisée pour déterminer les correspondances les plus proches affichées dans le volet Correspondances.

Pour avoir des correspondances plus littérales et proches de 100 %, sélectionnez plutôt l’option Texte complet, y compris balises et nombres.

`Seuil minimal pour afficher une correspondance partielle`  
Par défaut, OmegaT affiche les cinq meilleures correspondances partielles au-delà de 30 %. Vous pouvez modifier le seuil ici.

Chacun des trois types de pourcentages de concordance présentés dans le volet [\#panes.fuzzy.matches](#panes.fuzzy.matches) est pris en compte pour déterminer si une concordance est affichée. Les correspondances potentielles sont rejetées si les trois pourcentages sont inférieurs au seuil.

`Sélectionner la façon dont les balises des TMX non produites par OmegaT doivent être affichées`  
Déterminez comment traiter les balises dans les fichiers TMX générés par d’autres outils.

Vous pouvez choisir de les afficher ou non et d’utiliser la notation XML standard pour les balises autonomes (par exemple, &lt;i/&gt;).

`Inclure les correspondances dans d’autres langues`  
Les segments qui ont des correspondances dans différentes langues cibles peuvent également être affichés dans le volet [\#panes.fuzzy.matches](#panes.fuzzy.matches). Vous pouvez appliquer une pénalité à ces correspondances.

`Modèle d’affichage d’une correspondance`  
Changez la façon dont les correspondances sont affichées en utilisant des variables prédéfinies.

La valeur par défaut est :

    ${id} ${fuzzyFlag}${sourceText} ${targetText}
    <${score}/${noStemScore}/${adjustedScore}%
    ${filePath}>

Voici une alternative possible :

    ⥤ ${id}. <${score}/${noStemScore}/${adjustedScore}%> ${fuzzyFlag} ${fileNameOnly}
    [NEW]▷ ${diff}
                
    [OLD]◀ ${diffReversed}
    ◀ ${targetText}

Les variables du modèle sont également disponibles dans un menu déroulant et peuvent être insérées à l’aide d’un bouton.

<table>
<caption>Faire correspondre les variables du modèle</caption>
<tbody>
<tr class="odd">
<td style="text-align: left;"><code>${id}</code></td>
<td style="text-align: left;">Nombre de la correspondance compris entre 1 et 5</td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>${sourceText}</code></td>
<td style="text-align: left;">Texte source de la correspondance</td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>${diff}</code></td>
<td style="text-align: left;">chaine de caractères indiquant les différences entre la source et la correspondance.</td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>${diffReversed}</code></td>
<td style="text-align: left;">Identique à ${diff}, mais avec les différences (ce qui doit être inséré et supprimé) inversées.</td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>${targetText}</code></td>
<td style="text-align: left;">Texte cible de la correspondance</td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>${score}</code></td>
<td style="text-align: left;">Pourcentage calculé avec l’option Lemmatisation, aucune balise et aucun nombre.</td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>${noStemScore}</code></td>
<td style="text-align: left;">Pourcentage calculé avec l’option Aucune balise et aucun nombre.</td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>${adjustedScore}</code></td>
<td style="text-align: left;">Pourcentage calculé avec l’option Texte complet, y compris balises et nombres.</td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>${fileNameOnly}</code></td>
<td style="text-align: left;">Le nom du fichier de mémoire de traduction, sans l’extension.</td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>${filePath}</code></td>
<td style="text-align: left;">Le chemin d’accès complet au fichier de mémoire de traduction.</td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>${fileShortPath}</code></td>
<td style="text-align: left;">Le chemin d’accès relatif au fichier de mémoire de traduction.</td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>${initialCreationID}</code></td>
<td style="text-align: left;">L’identité de la personne qui a créé le segment.</td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>${initialCreationDate}</code></td>
<td style="text-align: left;">Date de création du segment.</td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>${changeID}</code></td>
<td style="text-align: left;">L’identité de la personne qui a modifié le segment pour la dernière fois.</td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>${changeDate}</code></td>
<td style="text-align: left;">La date de la dernière modification du segment.</td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>${fuzzyFlag}</code></td>
<td style="text-align: left;">Indique que la correspondance est partielle (pour le moment, existe uniquement pour les fichiers PO possédant la marque #correspondance partielle)</td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>${sourceLanguage}</code></td>
<td style="text-align: left;">La langue source du segment.</td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>${targetLanguage}</code></td>
<td style="text-align: left;">La langue cible du segment.</td>
</tr>
</tbody>
</table>

Faire correspondre les variables du modèle

## Affichage

`Afficher tous les segments source en gras`  
Par défaut, seul le segment en cours est affiché en gras.

`Afficher le segment source actif en gras`  
Si les segments source sont ne sont pas affichés en gras, vous pouvez utiliser cette option pour afficher uniquement le segment source actuel en gras.

`Colorer tous les segments répétés`  
Utilisez [\#menus.view](#menus.view)[\#menus.view.mark.non.unique.segments](#menus.view.mark.non.unique.segments) pour colorer la deuxième copie et les copies suivantes d’un segment répété. Utilisez cette option pour colorer également la première copie du segment.

`Simplifier les infobulles des balises`  
Les balises OmegaT sont des textes protégés qui représentent des balises spécifiques à un format dans le document source. Lors du survol d’une balise, OmegaT affiche une infobulle qui contient le contenu original de la balise. Si ce contenu était à l’origine entouré de balises jumelées, ces dernières peuvent être supprimées de l’infobulle pour une meilleure lisibilité.

`Personnaliser les informations de modification du segment`  
Les informations relatives à la modification du segment sont affichées au-dessus du segment. Le paramètre par défaut indique qui a modifié la traduction pour la dernière fois et quand :

    Dernière modification de la traduction par suzume le 6 octobre 2022 à 14 :18 :27
    [[チューリッヒ大学]]大学院博士課程修了。
    [[Université de Zurich]] Elle finit sa thèse de doctorat.<segment 0178>

Utilisez [\#menus.view](#menus.view)[\#menus.view.modification.info](#menus.view.modification.info) pour afficher les informations relatives à la modification des segments.

`Modèle standard`  
Utilisez les variables du modèle pour adapter ce modèle à vos besoins.

`Modèle pour les segments sans date`  
Utilisez les variables du modèle pour adapter ce modèle à vos besoins.

## Enregistrement et exécution

`Intervalle d’enregistrement des données du projet`  
Permet de sélectionner l’intervalle entre les enregistrements automatiques des données du projet. Voir la section [\#how.to.restore.your.data.automatic.backup](#how.to.restore.your.data.automatic.backup) pour en savoir plus.

Modifier l’intervalle par défaut (3 minutes) selon les caractéristiques du projet :

-   Intervalles courts (10 secondes minimum) pour les projets synchronisés sur un serveur interne.

-   Intervalles de longue durée pour des projets en équipes faisant appel à des serveurs externes.

`Commandes globales de post-traitement`  
OmegaT peut exécuter automatiquement des commandes après l’utilisation de [\#menus.project](#menus.project)[\#menus.project.create.translated.documents](#menus.project.create.translated.documents) ou [\#menus.project](#menus.project)[\#menus.project.create.current.translated.document](#menus.project.create.current.translated.document). Vous pouvez définir ces commandes ici.

Les commandes spécifiées ici sont disponibles pour tous les projets qui utilisent le même dossier de configuration. Elles sont enregistrées dans le fichier [\#configuration.folder.default.contents.omegat.prefs](#configuration.folder.default.contents.omegat.prefs).

La liste des variables de modèle vous permet d’accéder à diverses données de projet et variables système. Voir la section [\#post.processing.commands.template.variables](#post.processing.commands.template.variables) pour en savoir plus.

`Autoriser les commandes locales de post-traitement`  
Pour des raisons de sécurité, les [commandes locales de post-traitement](#dialogs.project.properties.external.processing.command) sont désactivées par défaut.

Vous pouvez également définir des commandes locales de post-traitement disponibles uniquement pour un projet donné. Ces commandes sont définies dans la fenêtre [\#dialogs.project.properties.external.processing.command](#dialogs.project.properties.external.processing.command).

Les commandes locales de post-traitement sont enregistrées dans le fichier [\#project.folder.omegat.project.file](#project.folder.omegat.project.file). N’activez cette option que si vous avez confiance en la source de ce fichier.

Les commandes locales sont exécutées avant les commandes globales.

## Connexion par proxy

Si vous utilisez un serveur proxy authentifié pour accéder à Internet, entrez vos informations d’identification ici.

## Stockage sécurisé

Définir ou réinitialiser le mot de passe principal utilisé pour protéger les identifiants de connexion ainsi que les clés d’accès aux services de traduction automatique.

Avant de réinitialiser le mot de passe principal, faites toujours une sauvegarde de ces informations, car elles seront supprimées et devront être saisies à nouveau.

## Modules d’extension

Affiche la liste de tous les plug-ins installés.

Les plug-ins sont installés par défaut dans le dossier [configuration](#configuration.folder), mais peuvent également être installés dans le dossier [\#application.folder.plugins](#application.folder.plugins) sous le dossier [application](#application.folder).

Des modules d’extension supplémentaires sont disponibles sur le [site de développement d’OmegaT](https://sourceforge.net/p/omegat/wiki/Plugins/).

## Mises à jour

Cette option permet de choisir d’être automatiquement informé des mises à jour d’OmegaT.

Si OmegaT détecte une mise à jour, il affichera un lien vers la page de téléchargement. Voir la section [\#update.and.delete.omegat](#update.and.delete.omegat) pour en savoir plus.
