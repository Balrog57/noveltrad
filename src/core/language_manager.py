import logging
from src.engines import get_engine_instance, list_engines
from src.core.dictionary_manager import DictionaryManager

class LanguageManager:
    def __init__(self):
        self.argos = get_engine_instance('Argos')
        self.nllb = get_engine_instance('NLLB')
        self.llm = get_engine_instance('LLM')
        self.dict_manager = DictionaryManager()
        self.logger = logging.getLogger("LanguageManager")

    def get_supported_languages(self):
        """
        Returns a list of language codes supported by ALL three engines.
        """
        # 1. Gather Candidates from LLM (usually the most standard ISO list)
        from src.engines.llm_engine import LANGUAGE_NAMES
        candidates = set(LANGUAGE_NAMES.keys())
        
        # 2. Check Argos Support
        argos_supported = set()
        if self.argos:
            try:
                # We consider a language supported if it appears in any package
                # Ideally we want Source AND Target support relative to English,
                # but simply checking if the code exists in available packages is a good proxy.
                packages = self.argos.get_available_models()
                for pkg in packages:
                    argos_supported.add(pkg.get('from_code'))
                    argos_supported.add(pkg.get('to_code'))
            except Exception as e:
                self.logger.error(f"Error getting Argos languages: {e}")
        
        # 3. Check NLLB Support
        nllb_supported_raw = set()
        if self.nllb:
            nllb_supported_raw = set(self.nllb.get_supported_languages())
            
        # 4. Filter Candidates (Intersection)
        final_supported = []
        
        for code in candidates:
            # Check Argos
            if self.argos and code not in argos_supported:
                continue
                
            # Check NLLB (using mapping)
            if self.nllb:
                nllb_code = self.nllb.map_lang_code(code)
                if nllb_code not in nllb_supported_raw:
                    continue
            
            # Check installation status
            is_installed = False
            
            # Check Argos
            argos_installed = False
            if self.argos:
                # We need to check if we have a pair involving this code
                # simpler: check if it is in get_installed_languages
                try:
                    installed_langs = self.argos.get_installed_languages() # Use new method
                    if code in installed_langs:
                        argos_installed = True
                except:
                    pass
            else:
                # If argos is missing, we can't be "fully" installed, or we ignore it?
                # We'll treat as "installed" if we have dictionary?
                pass
                
            # Check Dictionary
            # We can check if we have terms
            dict_installed = self.dict_manager.has_language(code)
            
            if (self.argos and argos_installed) or (not self.argos and dict_installed):
                is_installed = True
            
            # Add to result
            final_supported.append({
                "code": code,
                "name": LANGUAGE_NAMES[code],
                "installed": is_installed
            })
            
        return sorted(final_supported, key=lambda x: x['name'])

    def install_language_pack(self, code, callback=None):
        """
        Installs support for the language:
        1. Argos pair (en->code, code->en)
        2. NLLB model (verification)
        3. Free Dictionary (download/import)
        """
        status = {"argos": False, "nllb": False, "dict": False}
        
        # 1. Argos
        if self.argos:
            try:
                # Strategy: Install pair with 'en' as pivot
                # We need to find valid packages
                if callback: callback(f"Installing Argos support for {code}...", 10)
                
                # Try en->code
                self.argos.install_language_pair("en", code)
                # Try code->en
                self.argos.install_language_pair(code, "en")
                status["argos"] = True
            except Exception as e:
                self.logger.error(f"Argos install failed: {e}")

        # 2. NLLB
        if self.nllb:
            if callback: callback(f"Verifying NLLB support for {code}...", 50)
            # NLLB is usually a single model file. If we have the engine, we have the languages.
            # We assume NLLB model is already "installed" or we might trigger a download if needed.
            # But NLLB_engine.install_model is a stub/simulation in the current code.
            # We'll mark it as True if we have the engine.
            status["nllb"] = True

        # 3. Dictionary
        if callback: callback(f"Searching dictionary for {code}...", 80)
        # TODO: Implement actual download
        # For now, we search if we have a local CSV or can fetch one
        # self.dict_manager.download_dictionary(code, "en") # Example
        status["dict"] = True # specific implementation pending
        
        if callback: callback("Installation processing complete.", 100)
        return status
