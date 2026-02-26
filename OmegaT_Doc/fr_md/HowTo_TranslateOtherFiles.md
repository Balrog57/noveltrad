# Prendre en charge d’autres formats

Les filtres de fichiers d’OmegaT permettent de prendre en charge un grand nombre de formats de fichiers courants et moins courants. Si vous devez prendre en charge des formats qui ne sont pas traités par OmegaT, il y a quatre façons de le faire :

-   [Associer](#how.to.translate.other.files.associate) le format à un format déjà pris en charge.

-   [Convertir](#how.to.translate.other.files.convert) le format en un format déjà pris en charge.

-   [Étendre](#how.to.translate.other.files.third.party.plugins) OmegaT avec des extensions tierces qui prennent en charge le format.

-   [Développer](#how.to.translate.other.files.develop) un filtre pour le format.

## Association

Les filtres de fichiers sont associés à une liste d’extensions de fichiers. Si le format que vous souhaitez traduire est structurellement proche d’un format déjà pris en charge, il suffit d’ajouter son extension de fichier à la liste des extensions de format prises en charge ou de modifier l’extension de fichier pour qu’elle soit acceptée par le filtre de fichiers que vous souhaitez utiliser. Voir le chapitre [\#file.filters](#file.filters) pour en savoir plus.

Vous pouvez également utiliser la fonction de balise personnalisée d’OmegaT pour enregistrer des chaines de caractères spécifiques à un format et faire en sorte qu’OmegaT les traite comme s’il s’agissait de balises normales. Voir le paramètre [\#dialogs.preferences.tag.processing.regular.expressions.for.custom.tags](#dialogs.preferences.tag.processing.regular.expressions.for.custom.tags) pour en savoir plus.

## Conversion

Pour s’assurer que toutes les propriétés d’un format sont correctement prises en compte, il est parfois préférable de convertir le fichier dans un format pris en charge, puis de reconvertir le fichier traduit dans le format d’origine.

Un certain nombre de logiciels tiers libres permettent une telle conversion « aller-retour » :

-   Rainbow, d’[Okapi Framework](https://okapiframework.org)

    Licence : Licence Apache Version 2.0

    L’Okapi Framework comporte un certain nombre de filtres de fichiers, dont certains ne sont pas pris en charge nativement par OmegaT. Voir [Liste des filtres de fichiers](https://okapiframework.org/wiki/index.php?title=Filters) pour en savoir plus.

    Rainbow peut créer des fichiers conformes à XLIFF 1.2 ou des projets OmegaT à partir de tous les fichiers définis comme fichiers « d’entrée ». Les fichiers pris en charge par Rainbow sont convertis en XLIFF et insérés en tant que fichiers source dans un projet OmegaT à part entière que vous pouvez ouvrir immédiatement avec OmegaT. Voir [Rainbow TKit - Projet OmegaT](https://okapiframework.org/wiki/index.php/Rainbow_TKit_-_OmegaT_Project) pour en savoir plus.

-   [po4a](https://po4a.org)

    Licence : Licence Publique Générale GNU v2

    po4a prend en charge un certain nombre de formats de documentation de logiciels libres, énumérés sur la page d’accueil du site, et propose des outils de conversion vers et depuis le format po. Voir la section [\#file.filters.po](#file.filters.po) pour en savoir plus.

-   Les convertisseurs de [Translate Toolkit](http://docs.translatehouse.org/projects/translate-toolkit/en/latest/index.html)

    Licence : Licence Publique Générale GNU v2

    Le Translate Toolkit offre un certain nombre d’outils de conversion vers et depuis le format po. Voir [Convertisseurs](http://docs.translatehouse.org/projects/translate-toolkit/en/latest/commands/index.html) pour en savoir plus.

-   OpenXLIFF de [Maxprograms](https://maxprograms.com/)

    Licence : Eclipse Public License v1.0

    OpenXLIFF prend en charge un certain nombre de filtres de fichiers, dont quelques-uns non pris en charge nativement par OmegaT. Voir [Filtres OpenXLIFF](https://maxprograms.com/products/openxliff.html) pour en savoir plus. Maxprograms propose également [XLIFF Manager](https://maxprograms.com/products/xliffmanager.html), une interface graphique pour les filtres OpenXLIFF.

    OpenXLIFF génère des fichiers compatibles avec XLIFF 1.2.

Certains formats, comme le PDF, ne peuvent pas être correctement traités par des conversions « aller-retour ». Il faut alors effectuer une conversion intermédiaire vers un format pris en charge, qui servira de base pour créer manuellement un document adéquat dans la langue cible.

Il existe plusieurs solutions en ligne ou hors ligne permettant de convertir des fichiers PDF en formats de bureautique courants. Toutefois, la conversion nécessitera toujours d’importants ajustements manuels du document cible avant de pouvoir produire un document PDF convenable. Assurez-vous d’avoir une bonne connaissance des exigences en matière de format lorsque vous commencez à travailler sur un fichier PDF ou sur un fichier similaire.

## Extensions tierces

-   L’extension Okapi Filters pour OmegaT, d’[Okapi Framework](https://okapiframework.org)

    Licence : Licence Apache Version 2.0

    L’extension de filtre de fichier n’inclut pas tous les filtres de fichier d’Okapi Framework. Voir [Filtres inclus](https://okapiframework.org/wiki/index.php/Okapi_Filters_Plugin_for_OmegaT#Filters_Included) pour en savoir plus.

    Une fois installée, l’extension donne un accès direct aux formats ajoutés et permet également d’associer un fichier de paramètres de filtrage personnalisé créé dans Rainbow. Voir [ci-dessus](#how.to.translate.other.files.third.party.utilities.rainbow).

D’autres extensions pour des formats moins courants sont répertoriées sur le wiki d’OmegaT. Voir [Extensions](https://sourceforge.net/p/omegat/wiki/Plugins/).

## Développement

OmegaT fournit une documentation complète pour créer des extensions de filtres de fichiers. Voir [How to create a file filter plugin for OmegaT](https://omegat.readthedocs.io/en/latest/11.HowToCreateFilterPlugin/) pour en savoir plus.
