import logging

# Define placeholders or try-imports to handle platform/version incompatibilities
try:
    from src.engines.nllb_engine import NLLBEngine
except ImportError:
    NLLBEngine = None
    logging.warning("NLLBEngine could not be loaded.")

try:
    from src.engines.llm_engine import LLMEngine
except ImportError:
    LLMEngine = None
    logging.warning("LLMEngine could not be loaded.")

try:
    from src.engines.argos_engine import ArgosEngine
except Exception as e:
    # Argos/Spacy has issues with Python 3.14+ Pydantic V1
    ArgosEngine = None
    logging.error(f"ArgosEngine could not be loaded: {e}")

ENGINES = {}
if NLLBEngine: ENGINES['NLLB'] = NLLBEngine
if LLMEngine: ENGINES['LLM'] = LLMEngine
if ArgosEngine: ENGINES['Argos'] = ArgosEngine

def get_engine_class(name):
    """Returns the class for the given engine name."""
    return ENGINES.get(name)

def get_engine_instance(name, **kwargs):
    """Returns an instance of the engine."""
    cls = ENGINES.get(name)
    if cls:
        return cls(**kwargs)
    return None

def list_engines():
    """Returns list of available engine names."""
    return list(ENGINES.keys())
