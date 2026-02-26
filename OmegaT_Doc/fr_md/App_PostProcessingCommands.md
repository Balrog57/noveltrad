# Commandes de post-traitement

Voir la propriété du projet [\#dialogs.project.properties.external.processing.command](#dialogs.project.properties.external.processing.command) pour les commandes spécifiques au projet.

Voir le paramètre [\#dialogs.preferences.saving.and.output.external.post-processing.command](#dialogs.preferences.saving.and.output.external.post-processing.command) pour les commandes globales.

## Variables de modèle  

La commande est transmise à l’exécution Java sous la forme d’une chaine de caractères avec les valeurs du modèle développées. Tous les arguments doivent être cités, par exemple `« ${fileName} »`.

Les variables suivantes sont toujours disponibles. Les autres éléments de la liste des modèles sont des variables d’environnement de votre système.

<table>
<caption>Variables de modèle  </caption>
<thead>
<tr class="header">
<th style="text-align: left;">Nom de la variable</th>
<th style="text-align: left;">Valeur</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;">${projectName}</td>
<td style="text-align: left;">Le nom du dossier du projet</td>
</tr>
<tr class="even">
<td style="text-align: left;">${projectRoot}</td>
<td style="text-align: left;">Chemin complet vers le dossier du projet</td>
</tr>
<tr class="odd">
<td style="text-align: left;">${sourceRoot}</td>
<td style="text-align: left;">Chemin complet vers le dossier source</td>
</tr>
<tr class="even">
<td style="text-align: left;">${targetRoot}</td>
<td style="text-align: left;">Chemin complet vers le dossier cible</td>
</tr>
<tr class="odd">
<td style="text-align: left;">${glossaryRoot}</td>
<td style="text-align: left;">Chemin complet vers le dossier du glossaire</td>
</tr>
<tr class="even">
<td style="text-align: left;">${tmRoot}</td>
<td style="text-align: left;">Chemin complet vers le dossier racine de la mémoire de traduction</td>
</tr>
<tr class="odd">
<td style="text-align: left;">${tmAutoRoot}</td>
<td style="text-align: left;">Chemin complet vers le dossier automatique de mémoire de traduction</td>
</tr>
<tr class="even">
<td style="text-align: left;">${dictRoot}</td>
<td style="text-align: left;">Chemin complet vers le dossier du dictionnaire</td>
</tr>
<tr class="odd">
<td style="text-align: left;">${tmOtherLangRoot}</td>
<td style="text-align: left;">Racine de la mémoire de traduction + tmx2source (Voir le guide pratique <a href="#how.to.tm.bridge.two.languages">#how.to.tm.bridge.two.languages</a> pour en savoir plus).</td>
</tr>
<tr class="even">
<td style="text-align: left;">${sourceLang}</td>
<td style="text-align: left;">Langue source</td>
</tr>
<tr class="odd">
<td style="text-align: left;">${targetLang}</td>
<td style="text-align: left;">Langue cible</td>
</tr>
<tr class="even">
<td style="text-align: left;">${filePath}</td>
<td style="text-align: left;">Chemin complet du fichier source</td>
</tr>
<tr class="odd">
<td style="text-align: left;">${fileShortPath}</td>
<td style="text-align: left;">Nom du fichier source relatif à la racine donnée</td>
</tr>
<tr class="even">
<td style="text-align: left;">${fileName}</td>
<td style="text-align: left;">Nom complet du fichier source</td>
</tr>
<tr class="odd">
<td style="text-align: left;">${fileNameOnly}</td>
<td style="text-align: left;">Le nom du fichier source, sans l’extension</td>
</tr>
<tr class="even">
<td style="text-align: left;">${fileExtension}</td>
<td style="text-align: left;">Extension du fichier source sans point</td>
</tr>
</tbody>
</table>

Variables de modèle  

## Script local

En plus d’une commande normale, vous pouvez faire appel à un script. N’exécutez jamais de scripts de post-traitement à partir de sources non fiables. Pour des raisons de sécurité, les commandes locales de post-traitement sont désactivées par défaut.

Les variables de modèle peuvent être utilisées à la fois avec les commandes normales et les scripts personnalisés. Il vous faudra peut-être utiliser un chemin d’accès absolu pour votre script. Le chemin utilisé par OmegaT peut être différent du vôtre.

STDOUT et STDERR sont écrits dans le fichier [omegat.log](#configuration.folder.default.contents.logs.title). Le code de sortie et STDERR ou le dernier STDOUT apparaissent dans la barre d’état.

## Linux et macOS

Vous devez utiliser un shebang, par exemple `# ! /bin/bash` ou `#! /usr/bin/env python3`. Le script doit être exécutable. Enchainer des commandes avec `&&` ou `||` ou des barres verticales `|` ne fonctionnera pas ici.

Ouvrir le dossier cible sous Linux  
    xdg-open ${targetRoot}

Ouvrir le dossier cible sous macOS  
    open ${targetRoot}

Ouvrir le dossier cible dans Windows Powershell  
    Invoke-Item ${targetRoot}
