# Dossier de configuration

Le dossier de configuration contient la majorité des options et des préférences d’OmegaT.

Utilisez [\#menus.options](#menus.options)[\#menus.options.access.configuration.folder](#menus.options.access.configuration.folder) pour y accéder directement.

## Emplacement

L’emplacement du dossier de configuration par défaut varie selon le système (le caractère *~* représente votre dossier local)  :

Linux  
`~/.omegat`

macOS  
`~/Library/Preferences/OmegaT`

Windows  
`~\AppData\Roaming\OmegaT`

Vous pouvez préciser un dossier de configuration autre que celui défini par défaut lorsque vous démarrez OmegaT à partir de la ligne de commande. Voir le guide pratique [\#launch.with.command.line](#launch.with.command.line) pour en savoir plus.

Les préférences modifiées sont stockées dans le dossier de configuration du projet. Les modifications apportées dans les [préférences](#chapter.dialogs.preferences) seront stockées dans le dossier de configuration précisé et n’apparaitront pas lorsque vous reprendrez le travail avec le dossier de configuration par défaut.

## Contenu par défaut

omegat.prefs  
Ce fichier contient un certain nombre de préférences personnelles.

Certaines préférences n’ont pas d’équivalent dans l’interface graphique. Vous devez les modifier manuellement.

Pour éviter l’affichage de la liste des fichiers du projet à chaque rechargement, cherchez &lt;project\_files\_show\_on\_load&gt; et remplacez true par false :

    <project_files_show_on_load>false</project_files_show_on_load>

Cette préférence est la seule qui nécessite une modification manuelle (pour l’instant).

uiLayout.xml  
Ce fichier décrit la présentation générale d’OmegaT.

logs/  
Ce dossier contient un certain nombre de fichiers journaux. Le plus récent est `OmegaT.log`.

Ces fichiers enregistrent divers messages d’état interne et d’événements de programme générés pendant qu’OmegaT est en cours d’exécution. Ajoutez ce fichier, ou la partie correspondante, à votre rapport si OmegaT se comporte de manière anormale.

Pour afficher le contenu du fichier, utilisez [\#menus.help](#menus.help)[\#menus.help.log](#menus.help.log).

Le dossier script/  
Ce dossier peut contenir jusqu’à trois fichiers texte si les fonctions applicables sont utilisées :

selection.txt  
Ce fichier conserve le texte sélectionné lorsque [\#menus.edit](#menus.edit)[\#menus.edit.export.selection](#menus.edit.export.selection) est utilisé. Le texte du fichier est remplacé chaque fois que cette fonction est appliquée.

source.txt  
Ce fichier contient le *texte original* du segment en cours lorsque la préférence [\#dialogs.preferences.editor.export.the.segment.to.text.files](#dialogs.preferences.editor.export.the.segment.to.text.files) est activée. Le texte du fichier est remplacé à chaque fois qu’un nouveau segment est introduit.

target.txt  
Ce fichier contient le *texte traduit* du segment en cours lorsque la préférence [\#dialogs.preferences.editor.export.the.segment.to.text.files](#dialogs.preferences.editor.export.the.segment.to.text.files) est activée. Le texte du fichier est remplacé à chaque fois qu’un nouveau segment est introduit.

Ces trois fichiers constituent un moyen simple d’accéder au contenu d’OmegaT et de le traiter à l’aide de programmes locaux tels que les scripts shell.

## Contenu supplémentaire

EditorShortcuts.properties  
Ce fichier de paramètres contient des raccourcis personnalisés pour l’éditeur. Voir l’annexe [\#app.shortcuts.customization](#app.shortcuts.customization) pour en savoir plus.

MainMenuShortcuts.properties  
Ce fichier de paramètres contient des raccourcis personnalisés pour l’interface graphique. Voir l’annexe [\#app.shortcuts.customization](#app.shortcuts.customization) pour en savoir plus.

filters.xml  
Ce fichier de paramètres contient des filtres de fichiers personnalisés. Voir le paramètre [\#dialogs.preferences.file.filters](#dialogs.preferences.file.filters) pour en savoir plus.

finder.xml  
Ce fichier de paramètres contient des paramètres de recherche externe personnalisés. Voir le paramètre [\#dialogs.preferences.external.searches](#dialogs.preferences.external.searches) pour en savoir plus.

omegat.autotext  
Ce fichier de paramètres contient les paramètres personnalisés de l’insertion automatique. Voir le paramètre [\#dialog.preferences.auto.completion](#dialog.preferences.auto.completion) pour en savoir plus.

repositories.properties  
Ce fichier contient les informations d’authentification pour vos dépôts de projets en équipe.

Le contenu du fichier n’est pas crypté.

Voir le guide pratique [\#how.to.setup.team.project](#how.to.setup.team.project) pour en savoir plus.

segmentation.conf  
Ce fichier de paramètres contient des paramètres de segmentation personnalisés. Voir le paramètre [\#dialogs.preferences.segmentation.setup](#dialogs.preferences.segmentation.setup) pour en savoir plus.

plugins/  
Ce dossier fournit l’emplacement standard pour les plug-ins d’extension d’OmegaT installés manuellement. Voir le paramètre [\#dialogs.preferences.plugins](#dialogs.preferences.plugins) pour en savoir plus.

Il est également possible d’installer des plug-ins dans le dossier de l’application [\#application.folder.plugins](#application.folder.plugins).

spelling/  
Ce dossier contient vos dictionnaires orthographiques. Voir le paramètre [\#dialog.preferences.spellchecker](#dialog.preferences.spellchecker) pour en savoir plus.
