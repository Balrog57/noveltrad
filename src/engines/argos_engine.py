from src.engines.translation_engine import TranslationEngine
from src.core.glossary_applier import GlossaryApplier
import argostranslate.package
import argostranslate.translate
import os

class ArgosEngine(TranslationEngine):
    def __init__(self):
        self.current_source = None
        self.current_target = None

    def get_name(self):
        return "Argos Translate"

    def is_available(self):
        return True 

    def load_model(self, model_path="auto", device="cpu"):
        """
        Configures Argos Translate.
        model_path is ignored as Argos manages models globally.
        device sets ARGOS_DEVICE_TYPE.
        """
        if device == "cuda":
            os.environ["ARGOS_DEVICE_TYPE"] = "cuda"
        else:
            os.environ["ARGOS_DEVICE_TYPE"] = "cpu"
            
        # Update index just in case
        try:
            argostranslate.package.update_package_index()
        except:
            pass # Offline or error updating
            
        return True

    def translate(self, text, src_lang, tgt_lang, context=None, glossary_terms=None, **kwargs):
        try:
            # Argos translate expects ISO codes
            translation = argostranslate.translate.translate(text, src_lang, tgt_lang)
            
            # Post-processing glossary application
            if glossary_terms:
                applier = GlossaryApplier(glossary_terms)
                translation = applier.apply(translation)
                        
            return translation
        except Exception as e:
            print(f"Argos Translation Error: {e}")
            return text

    def translate_batch(self, texts, src_lang, tgt_lang, glossary_terms=None, **kwargs):
        translations = [self.translate(t, src_lang, tgt_lang) for t in texts]
        if glossary_terms:
            applier = GlossaryApplier(glossary_terms)
            translations = applier.apply_batch(translations)
        return translations

    def get_supported_languages(self):
        """Returns all languages that COULD be installed/supported."""
        try:
            packages = self.get_available_models()
            codes = set()
            for pkg in packages:
                codes.add(pkg['from_code'])
                codes.add(pkg['to_code'])
            return sorted(list(codes))
        except:
            return []

    def get_installed_languages(self):
        """Returns only currently installed language codes."""
        try:
            languages = argostranslate.translate.get_installed_languages()
            return [lang.code for lang in languages]
        except:
            return []

    def get_available_models(self):
        """Returns list of available language pairs' packages."""
        try:
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()
            return [
                {
                    'id': f"{pkg.from_code}-{pkg.to_code}",
                    'name': f"{pkg.from_name} → {pkg.to_name}",
                    'from_code': pkg.from_code,
                    'to_code': pkg.to_code,
                    'version': pkg.package_version,
                    'size': 'Unknown'
                }
                for pkg in available_packages
            ]
        except Exception as e:
            print(f"Error getting Argos models: {e}")
            return []

    def install_model(self, model_id, callback=None):
        """Install an Argos package by ID (format: from-to)."""
        try:
            from_code, to_code = model_id.split('-')
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()
            package_to_install = next(
                filter(lambda x: x.from_code == from_code and x.to_code == to_code, available_packages), 
                None
            )
            if package_to_install:
                if callback: callback("Downloading...", 10)
                download_path = package_to_install.download()
                if callback: callback("Installing...", 80)
                argostranslate.package.install_from_path(download_path)
                if callback: callback("Installed", 100)
                return True
        except Exception as e:
            print(f"Argos Installation failed: {e}")
        return False

    def install_language_pair(self, from_code, to_code):
        return self.install_model(f"{from_code}-{to_code}")
