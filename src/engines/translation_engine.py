from abc import ABC, abstractmethod

class TranslationEngine(ABC):
    @abstractmethod
    def load_model(self, model_path, device="cpu"):
        """
        Charge le modèle de traduction.
        
        Args:
            model_path (str): Chemin vers le modèle ou nom du modèle
            device (str): 'cpu' ou 'cuda'
            
        Returns:
            bool: True si le chargement a réussi, False sinon
        """
        pass

    @abstractmethod
    def translate(self, text, src_lang, tgt_lang, context=None, glossary_terms=None):
        """
        Traduit le texte source vers la langue cible.
        
        Args:
            text (str): Texte à traduire
            src_lang (str): Code langue source (ex: 'en')
            tgt_lang (str): Code langue cible (ex: 'fr')
            context (str, optional): Contexte lexical ou narratif
            glossary_terms (dict, optional): Dictionnaire de termes forcés {source: target}
            
        Returns:
            str: Texte traduit
        """
        pass

    @abstractmethod
    def translate_batch(self, texts, src_lang, tgt_lang):
        """
        Traduit une liste de textes.
        
        Args:
            texts (list[str]): Liste de textes à traduire
            src_lang (str): Code langue source
            tgt_lang (str): Code langue cible
            
        Returns:
            list[str]: Liste des traductions
        """
        pass

    @abstractmethod
    def get_supported_languages(self):
        """
        Retourne la liste des langues supportées.
        
        Returns:
            list[str]: Codes iso des langues
        """
        pass

    @abstractmethod
    def get_name(self):
        """Retourne le nom du moteur."""
        pass
        
    @abstractmethod
    def is_available(self):
        """Retourne True si le moteur est prêt à être utilisé."""
        pass

    def get_available_models(self):
        """Retourne la liste des modèles disponibles au téléchargement."""
        return []

    def install_model(self, model_id, callback=None):
        """Télécharge et installe un modèle."""
        return False
