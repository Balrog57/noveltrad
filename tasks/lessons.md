# Leçons Apprises (Memory)

## Modèles d'Erreurs Récents
- **Erreur** : `AttributeError: 'DictionaryManager' object has no attribute 'has_language'`
  - **Cause** : La méthode manquait dans `DictionaryManager` pour vérifier la présence d'une langue au sein d'une DB locale, déclenchant un crash de l'UI sur appel de `load_languages_into_footer`.
  - **Solution** : Ajouter `@staticmethod def has_language(...) -> bool` permettant une requête peewee `.exists()` sur `GlobalDictionaryTerm`.
- **Erreur** : `deep-translator library not found`
  - **Cause** : Dépendance manquante dans l'environnement.
  - **Solution** : Exécuter `pip install deep-translator` pour activer les fonctions de fallback Google.
- **Concept** : Les dialogues UI (Custom Instructions, Concordancer, Search/Replace) étaient préparés mais leurs "slots" Qt et leurs accès via `MainWindow` n'existaient pas. Il faut systématiquement vérifier si l'Action Menu est associée à son handler Python.
- **Règle UI** : Éviter la redondance stricte. Si une action est présente avec une icône visuelle évidente (Undo, Redo, Save) dans le header, elle doit être retirée des menus textuels pour garder une interface "Propre" et éviter la confusion de "double action".
- **PyQt Naming** : Faire attention aux noms de méthodes intégrées. Utiliser toujours `statusBar()` (méthode) au lieu de tenter d'instancier un membre `status_bar` par erreur de nommage, ce qui mène à des `AttributeError`.
