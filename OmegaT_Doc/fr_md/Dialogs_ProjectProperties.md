# Propriétés du projet

Utilisez [\#menus.project](#menus.project)[\#menus.project.properties](#menus.project.properties) pour ouvrir la boite de dialogue.

Cette boite de dialogue permet de définir les propriétés initiales du projet lors de la création d’un nouveau projet ou de les modifier ultérieurement, après la création du projet.

Voir le chapitre [\#introduction.create.and.open.new.project](#introduction.create.and.open.new.project) pour en savoir plus.

## Langues

Sélectionnez les langues source et cible dans la liste déroulante ou saisissez-les manuellement.

OmegaT fournit une liste brève et pratique de codes de langue à deux lettres, mais vous pouvez saisir n’importe quel code conforme au [BCP-47](https://www.rfc-editor.org/rfc/bcp/bcp47.txt) (y compris les codes de langue à trois lettres) dans le champ de saisie.

Les codes de langue sont utilisés à différents endroits dans OmegaT pour :

-   obtenir des résultats dans le volet [\#panes.fuzzy.matches](#panes.fuzzy.matches),

-   appliquer les règles de segmentation définies dans les préférences [\#dialogs.preferences.segmentation.setup](#dialogs.preferences.segmentation.setup),

-   pour trouver des erreurs d’orthographe à partir des dictionnaires installés dans les préférences [\#dialog.preferences.spellchecker](#dialog.preferences.spellchecker).

-   pour trouver des erreurs grammaticales et typographiques à partir des règles définies dans les préférences [\#dialog.preferences.languagetool.plugin](#dialog.preferences.languagetool.plugin), etc.

et ainsi de suite.

Veillez à saisir les codes de langue corrects et à vérifier que tous les autres emplacements nécessitant un tel code utilisent exactement les codes que vous saisissez ici. Les fonctions qui dépendent d’une langue échouent ou produisent des résultats incorrects en cas de non-concordance des codes de langue.

OmegaT sélectionne automatiquement les lemmatiseurs qui correspondent à la langue source et à la langue cible, mais vous pouvez modifier manuellement ces paramètres. Les lemmatiseurs permettent à OmegaT de fournir de meilleures correspondances.

## Options

`Segmentation au niveau des phrases`  
La segmentation au niveau des phrases divise les paragraphes ou autres blocs de texte du fichier source en segments selon des règles de segmentation.

Désactivez cette option si vous préférez ne pas segmenter davantage les paragraphes.

Par défaut, les règles de segmentation sont globales et s’appliquent à tous les projets.

Utilisez [\#menus.options](#menus.options)[\#menus.options.segmentation](#menus.options.segmentation) pour accéder aux règles de segmentation globales.

Cliquez sur [\#dialogs.project.properties.local.segmentation](#dialogs.project.properties.local.segmentation) pour utiliser les règles de segmentation spécifiques au projet (locales) plutôt que les règles globales. Vous pouvez également lancer OmegaT à partir de la ligne de commande avec un paramètre de configuration spécifique au projet pour obtenir un résultat similaire.

Voir la section [\#launch.with.command.line](#launch.with.command.line) pour en savoir plus.

Si vous utilisez les règles locales, vous pouvez toujours accéder aux règles générales, toutefois leur modification n’affectera pas votre projet.

La modification des règles de segmentation au cours d’une traduction ne modifie pas les segments enregistrés dans la mémoire de traduction du projet.

Passer de la segmentation par **phrase** à la segmentation par **paragraphe** en cours de traduction risque d’obliger OmegaT à mettre à jour les anciennes mémoires de traduction qui n’utilisaient pas la segmentation par phrase, mais pas l’inverse. Cependant, OmegaT tentera de créer des correspondances partielles pour les paragraphes en combinant les traductions de phrases existantes.

Si vous changez la segmentation pendant la traduction, vous devrez recharger le projet afin que celle-ci soit prise en compte. Cela aura pour effet de diviser ou de fusionner certains segments précédemment traduits, qui ne seront donc plus traduits. Cependant, leur traduction originale sera toujours présente dans la mémoire du projet.

Voir l’annexe [\#app.segmentation](#app.segmentation) pour des explications générales sur la segmentation (globale ou locale, paragraphe ou phrase, paramètres, etc.)

Règles locales de segmentation…  
Par défaut, les règles de segmentation sont globales et s’appliquent à tous les projets.

Les règles de segmentation présentées lorsque vous ouvrez les préférences [\#dialogs.preferences.segmentation.setup](#dialogs.preferences.segmentation.setup) (en utilisant [\#menus.options](#menus.options)[\#menus.options.segmentation](#menus.options.segmentation)) sont les règles globales.

Utilisez ce bouton pour créer des règles locales spécifiques à votre projet. Cochez la case `Utiliser les règles de segmentation locales` et ajustez les règles de segmentation comme vous le souhaitez.

Le projet stockera le nouvel ensemble de règles dans le fichier [\#project.folder.omegat.segmentation](#project.folder.omegat.segmentation) situé dans son dossier [\#project.folder.omegat.folder](#project.folder.omegat.folder). Ces règles remplaceront les règles de segmentation globales.

Pour désactiver les règles de segmentation locales, désactivez cette option ou supprimez ce fichier.

Si vous utilisez les règles locales, vous pouvez toujours accéder aux règles générales, toutefois leur modification n’affectera pas votre projet.

Voir l’annexe [\#app.segmentation](#app.segmentation) pour des explications générales sur la segmentation (globale ou locale, paragraphe ou phrase, paramètres, etc.)

`Propagation automatique des traductions`  
S’il y a des segments répétés dans les documents sources, le fait de cocher cette option définira le premier segment traduit comme la traduction par défaut et utilisera automatiquement le même texte cible dans les segments répétés restants.

Utilisez [\#menus.edit](#menus.edit)[\#menus.edit.create.alternative.translation](#menus.edit.create.alternative.translation) pour attribuer une traduction alternative aux segments qui nécessitent une traduction différente.

Si vous n’activez pas cette option, tous les segments peuvent se voir attribuer une traduction différente, même s’ils sont dupliqués dans le projet.

`Dissimuler les balises`  
Les balises sont généralement utiles pour reproduire dans le texte traduit des mises en page ou des caractéristiques spécifiques du texte source.

L’activation de cette fonction permet de masquer les balises dans les segments source, ce qui évite de les manipuler manuellement.

Cette fonction est particulièrement utile lorsqu’il s’agit de textes pour lesquels le formatage en ligne n’est pas particulièrement utile (par exemple, PDF OCR ou fichiers .odt ou .docx mal convertis.)

Les balises dissimulées sont simplement empilées à la fin du segment. Bien que cela n’empêche normalement pas l’ouverture du fichier traduit, gardez les points suivants à l’esprit lorsque vous utilisez cette fonction :

-   Vous devrez appliquer manuellement des caractères gras, italiques ou d’autres décorations de texte dans le fichier traduit.

-   Si vous souhaitez simplement réduire le nombre de balises dans un document Microsoft Word (2007 et versions ultérieures), vous pouvez utiliser le script [\#windows.scripts.distribution.tagwipe](#windows.scripts.distribution.tagwipe).

    Voir la section [\#windows.scripts](#windows.scripts) pour en savoir plus.

`Commandes locales de post-traitement`  
Pour des raisons de sécurité, les commandes locales de post-traitement sont désactivées par défaut.

Voir le paramètre [\#dialogs.preferences.saving.and.output.also.allow.per.project.external.commands](#dialogs.preferences.saving.and.output.also.allow.per.project.external.commands) pour en savoir plus.

OmegaT peut exécuter automatiquement des commandes après la création des fichiers cibles.

Saisissez les commandes que vous souhaitez exécuter dans ce champ.

Utilisez [\#menus.project](#menus.project)[\#menus.project.create.translated.documents](#menus.project.create.translated.documents) ou [\#menus.project](#menus.project)[\#menus.project.create.current.translated.document](#menus.project.create.current.translated.document) pour créer les fichiers cibles et déclencher la commande.

Les commandes spécifiées ici ne sont disponibles que pour ce projet. Elles sont enregistrées dans le fichier [\#project.folder.omegat.project.file](#project.folder.omegat.project.file). N’activez les commandes locales de post-traitement que si vous faites confiance à la source de ce fichier.

La liste des variables de modèle vous permet d’accéder à diverses données de projet et variables système.

Voir l’annexe [\#post.processing.commands](#post.processing.commands) pour en savoir plus.

Vous pouvez également définir des commandes globales de post-traitement accessibles à tous les projets qui partagent le même dossier de configuration. Ces commandes sont définies dans le paramètre [\#dialogs.preferences.saving.and.output.external.post-processing.command](#dialogs.preferences.saving.and.output.external.post-processing.command).

Les commandes locales sont exécutées avant les commandes globales.

Filtres de fichiers locaux…  
Par défaut, les paramètres de filtrage des fichiers sont globaux et partagés par tous les projets. Ils sont dans les préférences [\#dialogs.preferences.file.filters](#dialogs.preferences.file.filters).

Utilisez ce bouton pour créer des filtres de fichiers locaux spécifiques à votre projet. Cochez la case `Utiliser les paramètres des filtres de fichiers locaux` et ajustez les paramètres comme vous le souhaitez.

Le projet stockera le nouvel ensemble de filtres de fichiers dans le fichier [\#project.folder.omegat.filters](#project.folder.omegat.filters) situé dans son dossier [\#project.folder.omegat.folder](#project.folder.omegat.folder). Ces paramètres remplacent les paramètres globaux des filtres de fichiers.

Pour désactiver les filtres de fichiers spécifiques à un projet, décochez la case ou supprimez le fichier en question.

Voir l’annexe [\#file.filters](#file.filters) pour en savoir plus.

Mise en correspondance des dépôts…  
Lorsque vous travaillez sur un projet en équipe, cette fenêtre vous permet de définir la correspondance entre les dossiers distants et les dossiers locaux.

Voir la section [\#how.to.setup.team.project.mapping.parameters](#how.to.setup.team.project.mapping.parameters) du guide pratique [\#how.to.setup.team.project](#how.to.setup.team.project) pour en savoir plus.

Recherches externes locales  
Par défaut, les recherches externes sont globales et partagées par tous les projets. Elles sont définies dans les préférences [\#dialogs.preferences.external.searches](#dialogs.preferences.external.searches).

Utilisez ce bouton pour créer des recherches externes locales spécifiques à votre projet et ajustez les paramètres selon vos besoins.

Le projet stockera le nouvel ensemble de recherches externes dans le fichier [\#project.folder.omegat.finder](#project.folder.omegat.finder) situé dans son dossier [\#project.folder.omegat.folder](#project.folder.omegat.folder). Ces paramètres remplaceront les paramètres globaux de recherche externe.

Pour supprimer les recherches externes spécifiques à un projet, cliquez sur le bouton Supprimer ou supprimez ce fichier.

Voir le paramètre [\#dialogs.preferences.external.searches](#dialogs.preferences.external.searches) pour en savoir plus.

Pour des raisons de sécurité, les recherches externes basées sur les projets locaux sont désactivées par défaut. Pour les activer, cliquez sur [\#dialogs.preferences.external.search.enable.project.specific.commands](#dialogs.preferences.external.search.enable.project.specific.commands) dans les préférences [\#dialogs.preferences.external.searches](#dialogs.preferences.external.searches).

## Emplacement des fichiers

Un projet de traduction OmegaT se compose d’un certain nombre de ressources réparties dans des dossiers distincts.

Lors de la création d’un nouveau projet, OmegaT propose une structure de dossier par défaut qui contient toutes les ressources utilisées dans la traduction, mais cette structure n’est pas obligatoire.

Les dossiers de ressources peuvent se trouver n’importe où sur votre système, y compris sur des disques partagés.

Voir le chapitre [\#chapter.project.folder](#chapter.project.folder) pour en savoir plus.

Vous pouvez modifier la structure de votre projet en ajoutant ou en supprimant des fichiers des dossiers, ou même en changeant les dossiers utilisés par le projet à tout moment, même au cours de la traduction.

Utilisez [\#menus.project](#menus.project)[\#menus.project.access.project.contents](#menus.project.access.project.contents) et ses sous-menus pour accéder aux emplacements des ressources du projet.

Sélectionner  
Le bouton Sélectionner est disponible pour toutes les ressources du projet définies par l’utilisatrice.

Les ressources ne doivent pas nécessairement être stockées dans le dossier de projet par défaut créé par OmegaT. Vous pouvez sélectionner n’importe quel dossier pour contenir vos ressources, y compris des dossiers sur des disques partagés.

Cliquez sur le bouton pour sélectionner le dossier que vous souhaitez utiliser à la place du dossier de ressources par défaut.

`Dossier des fichiers à traduire`  
Ce dossier contient les fichiers à traduire. OmegaT tente de lire tous les fichiers à la fois et affiche dans l’éditeur les contenus traduisibles qu’il trouve.

Voir la section [\#project.folder.source](#project.folder.source) pour en savoir plus.

Si le dossier est vide, qu’aucun fichier ne contient de contenu traduisible ou qu’aucun fichier n’est pris en charge par les filtres disponibles, OmegaT vous indique que le dossier est vide.

Exclusions…  
Cliquez sur le bouton Exclusions… pour spécifier les fichiers ou dossiers qui doivent être ignorés par OmegaT. Un fichier ou un dossier ignoré est :

-   n’est pas affiché dans le volet [\#panes.editor](#panes.editor),

-   n’est pas pris en compte dans les différents rapports statistiques (tels que la commande [\#menus.tools](#menus.tools)[\#menus.tools.statistics](#menus.tools.statistics)), et

-   n’est pas copié dans le dossier [\#project.folder.target](#project.folder.target) lors de la création des fichiers traduits.

La boite de dialogue des motifs d’exclusion vous permet d’ajouter ou de supprimer un motif, ou d’en modifier un en double-cliquant dessus ou en le sélectionnant et en appuyant sur F2. Utilisez la syntaxe [Apache ant](https://ant.apache.org/manual/dirtasks.html#patterns) pour définir les exclusions.

`Dossier des mémoires de traduction`  
Ce dossier contient les fichiers que vous souhaitez utiliser comme mémoires de traduction de référence. OmegaT tente de lire tous les fichiers en même temps et compare leur contenu au segment que vous êtes en train de traduire.

Voir la section [\#project.folder.tm](#project.folder.tm) pour en savoir plus.

Si des correspondances sont trouvées, elles sont affichées dans le volet [\#panes.fuzzy.matches](#panes.fuzzy.matches).

`Dossier des fichiers glossaire`  
Ce dossier contient les fichiers que vous souhaitez utiliser comme glossaires de référence. OmegaT tente de lire tous les fichiers en même temps et compare leur contenu au segment que vous êtes en train de traduire.

Voir la section [\#project.folder.glossary](#project.folder.glossary) pour en savoir plus.

Si des correspondances sont trouvées, elles sont affichées dans le volet [\#panes.glossary](#panes.glossary).

Voir l’annexe [\#app.glossaries](#app.glossaries) pour en savoir plus.

`Glossaire modifiable`  
Le glossaire modifiable est le fichier qu’OmegaT utilise lorsque vous ajoutez des termes traduits dans votre projet à l’aide de la commande [\#menus.edit](#menus.edit)[\#menus.edit.create.glossary.entry](#menus.edit.create.glossary.entry).

Il est automatiquement créé la première fois qu’un terme est ajouté.

Les entrées nouvellement ajoutées sont automatiquement reconnues et affichées si elles correspondent à des termes du segment en cours.

Ce fichier est *toujours* situé dans le dossier [\#project.folder.glossary](#project.folder.glossary).

`Dossier des dictionnaires`  
Ce dossier contient les fichiers que vous souhaitez utiliser comme glossaires de référence. OmegaT essaie de lire tous les fichiers à la fois et de faire correspondre leur contenu au segment en cours de traduction.

Voir la section [\#project.folder.dictionary](#project.folder.dictionary) pour en savoir plus.

Si des correspondances sont trouvées, elles sont affichées dans le volet [\#panes.dictionary](#panes.dictionary).

`Dossier des fichiers traduits`  
Il s’agit du dossier dans lequel OmegaT crée les fichiers traduits.

Les fichiers traduits sont les versions traduites des fichiers situés dans le dossier [\#project.folder.source](#project.folder.source).

Les segments traduits sont remplacés par leur traduction et les segments non traduits restent dans la langue source.

La structure du dossier reflète celle du dossier [\#project.folder.source](#project.folder.source). Les fichiers qui ne sont pas pris en charge par les filtres de fichiers d’OmegaT sont copiés sans modification.

Utilisez [\#menus.project.create.translated.documents](#menus.project.create.translated.documents) ou [\#menus.project.create.current.translated.document](#menus.project.create.current.translated.document) pour créer les fichiers traduits.

Voir la section [\#project.folder.target](#project.folder.target) pour en savoir plus.

`Dossier des mémoires de traduction exportées`  
Il s’agit du dossier dans lequel OmegaT copie l’état actuel de la traduction sous forme de fichiers TMX lors de la création des fichiers traduits.

Par défaut, ce dossier est le dossier du projet lui-même, mais vous pouvez modifier son emplacement pour rendre plus pratique le partage des fichiers TM exportés.

Voir le guide pratique [\#how.to.tm.share.translation.memories](#how.to.tm.share.translation.memories) pour en savoir plus.

Les fichiers TMX ne contiennent que les segments des fichiers actuellement stockés dans le dossier [\#project.folder.source](#project.folder.source).

Utilisez [\#menus.project.create.translated.documents](#menus.project.create.translated.documents) ou [\#menus.project.create.current.translated.document](#menus.project.create.current.translated.document) pour créer les fichiers traduits et les fichiers TMX exportés.

`Mémoires de traduction à exporter`  
Cette case à cocher vous permet de choisir les formats dans lesquels OmegaT doit créer les fichiers TMX ci-dessus.

Voir le guide pratique [\#how.to.use.tm](#how.to.use.tm) pour en savoir plus.

`OmegaT`  
Un TMX "OmegaT" contient les balises créées par OmegaT sous une forme qui ne peut être utilisée que dans le cadre d’un projet OmegaT.

`TMX niveau 1`  
Un TMX de "niveau 1" supprime toutes les informations relatives aux balises et ne contient que des données textuelles.

`TMX niveau 2`  
Un TMX de "niveau 2" contient des données textuelles ainsi que des balises encapsulées sous une forme compatible avec d’autres outils de TAO.

Voir la [Spécification TMX 1.4b](https://www.gala-global.org/tmx-14b#SectionIntroduction) pour plus de détails.
