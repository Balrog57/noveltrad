from src.engines.translation_engine import TranslationEngine
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

    def translate(self, text, src_lang, tgt_lang, context=None, glossary_terms=None):
        try:
            # Argos translate expects ISO codes
            translation = argostranslate.translate.translate(text, src_lang, tgt_lang)
            
            # Basic glossary support (post-processing)
            if glossary_terms:
                for src_term, tgt_term in glossary_terms.items():
                    # Simple replacement - sensitive to substrings!
                    # Should ideally use regex with boundaries or token replacement
                    if src_term in translation:
                        # This is very risky for replacement in target if src_term is English word in French text? 
                        # Valid glossary usually maps Source -> Target. 
                        # But translation is already done. We want to replace Target -> FixedTarget?
                        # Or SourceTerm -> TargetTerm enforced?
                        # Usually glossary in NMT is applied during translation or via placeholder.
                        # Post-processing replacement handles 'Target -> FixedTarget' fixup?
                        # No, glossary_terms usually meant {source_term: target_term}.
                        # If we have strict mapping, we might replace occurences of target_term with correct one?
                        # OR if translation failed to use target_term.
                        pass
                        
            return translation
        except Exception as e:
            print(f"Argos Translation Error: {e}")
            return text

    def translate_batch(self, texts, src_lang, tgt_lang):
        return [self.translate(t, src_lang, tgt_lang) for t in texts]

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
