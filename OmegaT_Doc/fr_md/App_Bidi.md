# Caractères de formatage directionnel

Les caractères de contrôle Bidi sont disponibles à partir de [\#menus.edit](#menus.edit)[\#menus.edit.insert.unicode.control.character](#menus.edit.insert.unicode.control.character). Ils peuvent être utilisés pour :

-   Insérer un caractère invisible à forte directionnalité pour forcer une position spécifique pour un caractère à directionnalité faible ou neutre.

-   Créer une section de texte qui s’écoule dans la direction opposée à celle du segment.

Ces caractères de contrôle changent la directionnalité mais sont invisibles. Utilisez [\#menus.view](#menus.view)[\#menus.view.mark.bidirectional.algorithm.control.character](#menus.view.mark.bidirectional.algorithm.control.character) pour donner une indication visuelle de leur position.

## Marques

Pour modifier la position d’un caractère à directionnalité faible ou neutre (comme les symboles de ponctuation), insérez un caractère LRM ou RLM après le caractère, en fonction de la directionnalité du segment :

-   Insérer un LRM après un caractère à faible directionnalité qui doit aller de gauche à droite dans un segment de droite à gauche (par exemple, un extrait anglais dans un texte arabe).

-   Insérer un RLM après un caractère à faible directionnalité qui doit aller de droite à gauche dans un segment de gauche à droite (par exemple, un extrait en arabe dans un texte en anglais).

## Les intégrations

Les intégrations peuvent être utilisées pour créer une section de texte plus longue (contenant plusieurs mots et espaces) qui doit s’écouler dans la direction opposée à celle du segment. Vous pouvez créer deux types d’intégrations en fonction de la direction du segment :

-   Pour créer une intégration de gauche à droite dans un segment de droite à gauche, insérez un caractère d’intégration de gauche à droite (LRE), saisissez ou insérez le texte de gauche à droite, puis insérez le caractère de formatage directionnel pop (PDF).

-   Pour créer une intégration de droite à gauche dans un segment de gauche à droite, insérez un caractère d’intégration de droite à gauche (RLE), saisissez ou insérez le texte de droite à gauche, puis insérez le caractère PDF.
