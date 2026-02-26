# Segmentation

## Paragraphe ou phrase ?

Les outils à mémoire de traduction travaillent avec des unités textuelles appelées segments. Lorsqu’une traduction est saisie, le segment contenant le texte source est conservé avec sa traduction dans la mémoire du projet, et est subséquemment utilisé pour correspondre avec d’autres segments source dans le projet.

Pour spécifier le type de segmentation, utilisez la propriété du projet [\#dialogs.project.properties.options.segmentation](#dialogs.project.properties.options.segmentation).

Les segments sont par défaut des **paragraphes** définis par le format de fichier lui-même.

Ne pas utiliser la segmentation par **phrases** sur un fichier équivaut à utiliser une segmentation par *paragraphes*. Dans ce cas, chaque paragraphe (comme défini dans le format du document original) est affiché comme un unique segment, et vous êtes libre de réorganiser les phrases comprises dans le segment lors de la traduction.

La *segmentation par paragraphes* est plus efficace avec des textes littéraires ou créatifs, mais aussi, plus généralement, avec des documents où les correspondances de mémoire de traduction sont moins importantes.

La *segmentation par phrases* repose sur certaines règles (appelées *règles de segmentation*) qui définissent ce qui constitue une phrase dans la langue source. Ce paramètre est plus efficace avec les documents contenant des répétitions ou des phrases similaires, tels que des documents techniques ou juridiques.

Segmentation au niveau des paragraphes  
OmegaT effectue d’abord une analyse du texte pour procéder à une segmentation au niveau des paragraphes. Ce processus repose uniquement sur la structure du fichier source pour produire les segments.

Par exemple, les fichiers texte peuvent être segmentés au niveau des sauts de lignes, des lignes vides, ou pas du tout. Les fichiers contenant des formatages (documents ODF, HTML, etc.) sont divisés en fonction des balises délimitant des blocs (paragraphes). Les attributs traduisibles des balises présents dans les fichiers XHTML ou HTML peuvent être extraits en tant que « paragraphes  » séparés.

Segmentation au niveau des phrases  
Après avoir segmenté le fichier source en unités structurelles, OmegaT divise davantage ces unités en segments.

Vous pouvez visualiser la segmentation comme le processus qui consiste à bouger le curseur le long du texte, un caractère à la fois, en recherchant la position où une rupture se produira, ou la position où une rupture n’est pas autorisée.

Chaque fois que le curseur passe au caractère suivant, OmegaT vérifie :

-   si le texte situé avant l’emplacement correspond à une règle d’**Avant**,

-   et si le texte après l’emplacement correspond à la règle d’**Après** associée.

Si l’emplacement correspond aux deux règles, il sera considéré comme une rupture ou non, en fonction de ce que la règle a défini.

## Globales ou locales ?

Les mêmes mécanismes et boites de dialogue sont utilisés pour définir les règles globales et locales de segmentation.

Par défaut, les paramètres de segmentation sont globaux et partagés par tous les projets.

Utilisez les propriétés de projet [\#dialogs.project.properties.local.segmentation](#dialogs.project.properties.local.segmentation) pour limiter la portée des règles de segmentation au projet en cours.

Vous pouvez atteindre un résultat similaire en ouvrant OmegaT à partir de la ligne de commande. Voir le guide pratique [\#launch.with.command.line](#launch.with.command.line) pour en savoir plus.

Si vous utilisez les règles locales, vous pouvez toujours accéder aux règles générales, toutefois leur modification n’affectera pas votre projet.

## Règles

OmegaT fournit des règles prédéfinies de segmentation, et vous pouvez utiliser des expressions régulières pour les modifier. Voir l’annexe [\#app.regex](#app.regex) pour en savoir plus.

Pour rappel, les règles fonctionnent de la manière suivante : lorsqu’une règle correspond, OmegaT place un marqueur à l’emplacement de la correspondance afin que les règles suivantes ignorent cet emplacement. C’est la raison pour laquelle les règles d’exception doivent être appliquées avant les règles de segmentation.

Si vous changez la segmentation pendant la traduction, vous devrez recharger le projet afin que celle-ci soit prise en compte. Ce procédé va diviser ou fusionner certains segments précédemment traduits, qui ne seront donc plus considérés comme traduits. Néanmoins, leur traduction originale sera toujours dans la mémoire du projet.

<table>
<caption>Quelques exemples simples</caption>
<thead>
<tr class="header">
<th style="text-align: left;">Catégorie</th>
<th style="text-align: left;">Intention</th>
<th style="text-align: center;">Avant</th>
<th style="text-align: center;">Après</th>
<th style="text-align: left;">Explication</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;">Règle d’exception, case non cochée, plus haut dans la liste</td>
<td style="text-align: left;">Ne pas segmenter après Ms.</td>
<td style="text-align: center;">M\.</td>
<td style="text-align: center;">\s</td>
<td style="text-align: left;">Ms, suivi d’un point, suivi d’un caractère d’espacement.</td>
</tr>
<tr class="even">
<td style="text-align: left;">Règle d’exception, case non cochée, plus haut dans la liste</td>
<td style="text-align: left;">Cellules Excel avec des sauts de ligne qui ne représentent pas des segments.</td>
<td style="text-align: center;">\n</td>
<td style="text-align: center;">.</td>
<td style="text-align: left;">Saut de ligne, suivi de n’importe quoi.</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Règle de segmentation, case cochée, plus bas sur la liste</td>
<td style="text-align: left;">Commencer un nouveau segment après un point suivi d’une espace, une tabulation, ou autre caractère d’espacement.</td>
<td style="text-align: center;">\.</td>
<td style="text-align: center;">\s</td>
<td style="text-align: left;">Un point, suivi d’un caractère d’espacement.</td>
</tr>
<tr class="even">
<td style="text-align: left;">Règle de segmentation, case cochée, plus bas sur la liste</td>
<td style="text-align: left;">Commencer un nouveau segment après « 。» (point japonais).</td>
<td style="text-align: center;">。</td>
<td style="text-align: center;"></td>
<td style="text-align: left;">Remarquez que le champ <code>Après</code> peut être vide.</td>
</tr>
</tbody>
</table>

Quelques exemples simples
