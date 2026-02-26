# Glossaires

Les glossaires sont des fichiers terminologiques situés dans le dossier [\#project.folder.glossary](#project.folder.glossary).

Tous les termes d’un segment qui trouvent une correspondance dans l’*un* des glossaires seront affichés dans le volet [\#panes.glossary](#panes.glossary).

Les termes source peuvent être des expressions multimots.

Il y a 2 types de fichiers de glossaires :

Le glossaire du projet  
Utilisez [\#menus.edit](#menus.edit)[\#menus.edit.create.glossary.entry](#menus.edit.create.glossary.entry) pour créer une nouvelle entrée de glossaire. C’est la raison pour laquelle il est appelé le glossaire *modifiable*.

Utilisez [\#menus.project](#menus.project)[\#menus.project.access.project.contents.title](#menus.project.access.project.contents.title) pour y accéder directement. Vous pouvez ensuite l’ouvrir dans un éditeur de texte et le modifier.

Il n’est pas nécessaire de préparer ce fichier en avance.

Il sera créé la première fois que vous y insérerez un terme.

Si vous utilisez un fichier existant comme glossaire par défaut, toutes les nouvelles entrées seront enregistrées dans un format séparé par des tabulations et sauvegardées en UTF-8 par défaut.

Pour indiquer un encodage différent, vous pouvez ajouter un commentaire «  magique » sous la forme suivante :

\# -\*- coding: &lt;charset&gt; -\*-
,
dans lequel `<charset>` est généralement l’une des chaines de caractères répertoriées dans le [registre IANA](http://www.iana.org/assignments/character-sets/character-sets.xhtml).

Les glossaires de référence  
Il s’agit de fichiers terminologiques dans un format reconnu par OmegaT. Vous ne pouvez pas les modifier depuis l’interface d’OmegaT comme le glossaire du projet, mais vous pouvez le faire dans un éditeur de texte.

Toute modification apportée à un glossaire est immédiatement reconnue par OmegaT qui l’affiche dans le volet [\#panes.glossary](#panes.glossary).

## Le dossier des glossaires

Par défaut, un projet contient un dossier [\#project.folder.glossary](#project.folder.glossary) qui contient le glossaire modifiable ainsi que les glossaires de référence que vous souhaitez ajouter au projet. Voir les propriétés du projet [\#dialogs.project.properties.file.locations.glossaries](#dialogs.project.properties.file.locations.glossaries) pour en savoir plus.

Tous les glossaires doivent être situés dans le dossier [\#project.folder.glossary](#project.folder.glossary). Les glossaires situés dans des sous-dossiers sont également reconnus.

Dans ce dossier de glossaires de référence, vous pouvez créer plusieurs sous-dossiers terminologiques organisés par thème, par client ou par toute autre catégorie adaptée à votre travail.

Utilisez la propriété de projet [\#dialogs.project.properties.file.locations.glossaries](#dialogs.project.properties.file.locations.glossaries) pour définir l’emplacement du dossier des glossaires de référence. Ce dossier peut être placé en dehors du projet, ce qui vous permet de l’utiliser, ainsi que les sous-dossiers spécifiques, dans d’autres projets.

## Le glossaire du projet

Le glossaire modifiable est situé par défaut dans le dossier [\#project.folder.glossary](#project.folder.glossary) et s’appelle [\#project.folder.glossary.txt](#project.folder.glossary.txt).

Vous pouvez modifier son nom et son emplacement dans le dialogue [\#dialogs.project.properties.file.locations.writable.glossary](#dialogs.project.properties.file.locations.writable.glossary), mais vous devez lui donner une extension `.txt` ou `.utf8` et le mettre dans le dossier [\#project.folder.glossary](#project.folder.glossary) ou l’un de ses sous-dossiers.

## Format de fichier

Les fichiers glossaires d’OmegaT sont des fichiers simples en texte brut qui contiennent des listes de termes sur trois colonnes. Le terme source est en première colonne, un terme cible optionnel est en seconde colonne et un commentaire optionnel est en troisième colonne.

Les glossaires peuvent être des fichiers de « tabulation-separated values   » (TSV) ou de « comma-separated values  » (CSV) ou peuvent également utiliser le format TermBase eXchange (TBX 2).

Un glossaire modifiable créé par OmegaT pour le projet, sera un fichier TSV enregistré en UTF-8. Les fichiers qui n’utilisent que des caractères latins peuvent être reconnus et traités comme s’ils étaient encodés en ISO-8859-1 s’ils ne contiennent pas de caractères non ASCII ou d’autres caractères interprétables en UTF-8.

L’encodage utilisé pour lire les glossaires de référence dépend de leur extension de fichier :

<table>
<caption>Format, extension et encodage attendu</caption>
<thead>
<tr class="header">
<th>Format</th>
<th>Extension</th>
<th>Encodage</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>TSV</td>
<td><code>.txt</code></td>
<td>UTF-8</td>
</tr>
<tr class="even">
<td>TSV</td>
<td><code>.utf8</code></td>
<td>UTF-8</td>
</tr>
<tr class="odd">
<td>TSV</td>
<td><code>.tab</code></td>
<td>OS Encodage par défaut</td>
</tr>
<tr class="even">
<td>TSV</td>
<td><code>.tsv</code></td>
<td>OS Encodage par défaut</td>
</tr>
<tr class="odd">
<td>CSV</td>
<td><code>.csv</code></td>
<td>UTF-8</td>
</tr>
<tr class="even">
<td>TBX</td>
<td><code>.tbx</code></td>
<td>UTF-8</td>
</tr>
</tbody>
</table>

Format, extension et encodage attendu
