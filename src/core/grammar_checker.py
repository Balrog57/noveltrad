"""
Grammar and Spelling Checker wrapper for NovelTrad.
Supports French via Grammalecte and other languages via LanguageTool.
"""
import os
import threading
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class GrammarIssue:
    start: int
    end: int
    message: str
    suggestions: List[str]
    rule_id: str
    category: str  # 'grammar', 'spelling', 'typography'
    context: str

class GrammarChecker:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GrammarChecker, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.lt_tool = None
        self.grammalecte_engine = None
        self.current_lang = None
        
        # Try to initialize grammalecte directly
        try:
            import grammalecte
            self.grammalecte_engine = grammalecte.GrammarChecker("fr")
            # Set default options
            self.grammalecte_engine.gce.setOptions({"html": True, "latex": True, "apos": False})
        except ImportError:
            print("Grammalecte library is not installed.")
        except Exception as e:
            print(f"Grammalecte initialization failed: {e}")

        self._initialized = True

    def _get_lt_tool(self, lang_code: str):
        """Lazy load LanguageTool for a specific language."""
        if self.lt_tool and self.lt_tool.language == lang_code:
            return self.lt_tool
            
        try:
            import language_tool_python
            # The user explicitly requested to use the online API for LanguageTool 
            # to avoid downloading the heavy local Java server (~200MB)
            self.lt_tool = language_tool_python.LanguageToolPublicAPI(lang_code)
            return self.lt_tool
        except Exception as e:
            print(f"LanguageTool initialization failed for {lang_code}: {e}")
            return None

    def check(self, text: str, lang_code: str = 'fr') -> List[GrammarIssue]:
        """
        Check text for grammar and spelling issues.
        
        Args:
            text: Text to check.
            lang_code: ISO language code (e.g. 'fr', 'en', 'es').
            
        Returns:
            List of GrammarIssue objects.
        """
        if not text or not text.strip():
            return []

        # Convert simple code to LT/Grammalecte format if needed
        # e.g. 'en-US' or keeping it simple 'fr'
        
        issues = []
        
        # Priority 1: Grammalecte for French
        if lang_code.startswith('fr') and self.grammalecte_engine:
            try:
                # grammalecte.GrammarChecker.getParagraphErrorsAsJSON is what pygrammalecte uses
                # But it's easier to use getParagraphErrors directly if available
                # or just parse the JSON it returns.
                import json
                
                # We use i=0 as paragraph index
                # getParagraphErrors returns a list of errors
                # pygrammalecte uses a custom logic, let's try to match it.
                # Actually, oGrammarChecker.getParagraphErrors(text) returns a list of dictionaries.
                gl_errors = self.grammalecte_engine.getParagraphErrors(text)
                
                for res in gl_errors:
                    # Grammalecte errors can be dicts or objects
                    start = int(getattr(res, 'nStart', res.get('nStart', 0) if isinstance(res, dict) else 0))
                    end = int(getattr(res, 'nEnd', res.get('nEnd', 0) if isinstance(res, dict) else 0))
                    
                    issues.append(GrammarIssue(
                        start=start,
                        end=end,
                        message=getattr(res, 'sMessage', res.get('sMessage', 'Grammar error') if isinstance(res, dict) else 'Grammar error'),
                        suggestions=list(getattr(res, 'aSuggestions', res.get('aSuggestions', []) if isinstance(res, dict) else [])),
                        rule_id=getattr(res, 'sRuleId', res.get('sRuleId', 'unknown') if isinstance(res, dict) else 'unknown'),
                        category=getattr(res, 'sType', res.get('sType', 'grammar') if isinstance(res, dict) else 'grammar'),
                        context=text[max(0, start-20):min(len(text), end+20)]
                    ))
                return issues
            except Exception as e:
                import traceback
                print(f"Direct Grammalecte check failed: {e}")
                traceback.print_exc()
                # Fallback to LT if Grammalecte fails for some reason
        
        # Priority 2: LanguageTool for everything else (or fallback)
        tool = self._get_lt_tool(lang_code)
        if tool:
            try:
                matches = tool.check(text)
                for m in matches:
                    # language-tool-python matches have offset, length (or errorLength), message, replacements, etc.
                    length = getattr(m, 'errorLength', getattr(m, 'length', 0))
                    issues.append(GrammarIssue(
                        start=getattr(m, 'offset', 0),
                        end=getattr(m, 'offset', 0) + length,
                        message=getattr(m, 'message', 'Grammar error'),
                        suggestions=getattr(m, 'replacements', []),
                        rule_id=getattr(m, 'ruleId', 'unknown'),
                        category=getattr(m, 'category', 'grammar'),
                        context=text[max(0, getattr(m, 'offset', 0)-10):min(len(text), getattr(m, 'offset', 0)+length+10)]
                    ))
            except Exception as e:
                print(f"LanguageTool check failed: {e}")
                
        return issues

    def close(self):
        """Cleanup resources."""
        if self.lt_tool:
            try:
                self.lt_tool.close()
            except:
                pass
            self.lt_tool = None
