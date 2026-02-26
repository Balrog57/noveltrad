# Expressions régulières

Cette annexe s’adresse aux utilisatrices qui souhaitent explorer une technique puissante pour améliorer leur productivité. Souvent perçues comme étant intimidantes et complexes, même les expressions régulières les plus simples (souvent abrégées *regex* ou *regexp*) sont extrêmement utiles, non seulement dans OmegaT mais également dans beaucoup d’autres applications utilisées au quotidien, avec quelques variations.

Nous n’abordons ici que les notions de bases les plus utiles aux traductaires. La section [\#app.regex.tools](#app.regex.tools) à la fin de cette annexe propose des points de départ pour explorer des usages avancés ou complexes qui dépassent l’étendue de ce guide. Si vous avez besoin d’aide pour des cas spécifiques, n’hésitez pas à poser vos questions dans les différents canaux d’aide.

Les expressions régulières utilisent des combinaisons de lettre, chiffres et symboles (qu’on appellera ici *caractères*) pour définir une *expression* qui représente un motif textuel particulier.

Voici quelques exemples.

\[0-9\]  
Un chiffre de 0 à 9.

\w+  
Un « caractère de mot » ou plus, c’est-à-dire une lettre de l’alphabet non accentuée, un chiffre ou le symbole « \_ ».

\h?  
Représente zéro ou un caractère d’espacement (cela inclut les espaces régulières et insécables ainsi que les tabulations, mais pas les caractères de saut de ligne, qui appartiennent à la catégorie des « caractère d’espacement verticaux  » : \v.)

De nombreuses fonctions d’OmegaT dépendent des expressions régulières ou les proposent en option :

Recherches  
Les recherches incluent une option [\#windows.text.search.methods.regex](#windows.text.search.methods.regex) qui vous permet d’effectuer des recherches extrêmement puissantes dans vos fichiers.

La même option dans la boite de dialogue [\#windows.text.replace](#windows.text.replace) vous permet d’appliquer des expressions régulières à la fois au texte recherché et au texte remplacé.

Balises personnalisées  
Les balises personnalisées sont des balises définies avec des expressions régulières qui sont traitées exactement comme les balises natives d’OmegaT. Voir le paramètre [\#dialogs.preferences.tag.processing.regular.expressions.for.custom.tags](#dialogs.preferences.tag.processing.regular.expressions.for.custom.tags) pour en savoir plus.

Utilisez le caractère `|` (OU) pour séparer les définitions de balises individuelles.

Texte signalé  
Le paramètre [\#dialogs.preferences.tag.processing.regular.expressions.for.fragments.that.should.be.removed.from.translation](#dialogs.preferences.tag.processing.regular.expressions.for.fragments.that.should.be.removed.from.translation) vous permet de définir une chaine de caractères qu’OmegaT colorera en rouge par défaut et traitera comme une balise superflue.

Utilisez le caractère `|` (OU) pour séparer les définitions de fragments individuels.

Surlignage du texte dans les alignements  
Des repères visuels peuvent aider à vérifier que votre alignement est correct. Le paramètre [\#windows.aligner.adjust.highlight](#windows.aligner.adjust.highlight) permet de définir les chaines de caractères qu’OmegaT surlignera dans les documents alignés.

Utilisez le caractère `|` (OU) pour séparer les expressions individuelles.

Segmentation  
Les règles de segmentation et les masques de langage sont définis à l’aide d’expressions régulières. Vous pouvez les modifier librement pour améliorer la segmentation d’un document ou ajouter des règles générales supplémentaires. Voir l’annexe [\#app.segmentation](#app.segmentation) pour en savoir plus.

Les règles de segmentation ou d’exception définissent la position dans un segment dans lequel un fractionnement sera effectué ou non. Deux expressions régulières sont nécessaires pour définir cette position : une expression "avant" pour définir le masque de texte situé avant l’endroit où la règle doit s’appliquer, et une expression "après" pour définir le modèle de texte situé après cette position.

Un masque de langue qui correspond à la langue source du projet s’appliquera à ce projet.

## Les 4 règles

Les expressions régulières sont utilisées pour rechercher du texte, y compris des caractères qui ne sont pas visibles à l’écran ou à l’impression, comme les espaces, les tabulations ou les sauts de ligne. Toute expression donnée soit *correspond*, soit *ne **correspond** pas* à un mot, une phrase ou une autre séquence textuelle.

Chaque caractère de l’expression a son importance pour déterminer une correspondance.

Certains caractères ou combinaisons de caractères ont une signification particulière dans une expression régulière.

Les expressions régulières ne correspondent qu’à du texte. Elles ne peuvent pas correspondre à des décorations telles que *gras*, *italique*, ou d’autres *effets stylistiques*.

Il y a quatre règles à retenir.

La plupart des caractères correspondent simplement à eux-mêmes  
La plupart des caractères d’une expression régulière vont simplement *se chercher eux-mêmes* dans la séquence textuelle.

Par exemple, les sept lettres qui composent le mot « *exemple*  » indiquent à la fonction de recherche de trouver exactement ces lettres, dans cet ordre. La fonction de recherche a pour but de trouver le mot « *exemple*  ». Autrement dit, elle ne recherche que ce terme précis.

Les caractères alphanumériques précédés d’une barre oblique inverse (`\`) prennent une signification particulière.  
Contrairement à une lettre seule, qui se représente simplement comme indiqué ci-dessus, une lettre précédée d’une `\` a une fonction particulière dans une expression régulière.

Par exemple, *r* est juste un caractère normal mais le fait de le précéder d’une `\` pour en faire `\r` le transforme en une combinaison spéciale qui correspond à un *caractère retour chariot*. De même, `\R` correspond à *tout caractère de saut de ligne*.

Seules les lettres *i j l m o*, et *y*, en minuscules et en majuscules, n’ont pas de signification particulière lorsqu’elles sont précédées d’une barre oblique inversée. Ce manuel ne décrit qu’un petit sous-ensemble de lettres qui ont une signification particulière.

Consultez les sites de la section [\#app.regex.tools](#app.regex.tools) ci-dessous pour en savoir plus sur les combinaisons qui ne sont pas abordées ici.

Douze caractères ont une signification particulière par défaut  
Cette signification doit être annulée par un autre caractère pour correspondre au caractère lui-même.

La liste complète de ces caractères est [ci-dessous](#app.regex.twelve.characters). Par exemple, `.` : lorsqu’il est utilisé seul, il a une signification particulière qui permet de correspondre à*tout caractère unique*.

Pour trouver un point normal, il faut annuler ce sens en utilisant le `\`, pour faire l’expression `\.`, qui correspond juste à un point.

Le caractère `\` est un caractère très particulier  
Comme indiqué ci-dessus, le caractère `\` a par défaut un sens particulier. Il peut annuler ou activer la signification spéciale des autres caractères. Il n’a aucun effet s’il est placé devant un caractère sans signification particulière (que ce soit par défaut ou par ajout).

Le `\` peut annuler sa propre signification spéciale en se doublant pour former `\\`, qui correspond au caractère de la *barre oblique inversée*.

## Les 12 caractères

Les douze caractères particuliers sont la *barre oblique inversée* `\`, le *caret* `^`, le *symbole dollar* `$`, le *point* `.`, la *barre verticale* (ou *symbole de « pipe  »*) `|`, le *point d’interrogation* `?`, l’*astérisque* (ou *étoile*) `*`, le *signe plus* `+`, la *parenthèse* ouvrante `(`, la *parenthèse* fermante, `)`, le *crochet* ouvrant `[`, et l’*accolade* `{` ouvrante.

Chaque caractère est brièvement décrit ci-dessous, avec des exemples d’expressions régulières qui utilisent ce caractère, ainsi que du texte auquel elles correspondent ou non.

La BARRE OBLIQUE INVERSÉE : `\`  
Ce caractère annule ou active la signification particulière du caractère suivant.

<table>
<colgroup>
<col style="width: 30%" />
<col style="width: 70%" />
</colgroup>
<tbody>
<tr class="odd">
<td></td>
<td><code>0\.[0-9]</code></td>
</tr>
<tr class="even">
<td>Correspond à</td>
<td><p>Un nombre entre <em>0,0</em> et <em>0,9</em>, ou juste le dernier <em>0,5</em> dans des nombres comme 10,5 ou 560,5.</p>
<p>Le <code>\.</code> annule la signification « tout caractère  » du point pour correspondre au point décimal, tandis que le <code>\d</code> transforme la lettre « d » minuscule en une expression qui correspond à tout chiffre entre 0 et 9.</p></td>
</tr>
<tr class="odd">
<td>Ne correspond pas à</td>
<td><p>Des séquences telles que 0,1, 0-3, ou les trois premiers caractères de 0x002E, qui seraient trouvées si l’expression était juste <code>0.[0-9]</code>, sans barre oblique inverse avant le point</p></td>
</tr>
</tbody>
</table>

Le CARET `^`  
Lorsqu’il est le premier caractère de l’expression, le caractère *caret* correspond au début d’une ligne.

Lorsqu’il est le premier caractère d’une [classe de caractères entre crochets](#app.regex.types.of.expressions.classes), il correspond à tous les caractères qui ne font pas partie de cette classe.

<table>
<colgroup>
<col style="width: 30%" />
<col style="width: 70%" />
</colgroup>
<tbody>
<tr class="odd">
<td></td>
<td><ol type="1">
<li><p><code>^A</code></p></li>
<li><p>[^abc]</p></li>
</ol></td>
</tr>
<tr class="even">
<td>Correspond à</td>
<td><ol type="1">
<li><p>Le « A » majuscule dans la phrase suivante : « Au-dessus des étangs, au-dessus des vallées ».</p></li>
<li><p>Tout caractère qui n’est <em>pas</em> « a », « b », ou « c  ». Dans le mot « banc », par exemple, seul le « n » correspond.</p></li>
</ol></td>
</tr>
<tr class="odd">
<td>Ne correspond pas à</td>
<td><ol type="1">
<li><p>Le « A » majuscule dans la phrase suivante : « Baudelaire a écrit : <em>« Au-dessus des étangs, au-dessus des vallées »</em> ».</p></li>
<li><p>Le « a », « b », ou « c » minuscule dans le mot « banc ».</p></li>
</ol></td>
</tr>
</tbody>
</table>

Le SYMBOLE DOLLAR : `$`  
Lorsqu’il est le dernier caractère d’une expression, le symbole *dollar* correspond à la fin d’une ligne.

<table>
<colgroup>
<col style="width: 30%" />
<col style="width: 70%" />
</colgroup>
<tbody>
<tr class="odd">
<td></td>
<td><code>^\w+:$</code></td>
</tr>
<tr class="even">
<td>Correspond à</td>
<td><p>Une ligne qui se compose d’un seul mot et se termine par deux-points :</p>
<p><em>Questions :</em></p></td>
</tr>
<tr class="odd">
<td>Ne correspond pas à</td>
<td><p>Une ligne qui se compose d’un seul mot, mais qui ne se termine pas par deux-points :</p>
<p><em>Questions ?</em></p></td>
</tr>
</tbody>
</table>

Le POINT : `.`  
Correspond à tout caractère unique.

<table>
<colgroup>
<col style="width: 30%" />
<col style="width: 70%" />
</colgroup>
<tbody>
<tr class="odd">
<td></td>
<td><code>d.s</code></td>
</tr>
<tr class="even">
<td>Correspond à</td>
<td><p>Toute combinaison de trois lettres commençant par « d » et finissant par « s » : « <em>des</em> », « <em>dis</em> », « <em>dos</em> », ou même des combinaisons qui n’ont pas de sens, comme « <em>dzs</em> » ou « <em>dqs</em> ».</p></td>
</tr>
<tr class="odd">
<td>Ne correspond pas à</td>
<td><p>Des combinaisons contenant trois lettres qui commencent par « d » et se terminent par « s », mais qui sont réparties sur plus d’une ligne.</p>
<p>Quelle est la lettre manquante ?</p>
<code>d</code>, <code></code>, <code>s</code></td>
</tr>
</tbody>
</table>

La BARRE VERTICALE : `|`  
Ce caractère fonctionne comme un "OU", permettant de choisir une des expressions qui le précèdent ou le suivent.

<table>
<colgroup>
<col style="width: 30%" />
<col style="width: 70%" />
</colgroup>
<tbody>
<tr class="odd">
<td></td>
<td><code>^Une|^La</code></td>
</tr>
<tr class="even">
<td>Correspond à</td>
<td><p>Le premier mot « Une » ou « La » dans des phrases telles que : « Une pomme par jour… », « La prunelle de mes yeux… »</p></td>
</tr>
<tr class="odd">
<td>Ne correspond pas à</td>
<td><p>Le premier mot « Une » ou « La » dans des phrases telles que : « Un récit intitulé <em>Une Héroïne Inconnue</em>. », « Il travaille pour le journal <em>La Provence</em>. »</p></td>
</tr>
</tbody>
</table>

Le POINT D’INTERROGATION : `?`  
Ce caractère indique que le caractère ou l’expression qui le précède doit correspondre zéro ou une fois.

<table>
<colgroup>
<col style="width: 30%" />
<col style="width: 70%" />
</colgroup>
<tbody>
<tr class="odd">
<td></td>
<td><code>est?␣</code> ( sachant que "␣" représente une espace unique).</td>
</tr>
<tr class="even">
<td>Correspond à</td>
<td><p>Soit le « est » ou le « es » dans : « C’est une bonne question. », « Tu es un excellent médecin. »</p>
<p>Il trouvera également le « est » final de « Bucarest » dans une phrase telle que « Elles vont à Bucarest », ou le « es » final de « Naples » dans « À Naples on trouve la meilleure pizza. »</p></td>
</tr>
<tr class="odd">
<td>Ne correspond pas à</td>
<td><p>Ni le « est » ni le « es » dans : Le verbe être : « est » (ou « es »).</p>
<p>Il n’est pas suivi d’une espace.</p></td>
</tr>
</tbody>
</table>

L’ASTÉRISQUE : `*`  
Ce caractère indique que zéro ou plusieurs occurrences du caractère ou de l’expression qui le précède doivent être recherchées.

<table>
<colgroup>
<col style="width: 30%" />
<col style="width: 70%" />
</colgroup>
<tbody>
<tr class="odd">
<td></td>
<td><code>jour\w*</code></td>
</tr>
<tr class="even">
<td>Correspond à</td>
<td><p>Le mot « jour », ainsi que « Joure », « journée », « journalier », « jours » dans « toujours » ou « séjours », et tout autre mot ou suite de caractères contenant « jour » suivi de zéro ou plus « <em>caractères de mot</em> » (qui incluent les chiffres et le trait bas, de sorte que la partie précédant le « @ » dans une adresse de courriel telle que jour_123@example.email.org soit également une correspondance).</p></td>
</tr>
<tr class="odd">
<td>Ne correspond pas à</td>
<td><p>L’expression complète dans « contre-jour » ou « aujourd’hui », car le trait d’union et l’apostrophe ne sont pas inclus dans <code>\w</code>. Seule la première occurrence du mot « jour » dans ces phrases correspond.</p></td>
</tr>
</tbody>
</table>

Le signe PLUS : `+`  
Ce caractère indique qu’une ou plusieurs occurrences du caractère ou de l’expression qui le précède doivent correspondre.

<table>
<colgroup>
<col style="width: 30%" />
<col style="width: 70%" />
</colgroup>
<tbody>
<tr class="odd">
<td></td>
<td><code>\d+.d</code></td>
</tr>
<tr class="even">
<td>Correspond à</td>
<td><p>Des nombres tels que « 1,5 », « 23,2 » ou « 5235,8    » avec une seule décimale et un nombre quelconque de chiffres avant la décimale.</p></td>
</tr>
<tr class="odd">
<td>Ne correspond pas à</td>
<td><p>La valeur entière de nombres tels que « 5 235,8 » ou « 21 571,9 ». Seule la partie du texte située après le séparateur de milliers correspondra.</p></td>
</tr>
</tbody>
</table>

La PARENTHÈSE OUVRANTE : `(`  
Ce caractère commence un *groupe*, qui est un ensemble de caractères traités comme une seule unité. Les groupes sont numérotés, et leur contenu est stocké dans la mémoire. Ils peuvent être réutilisés ultérieurement dans l’expression de recherche en utilisant `\n`, où `n` est le numéro du groupe.

Le contenu du groupe peut également être utilisé dans le [texte de remplacement](#windows.text.replace). Utilisez `$n`, où `n` est le numéro du groupe défini dans la recherche.

Les parenthèses sont toujours utilisées par paires (ouverture et fermeture). Si vous essayez d’utiliser uniquement la parenthèse ouvrante ou fermante, une erreur se produira

<table>
<colgroup>
<col style="width: 30%" />
<col style="width: 70%" />
</colgroup>
<tbody>
<tr class="odd">
<td></td>
<td><code>(\b\w+\b)\h\1\b</code></td>
</tr>
<tr class="even">
<td>Correspond à</td>
<td><p>Des mots doublés séparés par une espace, comme le terme « une » consécutif dans la phrase suivante :</p>
<p>« J’ai acheté une une pomme. »</p></td>
</tr>
<tr class="odd">
<td>Ne correspond pas à</td>
<td><p>Le « ça, ça » dans la phrase suivante :</p>
<p>« Mais ça, ça dépasse les limites », car le premier « ça » est suivi à la fois d’une virgule et d’une espace et non d’une simple espace.</p></td>
</tr>
</tbody>
</table>

La PARENTHÈSE FERMANTE : `)`  
Ce caractère clôt un groupe. Il est spécial, car il ne peut jamais être utilisé seul. Il doit être précédé de `\` si vous devez faire correspondre le caractère de la parenthèse fermante à lui-même.

<table>
<colgroup>
<col style="width: 30%" />
<col style="width: 70%" />
</colgroup>
<tbody>
<tr class="odd">
<td></td>
<td><code>^\d+\)</code></td>
</tr>
<tr class="even">
<td>Correspond à</td>
<td><p>Le nombre séquentiel (y compris les parenthèses) au début de chaque ligne dans une liste comme :</p>
1) Pommes, 2) Oranges, 3) Poires</td>
</tr>
<tr class="odd">
<td>Ne correspond pas à</td>
<td><p>Les nombres séquentiels qui ne sont pas au début d’une ligne.</p>
<p>Procédez comme suit :</p>
Étape 1) Préparation, Étape 2) …</td>
</tr>
</tbody>
</table>

Le CROCHET OUVRANT : `[`  
Ce caractère doit être associé au crochet fermant pour contenir un ensemble de caractères individuels qui représentent chacun une correspondance potentielle valide.

Seule la parenthèse ouvrante est spéciale et doit être précédée d’une barre oblique inverse pour rechercher le caractère de crochet lui-même. Si vous souhaitez uniquement faire correspondre le crochet fermant tel quel, vous n’avez pas besoin de le faire précéder d’une barre oblique inverse. (Vous pouvez toujours l’ajouter, mais cela n’aura aucun effet sur l’expression ou le résultat).

<table>
<colgroup>
<col style="width: 30%" />
<col style="width: 70%" />
</colgroup>
<tbody>
<tr class="odd">
<td></td>
<td><code>li[cs]en[cs]e</code></td>
</tr>
<tr class="even">
<td>Correspond à</td>
<td><p>Les orthographes correctes de « licence » et « license », ainsi que les éventuelles fautes d’orthographe « lisence » et « lisense »</p></td>
</tr>
<tr class="odd">
<td>Ne correspond pas à</td>
<td><p>Des fautes d’orthographe plus flagrantes comme « licensse » ou « lissense ».</p></td>
</tr>
</tbody>
</table>

L’ACCOLADE OUVRANTE : `{`  
Ce caractère doit être associé à l’accolade fermante pour contenir un *nombre exact*, *minimum*, *maximum*, ou *gamme* précisant combien d’occurrences du caractère ou du groupe précédent doivent être correspondantes.

Seule l’accolade ouvrante est spéciale et doit être précédée d’une barre oblique inverse pour rechercher le caractère d’accolade lui-même. Si vous souhaitez uniquement faire correspondre l’accolade fermante en tant que telle, vous n’avez pas besoin de la faire précéder d’une barre oblique inverse. (Vous pouvez toujours l’ajouter, mais cela n’aura aucun effet sur l’expression ou le résultat).

<table>
<colgroup>
<col style="width: 30%" />
<col style="width: 70%" />
</colgroup>
<tbody>
<tr class="odd">
<td></td>
<td><code>\d{4}/\d{1,3}</code></td>
</tr>
<tr class="even">
<td>Correspond à</td>
<td><p>Les codes tels que « 1234/5 », « 1472/69 » ou « 9513/842 » sont composés de quatre chiffres, d’une barre oblique et d’un ou trois chiffres supplémentaires.</p></td>
</tr>
<tr class="odd">
<td>Ne correspond pas à</td>
<td><p>Les codes tels que « 123/45 », « 1472/6985 », ou « 95133/15746 ».</p>
<p><strong>Attention :</strong> Bien que les deux derniers codes ci-dessus ne soient pas complètement correspondants, l’expression donnera la partie « <em>1472/698</em> » de « 1472/6985 », ainsi que la partie « <em>5133/157</em> » de « 95133/15746 ».</p></td>
</tr>
</tbody>
</table>

## De nombreuses expressions

Cette partie présente différents types d’expressions régulières, allant des plus simples aux plus complexes.

Rappelez-vous que la plupart des *caractères alphabétiques* précédés d’un `\` se transforment en une expression qui représente *non pas le caractère lui-même, mais la signification particulière qui lui est associée*.

### Les expressions simples

L’expression régulière la plus simple consiste en un seul caractère, ou en la combinaison d’une `\` et d’un caractère constituant une unité avec une seule signification.

<table>
<caption>Caractères</caption>
<thead>
<tr class="header">
<th style="text-align: left;">Expression</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;"><code>x</code></td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>\t</code></td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>\n</code></td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>\r</code></td>
</tr>
</tbody>
</table>

Caractères

### Casse

Les recherches ordinaires d’OmegaT sont insensibles à la casse par défaut : elles correspondent à la fois aux caractères en majuscules et en minuscules, sauf si vous choisissez d’activer l’option [\#windows.text.search.options](#windows.text.search.options). Dans ce cas, l’ensemble de l’expression de recherche sera sensible la casse.

En revanche, les Expressions régulières sont sensibles à la casse par défaut. Cela signifie qu’une expression régulière recherchant « OmegaT », par exemple, ne correspondra pas à « omegat ». Cependant, il est possible de définir la sensibilité à la casse au sein de l’expression régulière en utilisant des modificateurs spéciaux :

`(?i)`  
Rend la partie de l’expression située à droite du modificateur insensible à la casse.

`(?-i)`  
Rend la partie de l’expression située à droite du modificateur sensible à la casse.

Vous pouvez en profiter pour contrôler avec précision la sensibilité à la casse dans les recherches. Par exemple, supposons que vous souhaitiez trouver des exemples de « OmegaT » et de « omegat », mais pas de « OMEGAT ». Vous pouvez utiliser l’expression suivante : `(?i)o``(?-i)mega` `(?i)t`, qui correspond à un « o » insensible à la casse, suivi d’un « mega » sensible à la casse, suivi d’un « t » insensible à la casse.

### Classes

Les expressions régulières permettent de créer des ensembles de caractères, appelés *classes*. Les recherches correspondront à n’importe quel caractère de l’ensemble.

Les classes sont définies en mettant les caractères souhaités entre crochets et peuvent être précisées soit en énumérant chaque caractère individuel à inclure, soit en définissant une gamme de caractères. Par exemple, vous pourriez créer la classe `[£€$]` pour trouver n’importe lequel de ces trois symboles monétaires dans le texte, ou \[1-3\] pour trouver le chiffre 1, 2 ou 3.

À l’intérieur d’une classe, seuls la barre oblique inverse (`\`), le caret (`^`), le crochet fermant (`]`) et le trait d’union (`-`) sont spéciaux. Les douze autres caractères sont normaux et ne nécessitent pas de barre oblique inverse pour être recherchés comme tels.

Vous pouvez rechercher n’importe lequel des quatre caractères spéciaux de la classe comme des caractères normaux en les faisant précéder d’une barre oblique inverse. Il est possible de rechercher le caret, le crochet fermant et le trait d’union en les positionnant à un endroit qui n’active pas leur signification particulière. Pour cela, il faut les placer n’importe où sauf juste après le crochet ouvrant pour le caret, immédiatement après le crochet ouvrant ou le caret qui le suit pour le crochet fermant, et juste après le crochet ouvrant ou juste avant le crochet fermant pour le trait d’union.

De nombreux ensembles fréquemment utilisés ont une forme abrégée consistant en une barre oblique inverse suivie d’une lettre de l’alphabet. Par exemple, `\d` est une abréviation de `[0-9]`, qui correspond à n’importe quel chiffre entre 0 et 9. Dans de nombreux cas, la majuscule correspondante est utilisée pour annuler la classe : `\D` correspond à tout caractère qui n’est **pas** un chiffre.

Le tableau ci-dessous fournit plusieurs exemples supplémentaires. Ces classes ne représentent pas uniquement la lettre utilisée pour former l’abréviation.

<table>
<caption>Exemples de classes</caption>
<thead>
<tr class="header">
<th style="text-align: left;">Expression</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;"><code>[abc]</code></td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>[C-X]</code></td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>[^\n\r\t]</code></td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>\w</code></td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>\s</code></td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>\h</code> et <code>\v</code></td>
</tr>
</tbody>
</table>

Exemples de classes

Les expressions régulières ne sont pas limitées aux caractères alphanumériques. Elles comprennent l’ensemble des caractères Unicode. Utilisez les blocs, les scripts et les catégories Unicode pour spécifier des classes de caractères en dehors de la gamme des caractères alphanumériques. Quelques exemples sont présentés dans le tableau ci-dessous.

Consultez également le document [Unicode Regular Expressions](https://www.regular-expressions.info/unicode.html) pour vous familiariser avec les expressions régulières Unicode.

<table>
<caption>Blocs, scripts et catégories Unicode</caption>
<thead>
<tr class="header">
<th style="text-align: left;">Expression</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;"><code>\p{InGreek}</code></td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>\p{IsHan}</code></td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>\p{Lu}</code></td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>\p{Sc}</code></td>
</tr>
</tbody>
</table>

Blocs, scripts et catégories Unicode

### Expressions plus avancées

Certaines expressions précisent un emplacement plutôt qu’un caractère. Elles indiquent où la correspondance doit être recherchée dans le texte, mais n’incluent aucun caractère dans cette correspondance. Le tableau ci-dessous énumère les exemples les plus communs. Consultez les sites de la section [\#app.regex.tools](#app.regex.tools) pour plus d’informations.

<table>
<caption>Expressions qui indiquent un emplacement</caption>
<thead>
<tr class="header">
<th style="text-align: left;">Expression</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;"><code>^</code></td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>$</code></td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>\b</code></td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>\B</code></td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>(?=u)</code></td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>(?!u)</code></td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>(?&lt;=q)</code></td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>(?&lt;!q)</code></td>
</tr>
</tbody>
</table>

Expressions qui indiquent un emplacement

## Plus d’exemples

Cette section présente quelques exemples démontrant comment les différentes expressions décrites ci-dessus peuvent être combinées pour effectuer des recherches efficaces dans OmegaT.

<table>
<caption>Exemples d’expressions régulières utilisant les expressions présentées ci-dessus</caption>
<thead>
<tr class="header">
<th style="text-align: left;">Expression</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;"><code>(\b\w+\b)\h\1\b</code></td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>,\h[\h(\w+\.\w+)\w,'ʼ"“”-]+[\.,]</code></td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>\. \h+$</code></td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>\h+a\h+[aeiou]</code></td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>\h+an\h+[^aeiou]</code></td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>\d{4}([/\.-]\d{1,2}){2}</code></td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>\.[A-Z]</code></td>
</tr>
<tr class="even">
<td style="text-align: left;"><code>\ben\b</code></td>
</tr>
<tr class="odd">
<td style="text-align: left;"><code>[\w\.-]+@[\w\.-]+</code></td>
</tr>
</tbody>
</table>

Exemples d’expressions régulières utilisant les expressions présentées ci-dessus

## Références

Bien qu’OmegaT n’offre pas de couleurs extravagantes pour vos expressions régulières, vous pouvez vous exercer en utilisant la fenêtre [\#windows.text.search](#windows.text.search), car OmegaT colore les résultats de la recherche.

Quelques ressources supplémentaires sont présentées ci-dessous.

La référence technique Java est utile en tant que référence de base.

[Documentation Regex Java](https://docs.oracle.com/en/java/javase/11/docs/api/java.base/java/util/regex/Pattern.html)  
La référence officielle pour les expressions régulières utilisées en Java.

Si vous souhaitez en savoir plus sur l’utilisation des expressions régulières, nous vous recommandons les deux sites ci-dessous.

<https://regex101.com>  
Un outil de correspondance d’expressions régulières en ligne qui vous permet de saisir le texte que vous recherchez et les expressions régulières que vous voulez tester.

<https://www.regular-expressions.info>  
L’un des tutoriels et références les plus complets sur le web en ce qui concerne les expressions régulières.

OmegaT ne soutient en aucune façon ces sites. Si vous trouvez d’autres références intéressantes - dans n’importe quelle langue - l’équipe d’OmegaT serait ravie de les découvrir.
