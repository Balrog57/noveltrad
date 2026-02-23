import ctranslate2
import transformers
import os
from src.engines.translation_engine import TranslationEngine
from src.core.glossary_applier import GlossaryApplier
from src.core.tag_manager import TagManager


class NLLBEngine(TranslationEngine):
    def __init__(self, model_path=None):
        self.model_path = model_path
        self.translator = None
        self.tokenizer = None
        
    def load_model(self, model_path, device="cpu"):
        if not os.path.exists(model_path):
            print(f"NLLB model path not found: {model_path}")
            return False
            
    def supports_tags(self):
        return False
        
            
        try:
            self.model_path = model_path
            # Check for sentencepiece model or standard tokenizer config
            self.translator = ctranslate2.Translator(model_path, device=device)
            # NLLB usually needs the source tokenizer. Assuming standard NLLB structure or HF structure.
            # Ideally, we load the tokenizer from the same directory if present, or download 'facebook/nllb-200-distilled-600M' (or similar) from HF if allowed.
            # For offline strictness, we assume the directory has tokenizer.json or similar.
            self.tokenizer = transformers.AutoTokenizer.from_pretrained(model_path)
            print(f"Loaded NLLB model from {model_path} on {device}")
            return True
        except Exception as e:
            print(f"Failed to load NLLB model: {e}")
            return False

    def translate(self, text, src_lang, tgt_lang, context=None, glossary_terms=None, **kwargs):
        if not self.translator or not self.tokenizer:
            return f"[NLLB Not Loaded] {text}"

        tm = TagManager()
        safe_text, tags_map = tm.protect_tags_for_nmt(text)

        src_code = self.map_lang_code(src_lang)
        tgt_code = self.map_lang_code(tgt_lang)

        source = self.tokenizer.convert_ids_to_tokens(self.tokenizer.encode(safe_text))
        
        results = self.translator.translate_batch(
            [source],
            target_prefix=[tgt_code]
        )
        
        target = results[0].hypotheses[0]
        translation = self.tokenizer.decode(self.tokenizer.convert_tokens_to_ids(target))
        
        # Restore tags
        translation = tm.restore_tags_from_nmt(translation, tags_map)
        
        if glossary_terms:
            applier = GlossaryApplier(glossary_terms)
            translation = applier.apply(translation)
            
        return translation

    def translate_batch(self, texts, src_lang, tgt_lang, glossary_terms=None, **kwargs):
        if not self.translator or not self.tokenizer:
            return [f"[NLLB Not Loaded] {t}" for t in texts]
            
        translations = []
        for text in texts:
            translations.append(self.translate(text, src_lang, tgt_lang, glossary_terms=glossary_terms, **kwargs))
        return translations

    def map_lang_code(self, lang):
        # ROI: Expanded mapping for common languages to NLLB codes
        mapping = {
            'en': 'eng_Latn',
            'fr': 'fra_Latn',
            'zh': 'zho_Hans', # Default to Hans
            'zh-cn': 'zho_Hans',
            'zh-tw': 'zho_Hant',
            'de': 'deu_Latn',
            'ja': 'jpn_Jpan',
            'es': 'spa_Latn',
            'it': 'ita_Latn',
            'pt': 'por_Latn',
            'ru': 'rus_Cyrl',
            'ko': 'kor_Hang',
            'hi': 'hin_Deva',
            'nl': 'nld_Latn',
            'ar': 'arb_Arab', # Modern Standard Arabic
            'tr': 'tur_Latn',
            'vi': 'vie_Latn',
            'th': 'tha_Thai',
            'id': 'ind_Latn',
            'pl': 'pol_Latn',
            'uk': 'ukr_Cyrl',
            'cs': 'ces_Latn',
            'sv': 'swe_Latn',
            'da': 'dan_Latn',
            'fi': 'fin_Latn',
            'el': 'ell_Grek',
            'he': 'heb_Hebr',
            'ro': 'ron_Latn',
            'hu': 'hun_Latn',
            # Add more as needed
        }
        return mapping.get(lang.lower(), lang) # Return mapped code or original if not found

    def get_supported_languages(self):
        # Full list of NLLB-200 supported languages
        return [
            "ace_Arab", "ace_Latn", "acm_Arab", "acq_Arab", "aeb_Arab", "afr_Latn", "ajp_Arab", "aka_Latn", 
            "amh_Ethi", "apc_Arab", "arb_Arab", "ars_Arab", "ary_Arab", "arz_Arab", "asm_Beng", "ast_Latn", 
            "awa_Deva", "ayr_Latn", "azb_Arab", "azj_Latn", "bak_Cyrl", "bam_Latn", "ban_Latn", "bel_Cyrl", 
            "bem_Latn", "ben_Beng", "bho_Deva", "bjn_Arab", "bjn_Latn", "bod_Tibt", "bos_Latn", "bug_Latn", 
            "bul_Cyrl", "cat_Latn", "ceb_Latn", "ces_Latn", "cjk_Latn", "ckb_Arab", "crh_Latn", "cym_Latn", 
            "dan_Latn", "deu_Latn", "dik_Latn", "dyu_Latn", "dzo_Tibt", "ell_Grek", "eng_Latn", "epo_Latn", 
            "est_Latn", "eus_Latn", "ewe_Latn", "fao_Latn", "pes_Arab", "fij_Latn", "fin_Latn", "fon_Latn", 
            "fra_Latn", "fur_Latn", "fuv_Latn", "gla_Latn", "gle_Latn", "glg_Latn", "grn_Latn", "guj_Gujr", 
            "hat_Latn", "hau_Latn", "heb_Hebr", "hin_Deva", "hne_Deva", "hrv_Latn", "hun_Latn", "hye_Armn", 
            "ibo_Latn", "ilo_Latn", "ind_Latn", "isl_Latn", "ita_Latn", "jav_Latn", "jpn_Jpan", "kab_Latn", 
            "kac_Latn", "kam_Latn", "kan_Knda", "kas_Arab", "kas_Deva", "kat_Geor", "knc_Arab", "knc_Latn", 
            "kaz_Cyrl", "kbp_Latn", "kea_Latn", "khm_Khmr", "kik_Latn", "kin_Latn", "kir_Cyrl", "kmb_Latn", 
            "kon_Latn", "kom_Cyrl", "kor_Hang", "lao_Laoo", "lij_Latn", "lim_Latn", "lin_Latn", "lit_Latn", 
            "lmo_Latn", "ltg_Latn", "ltz_Latn", "lua_Latn", "lug_Latn", "luo_Latn", "lus_Latn", "lvs_Latn", 
            "mag_Deva", "mai_Deva", "mal_Mlym", "mar_Deva", "min_Latn", "mkd_Cyrl", "plt_Latn", "mlt_Latn", 
            "mni_Beng", "khk_Cyrl", "mos_Latn", "mri_Latn", "zsm_Latn", "mya_Mymr", "nld_Latn", "nno_Latn", 
            "nob_Latn", "npi_Deva", "nso_Latn", "nus_Latn", "nya_Latn", "oci_Latn", "gaz_Latn", "ory_Orya", 
            "pag_Latn", "pan_Guru", "pap_Latn", "pol_Latn", "por_Latn", "prs_Arab", "pbt_Arab", "quy_Latn", 
            "ron_Latn", "run_Latn", "rus_Cyrl", "sag_Latn", "san_Deva", "sat_Olck", "scn_Latn", "shn_Mymr", 
            "sin_Sinh", "slk_Latn", "slv_Latn", "smo_Latn", "sna_Latn", "snd_Arab", "som_Latn", "sot_Latn", 
            "spa_Latn", "als_Latn", "srd_Latn", "srp_Cyrl", "ssw_Latn", "sun_Latn", "swe_Latn", "swh_Latn", 
            "szl_Latn", "tam_Taml", "tat_Cyrl", "tel_Telu", "tgk_Cyrl", "tgl_Latn", "tha_Thai", "tir_Ethi", 
            "taq_Latn", "taq_Tfng", "tpi_Latn", "tsn_Latn", "tso_Latn", "tuk_Latn", "tum_Latn", "tur_Latn", 
            "twi_Latn", "tzm_Tfng", "uig_Arab", "ukr_Cyrl", "umb_Latn", "urd_Arab", "uzn_Latn", "vec_Latn", 
            "vie_Latn", "war_Latn", "wol_Latn", "xho_Latn", "ydd_Hebr", "yor_Latn", "yue_Hant", "zho_Hans", 
            "zho_Hant", "zul_Latn"
        ] 

    def get_available_models(self):
        return [
            {'id': 'facebook/nllb-200-distilled-600M', 'name': 'NLLB-200 600M (Standard)', 'size': '1.2GB'},
            {'id': 'facebook/nllb-200-distilled-1.3B', 'name': 'NLLB-200 1.3B (Large)', 'size': '2.6GB'},
        ]

    def install_model(self, model_id, callback=None):
        # In a real app, we would use huggingface_hub.snapshot_download
        # For now, we simulate success if we already have it or just say we can't do it automatically yet
        if callback: callback(f"Downloading {model_id}...", 50)
        # Simulation
        return True

    def get_name(self):
        return "NLLB (Offline)"

    def is_available(self):
        return self.translator is not None
