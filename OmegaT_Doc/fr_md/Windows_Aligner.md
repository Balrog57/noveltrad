# Aligner des fichiers

Utilisez [\#menus.tools](#menus.tools)[\#menus.tools.align.files](#menus.tools.align.files) pour accéder à cet outil.

OmegaT propose également un mode d’alignement en ligne de commande pour les formats basés sur des clés. Voir l’option [\#launch.with.command.line.mode.console.align](#launch.with.command.line.mode.console.align) pour en savoir plus.

Cet outil ne vous permet pas d’enregistrer votre travail au cours d’un alignement. Il est donc recommandé de diviser les fichiers à aligner en fichiers plus courts que vous pourrez aisément aligner en une seule fois. Cela a pour avantage supplémentaire de réduire les incohérences dans l’alignement automatique initial, ce qui rend l’étape de la correction manuelle plus facile.

L’alignement est le processus de création d’une mémoire de traduction bilingue à partir d’une paire de documents monolingues déjà traduits. L’alignement du contenu des dossiers se fait en quatre étapes :

1.  Spécifier les langues source et cible et sélectionner les deux fichiers à aligner.

2.  L’aligneur lit les fichiers et tente d’associer les segments qui correspondent l’un à l’autre dans le texte original et le texte traduit.

3.  Examiner les résultats et procéder aux ajustements manuels nécessaires.

4.  Enregistrer le résultat dans un fichier TMX.

L’aligneur peut lire tous les formats de fichiers pris en charge par OmegaT.

Si vous avez un projet de traduction ouvert, l’aligneur utilisera automatiquement les langues de ce projet, ainsi que les règles de segmentation spécifiques au projet, le cas échéant.

Après avoir sélectionné la langue et les fichiers, cliquez sur le bouton OK pour faire apparaitre la fenêtre Aligner, qui montre les résultats de l’alignement automatique.

La partie principale de la fenêtre est divisée en trois colonnes :

-   Conserver : les paires de segments des lignes dont la case est cochée sont conservées dans le fichier de mémoire de traduction. Les lignes non cochées sont écartées.

-   Source : Les segments du texte original.

-   Cible : les segments du texte traduit.

## Paramètres

Dans cette étape, la partie inférieure de la fenêtre présente divers paramètres et options que vous pouvez modifier si l’alignement initial peut être amélioré. Elle affiche également un résultat Score moyen pour l’alignement. En règle générale, plus le score est bas, plus l’alignement est précis. La modification d’un paramètre recalcule immédiatement l’alignement, ce qui vous permet d’essayer rapidement différentes combinaisons pour obtenir les meilleurs résultats.

Les paramètres et options disponibles sont les suivants :

Mode de comparaison  :  
-   Globale : ce mode compare les documents dans leur ensemble.

-   Par segments : ce mode compare les documents segment par segment. Il n’est affiché que lorsqu’il est applicable pour les fichiers en cours d’alignement.

-   Identifiant : ce mode s’applique aux fichiers constitués d’entrées `clé = valeur`. Ce mode fonctionne même si l’ordre des clés diffère dans chaque fichier et si les fichiers ont un nombre différent d’entrées. Il n’apparait que lorsque les deux fichiers sélectionnés sont reconnus comme des fichiers clé=valeur.

Algorithme :  
-   Viterbi : Les algorithmes par défaut utilisés pour aligner les documents.

-   Avant-Arrière : Un algorithme alternatif qui peut être utilisé pour aligner les documents.

Il n’y a pas de règle absolue quant au choix de l’algorithme. Essayez les deux, et utilisez celui qui donne le meilleur résultat pour vos fichiers.

Calcul :  
-   Normal : La répartition statistique par défaut utilisée pour aligner les documents.

-   Poisson : Une répartition statistique alternative qui peut être utilisée pour aligner les documents.

Comme pour les algorithmes, il n’y a pas de règle absolue quant au choix de la répartition statistique. Essayez les deux, et utilisez celui qui donne le meilleur résultat pour vos fichiers.

Compteur :  
-   Caractère : L’unité de base utilisée pour déterminer la taille des segments dans les langues qui n’utilisent pas d’espace pour délimiter les mots.

-   Mot : L’unité de base utilisée pour déterminer la taille des segments dans les langues qui utilisent une espace pour délimiter les mots.

L’aligneur sélectionne automatiquement le compteur en fonction des langues source et cible des fichiers à aligner. La valeur par défaut est Caractère si au moins une des langues concernées ne délimite pas les mots par des espaces, et Mot dans le cas contraire. Si vous travaillez avec l’un des deux, vous pouvez essayer de passer de l’un à l’autre pour voir lequel donne les meilleurs résultats.

<!-- -->

Segmenter  
L’aligneur utilise par défaut la segmentation par phrases. Décochez la case pour utiliser la segmentation par paragraphes. Voir les préférences [\#dialogs.preferences.segmentation.setup](#dialogs.preferences.segmentation.setup).

Supprimer les balises  
L’aligneur inclut par défaut des balises dans les segments. Décochez la case pour supprimer toutes les balises de l’alignement et du fichier TMX final.

Mettre en évidence  
Décochez la case pour désactiver la mise en évidence.

L’aligneur utilise l’expression régulière `\d+` pour mettre en évidence tous les chiffres dans les segments source et cible.

Vous pouvez modifier l’expression régulière pour mettre en évidence d’autres éléments. Voir le chapitre [\#app.regex](#app.regex) pour en savoir plus.

Règles…  
En cliquant sur ce bouton, vous pouvez modifier les règles de segmentation qui s’appliquent à ce projet. Voir l’annexe [\#app.segmentation](#app.segmentation) pour en savoir plus.

Si vous modifiez les règles de segmentation, il vous sera demandé si vous souhaitez enregistrer ces modifications lorsque vous quitterez l’aligneur. Le choix par défaut est Oui, qui n’est peut-être pas celui que vous souhaitez si vous avez modifié les règles globales de segmentation d’OmegaT.

Filtres…  
En cliquant sur ce bouton, vous pouvez modifier les filtres de fichiers qui s’appliquent à ce projet. Voir le paramètre [\#dialogs.preferences.file.filters](#dialogs.preferences.file.filters) pour en savoir plus.

Si vous modifiez les filtres du fichier, il vous sera demandé si vous souhaitez enregistrer ces modifications lorsque vous quitterez l’aligneur. Le choix par défaut est Oui, qui n’est peut-être pas celui que vous souhaitez si vous avez modifié les règles globales de segmentation d’OmegaT.

Masques…  
Cette option vous permet de saisir une expression régulière pour définir le masque utilisé pour mettre en évidence le texte dans les segments source et cible. Par défaut, l’aligneur utilise `\d+` pour mettre en évidence les chiffres. Si vos textes comportent d’autres éléments qu’il serait utile de mettre en évidence, modifiez l’expression régulière pour inclure ces éléments, en utilisant le symbole `|` pour séparer chaque élément.

Vous pouvez également accéder à l’option Mise en évidence et à la boite de dialogue permettant de modifier le masque à partir du menu Affichage, et aux autres options à partir du menu Options.

De plus, le menu Fichier propose les commandes suivantes :

-   Enregistrer la TMX… : Cet élément est grisé jusqu’à ce que l’étape suivante soit terminée.

-   Réinitialiser : Cette commande rétablit la valeur par défaut de tous les paramètres. Cette commande peut également être exécutée en appuyant sur le bouton Réinitialiser situé en bas à droite de la fenêtre ou en appuyant sur <span class="keycombo">C+S+R</span>

-   Recharger : Cette commande recharge le fichier à partir du disque. Vous pouvez utiliser cette commande pour analyser et aligner à nouveau les fichiers si vous avez dû en modifier le contenu.

-   Fermer : Cette option permet de fermer la boite de dialogue Aligner. Cette étape annule l’alignement sans enregistrer de données dans un fichier de mémoire de traduction. Cette commande peut également être exécutée en appuyant sur <span class="keycombo">C+W</span>.

Le menu Édition est grisé durant cette étape.

Lorsque vous êtes satisfait des résultats à cette étape, cliquez sur le bouton Continuer pour passer à l’étape suivante.

## Corrections

Des ajustements manuels sont généralement nécessaires après la phase initiale d’alignement automatique. Il s’agit généralement de déplacer des segments vers le haut ou vers le bas pour les aligner sur les segments corrects dans l’autre langue, ainsi que de diviser ou de fusionner des segments. L’aligneur vous permet également d’éditer le contenu d’un segment, ce qui peut être utile si vous remarquez des erreurs dans un segment, par exemple une faute d’orthographe.

Toutes les actions disponibles sont accessibles à partir du menu Édition ou en appuyant sur la touche de raccourci correspondante. Les actions les plus courantes sont également accessibles à partir des boutons situés à droite du volet principal.

Les touches de raccourci sont utiles si vous utilisez souvent l’aligneur ou si vous travaillez sur des documents volumineux, car elles vous permettent d’effectuer des manipulations très rapidement.

Pour procéder à un changement, sélectionnez le segment ou le bloc de segments concernés. Les segments individuels peuvent être sélectionnés à l’aide de la souris ou des touches fléchées. Les blocs de segments peuvent être sélectionnés à l’aide de la souris en cliquant sur le premier segment et en maintenant la touche Shift enfoncée tout en cliquant sur le dernier segment.

Vous pouvez également appuyer sur les touches fléchées tout en maintenant la touche Shift enfoncée pour sélectionner des segments consécutifs. Les actions disponibles sont présentées ci-dessous.

Glisser ver le haut (U)  
Déplace le segment sélectionné ou le bloc de segments consécutifs, d’une ligne vers le haut.

Cette commande est également disponible à partir du bouton situé à droite de la fenêtre principale.

Glisser vers le bas (D)  
Déplace le segment sélectionné ou le bloc de segments consécutifs, d’une ligne vers le bas.

Cette commande est également disponible à partir du bouton situé à droite de la fenêtre principale.

Fractionner (S)  
Si un seul segment est sélectionné, cette commande ouvre la boite de dialogue Fractionner le texte. Utilisez la souris ou les touches fléchées pour placer le curseur à l’endroit où vous souhaitez diviser le texte, et cliquez sur le bouton OK ou appuyez sur Entrée.

Si deux segments ou plus occupant des lignes séparées dans la même colonne (segments de plusieurs lignes contenant des lignes où la case Conserver n’est pas cochée) sont sélectionnés, cette commande fractionnera à nouveau les lignes sélectionnées en lignes séparées (en cochant la case Conserver).

Cette commande est également disponible à partir du bouton situé à droite de la fenêtre principale.

Fusionner (M)  
Si un seul segment est sélectionné, l’aligneur le fusionnera avec le segment suivant. Si deux segments ou plus sont sélectionnés, ils seront tous fusionnés, mais resteront placés dans des lignes séparées. Lorsque la commande est exécutée une nouvelle fois sur la même sélection, le contenu de toutes les lignes sélectionnées est fusionné en une seule ligne.

Cette commande est également disponible à partir du bouton situé à droite de la fenêtre principale.

Modifier (E)  
Cette commande ne peut être exécutée que sur un seul segment. La commande ouvre la boite de dialogue Modifier le texte, qui vous permet d’apporter des modifications au texte du segment. Utilisez le bouton OK pour fermer la boite de dialogue une fois que vous avez terminé. Dans cette boite de dialogue, la touche Entrée insère un saut de ligne dans le texte.

utilisez <span class="keycombo">C+Entrée</span> pour la fermer sans utiliser la souris.

Cette commande est également disponible à partir du bouton situé à droite de la fenêtre principale.

Marquer accepté (A)  
Cette commande permet de confirmer que l’alignement des segments de la ligne ou du bloc de lignes sélectionné est correct. La colonne Conserver apparait en vert.

Marquer à vérifier (R)  
Cette commande permet d’identifier une ligne ou un bloc de lignes dont l’alignement des segments est incertain. La colonne Conserver apparait en rouge.

Effacer la marque (C)  
Utilisez cette commande pour supprimer une ou plusieurs marques définies par les commandes Marquer accepté ou Marquer à vérifier.

Réaligner les éléments en attente (<span class="keycombo">C+R</span>)  
Si des lignes ont été marquées comme acceptées, utilisez cette commande pour mettre à jour l’alignement des lignes restantes.

Conserver tout  
Cette commande permet de cocher la case Conserver pour toutes les lignes.

Ne rien conserver  
Cette commande permet de décocher la case Conserver pour toutes les lignes.

Inverser la sélection (K)  
Utilisez cette commande pour faire cocher ou décocher la case Conserver de la ligne ou du bloc de lignes sélectionnées.

Démarrer l’alignement précis (Espace)  
Si les segments correspondants sont séparés par plusieurs lignes et que vous souhaitez les aligner rapidement, utilisez cette commande pour sélectionner le premier segment et cliquez ensuite sur le segment correspondant dans l’autre colonne.

Vous pouvez également utiliser les touches fléchées et appuyer sur Espace dans le segment correspondant.

Les segments alignés en utilisant cette méthode sont automatiquement marqués comme acceptés.

Il peut être utile d’exécuter la commande Réaligner les éléments en attente après avoir utilisé plusieurs fois la commande d’alignement précis.

Une fois terminé l’alignement des deux colonnes, cliquez sur le bouton Enregistrer la TMX… pour créer la mémoire de traduction.

Seules les lignes dont la case Conserver est cochée dans la première colonne sont enregistrées dans la mémoire de traduction.

En plus du bouton Enregistrer la TMX…, la partie inférieure de la fenêtre Aligner de l’étape de correction manuelle comporte la même case à cocher Mettre en évidence et le même bouton Masques… que dans la première étape. Cette option est également accessible à partir du menu Affichage.

Il existe également un bouton Réinitialiser situé en bas de la fenêtre. **Utilisez-le avec précaution !** En cliquant sur ce bouton, vous annulez toutes vos modifications et vous revenez à la première étape.
