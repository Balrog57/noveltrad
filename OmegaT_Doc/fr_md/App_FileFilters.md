# Filtres de fichiers

Les filtres de fichiers sont soit locaux et spécifiques à un projet donné, soit globaux et disponibles pour tous les projets qui partagent un dossier de configuration.

Pour en savoir plus, voir :

-   [\#dialogs.project.properties.filters](#dialogs.project.properties.filters)

-   [\#dialogs.preferences.file.filters](#dialogs.preferences.file.filters)

-   [\#configuration.folder](#configuration.folder)

Les filtres en gras sont utilisés dans le projet actuel.

Désactivez un filtre en décochant sa case si vous préférez ne pas traduire les fichiers qui lui sont associés. Leur contenu ne sera pas affiché pour la traduction.

Vous pouvez trier les filtres selon leur nom ou selon qu’ils soient activés ou non. Cliquez sur l’entête approprié afin de les trier par ordre croissant ou décroissant.

Afin de modifier les extensions de fichiers, le nom du fichier cible et les encodages liés a un filtre, sélectionnez-le dans la liste et cliquez sur le bouton Modifier….

Certains filtres proposent un bouton Options… afin d’approfondir la personnalisation des paramètres.

Cliquez sur le bouton Rétablir par défaut afin de réinitialiser les filtres de fichiers à leurs paramètres initiaux.

Les modifications des préférences globales de filtres de fichier sont enregistrées dans [\#configuration.folder.extra.contents.filters](#configuration.folder.extra.contents.filters), dans le dossier de configuration. Voir [\#configuration.folder](#configuration.folder) pour en savoir plus. La suppression de ce fichier réinitialise aussi les préférences de filtre.

Les modifications des filtres de fichiers locaux sont enregistrées dans le fichier [\#configuration.folder.extra.contents.filters](#configuration.folder.extra.contents.filters), situé dans le dossier du projet. Voir le chapitre [\#chapter.project.folder](#chapter.project.folder) pour en savoir plus. La suppression de ce fichier réinitialise aussi les préférences de filtre et ramène le projet aux filtres de fichiers globaux.

## Préférences communes

Masquer les balises de début et de fin.  
Les balises de début et de fin sont généralement demandées par OmegaT afin de recréer correctement le segment traduit. Les masquer du contenu traduisible vous assure de ne pas les effacer ou les modifier par erreur.

Si vous garder les balises de début et de fin, veillez à aussi les inclure dans le texte traduit.

Supprimer les espaces en début et fin de segment dans les projets non segmentés  
Par défaut, OmegaT supprime tout espace en début et fin de segment du contenu traduisible. Dans les projets non segmentés, désactivez cette option afin de pouvoir modifier les espaces en début et fin de segment dans la traduction.

Préserver les espaces pour toutes les balises  
Si les fichiers sources utilisent des espaces pour contrôler la mise en page, les espaces qui doivent être conservés le seront dans le document traduit.

N’utilisez pas le nom de fichier pour identifier des traductions alternatives  
Le nom de fichier source est un des éléments qui caractérisent une traduction alternative. Si cette option est cochée, seuls les segments précédents/suivants ou un identifiant de segment seront utilisés afin de caractériser une traduction alternative.

Les segments avec les mêmes caractéristiques et situés dans d’autres fichiers seront traduits de la même manière.

## Édition

Double-cliquez sur les champs modifiables afin d’effectuer des modifications simples ou cliquez sur le bouton Modifier… afin d’accéder à la boite de dialogue de modification.

Afin d’ajouter un modèle de filtre, cliquez sur Ajouter… pour ouvrir une boite de dialogue similaire.

Les deux boites de dialogue vous permettent de personnaliser les modèles de nom de fichier pour les fichiers source et cible associés à ce filtre, et de sélectionner leur encodage respectif.

Utilisez le menu déroulant Variables du nom de fichier afin de personnaliser le nom du fichier cible.

### Masque de nom de fichier source

Afin d’associer un filtre à un fichier, OmegaT vérifie son extension et essaie de le faire correspondre à un modèle de nom de fichier source dans un filtre.

Par exemple, le motif `.xhtml` enregistré dans le filtre XHTML correspond à tout fichier d’extension `xhtml`. Si un tel fichier est trouvé dans le dossier [\#project.folder.source](#project.folder.source), il sera traité par le filtre XHTML.

Vous pouvez changer ou ajouter des masques de nom de fichier pour associer différents fichiers à un filtre.

Associer une extension de fichier à un filtre n’est pas suffisant pour que ce dernier puisse traiter le fichier. La structure du fichier doit être compatible avec le filtre : même si vous associez `.odt` au filtre XHTML, le filtre ne sera pas capable de comprendre le contenu d’un fichier LibreOffice Writer.

Les masques de nom de fichier source utilisent des caractères génériques : le caractère `*` correspond à zéro ou plus de caractères, alors que le caractère `?` correspond à exactement un caractère.

Par exemple, utilisez le masque `read*` si vous souhaitez que le filtre texte traite les fichiers lisez-moi (`readme, read.me`, ou `readme.txt`).

### Encodage des fichiers source et traduits

La plupart des formats de fichiers permettent plusieurs encodages. Par défaut, l’encodage du fichier traduit est le même que celui du fichier source.

Les champs d’encodage cible et source utilisent des listes déroulantes incluant tous les encodages supportés. Sélectionner l’option &lt;auto&gt; laisse le choix de l’encodage à OmegaT, selon les critères suivants  :

-   OmegaT utilise la déclaration d’encodage dans le fichier source, si présent, pour identifier l’encodage (fichiers HTML, les fichiers à base XML).

<!-- -->

-   OmegaT est conçu pour utiliser un encodage obligatoire pour certains formats de fichier (propriétés de Java, etc.)

<!-- -->

-   OmegaT utilise l’encodage par défaut du système d’exploitation pour les fichiers texte.

### Noms des fichiers traduits

Les fichiers dans le dossier [\#project.folder.target](#project.folder.target) sont remplacés à chaque fois que vous les créez, s’ils sont créés avec le même nom.

OmegaT peut automatiquement créer de nouveaux noms pour les fichiers que vous créez, en y ajoutant un code de langue ou une date, par exemple.

Le masque de nom de fichier cible utilise une syntaxe spéciale. La façon la plus simple de le modifier est d’utiliser la boite de dialogue Modifier le Masque. La boite de dialogue propose plusieurs options :

&(filename)  
Le masque par défaut. Il représente le nom du fichier complet du fichier source, incluant l’extension. Utiliser ce masque associe au fichier traduit le même nom que le fichier source.

$(nameOnly)  
le nom du fichier source, sans l’extension

$(extension)  
extension du fichier original

$(targetLocale)  
langue cible+code de région (xx\_YY)

${targetLanguage}  
langue cible+région (xx-YY)

${targetLanguageCode}  
code de langue cible (xx)

${targetCountryCode}  
code de région cible (YY)

${timestamp-????}  
heure du système lors de la création du fichier

Voir la [documentation Oracle](https://docs.oracle.com/en/java/javase/11/docs/api/java.base/java/text/SimpleDateFormat.html) pour des exemples.

${system-os-name}  
nom du système d’exploitation

${system-user-name}  
identifiant

${system-host-name}  
nom de l’hôte sur le système

${file-source-encoding}  
encodage du fichier source

${file-target-encoding}  
encodage du fichier cible

${targetLocaleLCID}  
paramètres locaux cible Microsoft

Des variantes additionnelles sont disponibles pour `${nameOnly}` et `${extension}`.

Si l’utilisation de plusieurs points rend difficile l’identification du nom du fichier et de son extension, il est possible d’utiliser les variables de la forme `${nameOnly-`*nombre*} ou `${extension-`*nombre}* pour préciser quels sont les éléments qui font partie du nom et ceux qui font partie de l’extension, comme on peut le voir dans l’exemple ci-dessous.

Pour un fichier source nommé Document.xx.docx, utiliser les variantes de variables ci-dessous produira les résultats suivants :

-   `${nameOnly-0}` : `Document`

-   `${nameOnly-1}` : `Document.xx`

-   `${nameOnly-2}` : `Document.xx.docx`

-   `${extension-0}` : `docx`

-   `${extension-1}` : `xx.docx`

-   `${extension-2}` : `Document.xx.docx`

## Options

Plusieurs filtres proposent des options. Sélectionnez le filtre dans la liste et cliquez sur Options… pour le modifier.

Les options disponibles sont :

Fichiers texte  
Nouveaux paragraphes à chaque :  
Les fichiers texte n’ont pas de marqueurs de paragraphe génériques. Choisissez ici la manière dont OmegaT créer les paragraphes dans vos fichiers texte.

Longueur des lignes dans les fichiers cibles (0 = aucune limite)  
Longueur de ligne  
spécifie le nombre de caractères maximum avant de rompre une longue ligne. Une valeur de 0 n’établit aucune limite.

Longueur de ligne maximale  
spécifie le nombre de caractères maximum avant de couper une ligne et d’ignorer le reste. Une valeur de 0 n’établit aucune limite.

Fichiers Microsoft Office Open XML  
Le `Microsoft Office Open XML (filtre obsolète)` est le filtre OmegaT originel. Ne l’utilisez que pour éviter les problèmes de compatibilité avec les projets précédents contenant les fichiers que vous avez traités avec ce filtre.

Vous pouvez choisir des éléments de documents supplémentaire à traduire. Ils apparaitront en segments séparés dans l’éditeur.

Word  
Textes d’instruction non visibles, commentaires, notes de bas de pages, notes de fin de document, pieds de page, texte de remplacement en double et propriétés du document.

Excel  
Commentaires et noms des feuilles.

Power Point  
Commentaires des diapositives, masques des diapositives, et mise en page des diapositives.

Globales  
Liens externes, graphiques, diagrammes, dessins, et WordArt.

Autres options :  
Agréger les balises  
Les balises qui ne contiennent pas de texte traduisible seront agrégées en une seule balise.

Préserver les espaces pour toutes les balises  
Les caractères d’espacement (c.-à-d. les espaces et les sauts de ligne) seront préservés, même si cette option n’est pas définie dans le document.

Considérer un saut de ligne comme un saut de paragraphe  
Activez cette option si les sauts de ligne sont prévus pour être des sauts de paragraphe.

Fichiers XHTML  
Traduire les attributs suivants  
Les attributs sélectionnés apparaitront en tant que segments dans l’Éditeur.

Commencer un nouveau paragraphe sur  
La balise HTML &lt;br&gt; sera considérée comme un saut de paragraphe.

Paragraphes ignorés (expression régulière)  
Tout paragraphe correspondant à l’expression régulière sera ignoré lors du chargement et ne sera pas affiché pour la traduction.

Cette option est pratique pour traiter les parties HTML qui ne contiennent pas de texte traduisible.

L’attribut "content" ignoré des balises &lt;meta&gt;  
Définissez les valeurs des attributs de la balise &lt;meta&gt; pour lesquelles l’attribut "content" associé ne sera pas traduit.

N’ajoutez pas de guillemets et séparez les valeurs avec une virgule.

Pour ignorer ce contenu :

`<meta name="robots" content="index, follow">`

utilisez :

`name=robots`

Balises ignorées (attribute=value)  
Définissez les valeurs des attributs qui rendent une balise non traduisible.

N’ajoutez pas de guillemets et séparez les valeurs avec une virgule.

Pour ignorer ce contenu :

`<span translate="no">This content is not translatable</span>`

utilisez : `translate=no`.

Tous les tags marqués avec un `translate="no"` seront ignorés.

Fichiers HTML et XHTML  
Seules les options qui ne sont pas disponibles sous les filtres de fichier XHTML (voir ci-dessus) sont décrites ici.

Modifier la déclaration d’encodage  
L’encodage d’un document HTML est généralement déclaré dans un élément &lt;meta&gt; situé dans l’élément &lt;head&gt;.

Les fichiers sources et cibles nécessitent parfois d’un encodage différent.

Ici, vous pouvez ajouter ou modifier la déclaration du fichier cible.

-   toujours, en fonction des paramètres du filtre de fichier,

-   seulement si le fichier a déjà une balise &lt;head&gt;,

-   seulement si le fichier a déjà une déclaration,

-   ou jamais et n’enregistrez le fichier cible que dans l’encodage spécifié dans les paramètres du filtre de fichier.

Compresser les espaces dans le fichier traduit  
Les espaces en dehors des balises sont considérées comme insignifiantes en HTML/XHTML.

Cette option convertit ces multiples espaces continus en un seul espace dans le document traduit.

Supprimer les commentaires HTML  
Les commentaires dans un fichier HTML sont généralement destinés au développement. Utilisez cette option pour les supprimer. Si l’option n’est pas cochée, les commentaires seront affichés sous la forme de balises.

Les textes en commentaire HTML (entre `<!--` et `-->`) ne sont pas copiés dans le document traduit.

Mozilla FTL  
Supprimer les chaines non traduites dans les fichiers cibles  
La présence de contenus non traduits dans les fichiers traduits crée parfois des problèmes de compatibilité.

DTD Mozilla  
Supprimer les chaines non traduites dans les fichiers cibles  
La présence de contenus non traduits dans les fichiers traduits crée parfois des problèmes de compatibilité.

Fichiers PO  
Le filtre vérifie les variables printf ('%s, etc.) par défaut. Voir le paramètre [\#dialogs.preferences.tag.processing.programming.variables](#dialogs.preferences.tag.processing.programming.variables) pour en savoir plus.

Autoriser les segments cibles vides  
OmegaT reproduit toujours le contenu source quand un segment est manquant. Utilisez cette option pour laisser un vide à la place d’un segment non traduit.

Traduire les segments sources vides  
Les segments sources vides servent parfois de substituts temporaires à des parties qui n’existent pas dans la langue source mais qui sont nécessaires dans la langue cible. Utilisez cette option pour fournir une traduction basée sur les commentaires associés.

Ignorer l’entête des fichiers PO  
L’entête du PO ne sera pas affiché pour la traduction.

Remplacement automatique de la spécification du pluriel.  
Remplace la spécification du pluriel dans l’entête et utilise la langue cible par défaut.

Format :  
Standard  
Les fichiers PO qui utilisent `msgid` comme conteneur source et attendent que la traduction soit mise dans `msgstr`.

Monolingue  
Les fichiers PO qui utilisent `msgid` comme identifiant, utilisent `msgstr`comme conteneur source et attendent que la traduction remplace le contenu de `msgstr`.

PHP Moodle  
Supprimer les chaines non traduites dans les fichiers cibles  
La présence de contenus non traduits dans les fichiers traduits crée parfois des problèmes de compatibilité.

Paquets de ressources Java  
Le filtre vérifie les masques Java MessageFormat (ex. : \\0\\) par défaut. Voir le paramètre [\#dialogs.preferences.tag.processing.programming.variables](#dialogs.preferences.tag.processing.programming.variables) pour en savoir plus.

Forcer la compatibilité avec Java 8 des littéraux Unicode  
Java 8 nécessite l’encodage ISO-8859-1 et utilise des littéraux Unicode pour les caractères qui ne font pas partie de ce jeu de caractères. Java 9 et les versions ultérieures requièrent l’encodage UTF-8. Cette option force la compatibilité avec Java 8.

Supprimer les chaines non traduites dans les fichiers cibles  
La présence de contenus non traduits dans les fichiers traduits crée parfois des problèmes de compatibilité.

Conserver les littéraux Unicode (\\uXXXX)  
Certaines applications nécessitent de conserver certains littéraux Unicode. Cette option le permet.

Fichiers Open Document Format (ODF)  
Traduire les éléments suivants  
Entrées d’index, signets (repère de texte), références aux signets, notes, commentaires, notes des présentations, liens (URL), et noms des feuilles.

XLIFF (filtre obsolète)  
Ce filtre est le filtre XLIFF originel d’OmegaT. Ne l’utilisez que pour éviter les problèmes de compatibilité avec les projets précédents contenant des fichiers que vous avez traités avec ce filtre.

Compatibilité avec OmegaT 2.6  
Activez cette option si vous devez travailler avec des fichiers XLIFF crées avec OmegaT 2.6.

Identifiant utilisé pour les traductions alternatives  
Vous pouvez faire le choix parmi trois options : les paragraphes suivants et précédents, l’ID &lt;trans unit&gt;, ou l’attribut resname de &lt;trans-unit&gt; lorsqu’il est disponible. S’il ne l’est pas, l’ID sera utilisé à la place.

Balises abrégées  
Ces options précisent la manière dont OmegaT crée les balises des contenus XLIFF.

Statut du segment cible  
si cette option est cochée, OmegaT passe l’état de la cible XLIFF en "needs-review-translation" au lieu de "translated".
