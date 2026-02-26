# Outils

Ce menu vous permet d’accéder à certains outils comme la validation d’assurance qualité, les statistiques de correspondances, l’aligneur, et les scripts.

Sur Windows et Linux : <span class="keycombo">Ctrl+Maj+V</span>

Sur macOS : <span class="keycombo">Maj+commande+V</span>

**Dans ce manuel :** <span class="keycombo">C+Maj+V</span>

Afficher les erreurs… <span class="keycombo">C+Maj+V</span>  
L’outil d’assurance de qualité effectue toutes les vérifications automatiques en une fois et affiche les résultats dans une fenêtre.

Quatre types de problèmes peuvent être détectés :

-   Problèmes de balises (toujours activée) : détecte les balises manquantes ou mal placées, y compris les balises personnalisées et les textes signalés. Voir les préférences [\#dialogs.preferences.tag.processing](#dialogs.preferences.tag.processing) pour en savoir plus.

    Cette option est toujours activée.

-   Erreurs d’orthographe (optionnelle) : détecte les fautes d’orthographe. Fonctionne seulement si un dictionnaire orthographique est installé. Voir les préférences [\#dialog.preferences.spellchecker](#dialog.preferences.spellchecker) pour en savoir plus.

-   Problèmes de terminologie (optionnelle) : détecte tous les éléments de glossaires qui ne sont pas traduits correctement. Voir les préférences [\#dialogs.preferences.glossary](#dialogs.preferences.glossary) pour en savoir plus.

-   Erreurs LanguageTool (optionnelle) : détecte les problèmes grammaticaux ou typographiques Voir les préférences [\#dialog.preferences.languagetool.plugin](#dialog.preferences.languagetool.plugin) pour en savoir plus.

Les résultats sont disposés sous la forme d’un tableau dans lequel :

-   Double-cliquer sur une ligne active le segment correspondant dans le volet Éditeur.

-   Cliquer sur un entête de colonne modifie l’ordre de tri de la colonne.

-   Sélectionner ou déplacer la souris sur une ligne va afficher une icône de menu contextuel à l’extrémité droite de la ligne. Cliquer sur cette icône va vous présenter les actions disponibles pour corriger ou ignorer l’erreur.

    Pour forcer la vérification orthographique à chaque fois que vous quittez un segment, activez la préférence [\#dialogs.preferences.editor.validate.tags.when.leaving.a.segment](#dialogs.preferences.editor.validate.tags.when.leaving.a.segment).

    Pour empêcher la création de fichiers traduits s’il y a des problèmes de balises, activez la préférence [\#dialogs.preferences.tag.processing.do.not.allow.creating.translated.documents.with.tag.issues](#dialogs.preferences.tag.processing.do.not.allow.creating.translated.documents.with.tag.issues).

Afficher les erreurs pour le document actuel  
Comme ci-dessus, mais seulement pour le document actif dans le volet Éditeur.

Statistiques  
Ouvre une nouvelle fenêtre et affiche les statistiques du projet telles que le nombre de mots ou les totaux des segments, ainsi que les totaux de chaque fichier du projet.

Les données sont enregistrées dans le fichier [\#project.folder.project.stats](#project.folder.project.stats) qui est situé dans le dossier [\#project.folder.omegat.folder](#project.folder.omegat.folder) du projet.

Le nombre de mots, le total des segments, et d’autres éléments peuvent être influencés par les facteurs suivants :

-   Les paramètres de filtres de fichiers : certains filtres permettent à des parties supplémentaires d’être prises en compte pour la traduction. Voir les [options](#filters.options) de filtre de fichier pour en savoir plus.

-   Règles de segmentation : différentes règles vont générer un différent nombre de segments. Voir l’annexe [\#app.segmentation](#app.segmentation) pour en savoir plus.

-   Balises : Les balises OmegaT ne sont jamais comptées dans les statistiques, mais dans certains elles peuvent diviser des termes et créer des divergences dans la façon dont OmegaT les comptabilise. Voir le paramètre [\#dialogs.project.properties.hide.tags](#dialogs.project.properties.hide.tags) dans la boite de dialogue [\#dialogs.project.properties](#dialogs.project.properties) pour en savoir plus.

-   Balises personnalisées et textes signalés : comme les balises OmegaT, ils ne sont pas comptés par défaut dans les statistiques, mais vous pouvez demander à OmegaT de les compter comme des mots. Voir le paramètre [\#dialogs.preferences.tag.processing.count.protected.text.and.custom.tags.in.statistics](#dialogs.preferences.tag.processing.count.protected.text.and.custom.tags.in.statistics) pour en savoir plus.

Statistiques des correspondances  
Montre les statistiques des correspondances du projet, c’est-à-dire le nombre de répétitions, de correspondances exactes, de correspondances partielles, et d’absences de correspondances pour les segments, les mots, et les caractères.

Les données sont enregistrées dans le fichier [\#project.folder.omegat.project.stats.match](#project.folder.omegat.project.stats.match) qui est situé dans le dossier [\#project.folder.omegat.folder](#project.folder.omegat.folder) du projet.

Statistiques des correspondances par fichier  
Montre les statistiques des correspondances du projet individuelles pour chaque fichier du projet, c’est-à-dire le nombre de répétitions, de correspondances exactes, de correspondances partielles, et d’absences de correspondances pour les segments, les mots, et les caractères.

Les données sont enregistrées dans le fichier [\#project.folder.omegat.project.stats.match.per.file](#project.folder.omegat.project.stats.match.per.file) qui est situé dans le dossier [\#project.folder.omegat.folder](#project.folder.omegat.folder) du projet.

Aligner les fichiers…  
Sélectionner les deux fichiers à aligner (le fichier source et sa traduction) et cliquer sur OK pour ouvrir la fenêtre [\#windows.aligner](#windows.aligner).

Les formats de fichiers pris en charge dépendent des paramètres de votre projet. Voir l’annexe [\#file.filters](#file.filters) pour en savoir plus.

Les fichiers source et cible peuvent être dans des formats différents (par exemple, un fichier `.docx` peut être aligné avec un fichier `.pdf`).

Scripts…  
Ouvre la fenêtre [\#windows.scripts](#windows.scripts), qui vous permet de définir l’emplacement où les scripts se trouvent, ainsi que d’écrire et d’exécuter des scripts, et leur assigner un raccourci.

La liste sous cet élément affiche 12 emplacements potentiels pour des scripts. Cliquer sur un emplacement assigné permet de lancer le script assigné à cet emplacement.

Pour assigner un numéro à un script :

1.  Ouvrez la fenêtre des scripts

2.  Sélectionnez le script à associer dans la liste à gauche

3.  Faites un clic droit sur un numéro libre au bas de la fenêtre et choisissez Ajouter le script.

Commandes de recherches externes  
Si vous avez défini des recherches externes dans les paramètres [\#dialogs.preferences.external.searches](#dialogs.preferences.external.searches), ils sont listés et accessibles ici.
