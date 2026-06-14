def replace_translate_batch():
    with open('src/backend/engines/nllb_engine.py', 'r') as f:
        content = f.read()

    old_method = """    def translate_batch(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
    ) -> list[str]:
        if not texts:
            return []

        # If test mode, fallback or multiblock is needed, fallback to loop.
        # This keeps edge-cases safe while allowing normal text to be batched.
        if (
            not self.available
            or os.environ.get("NOVELTRAD_TRANSLATION_TEST_MODE") in {"1", "true", "yes"}
            or any("\\n" in t for t in texts)
        ):
            return [self.translate(t, source_lang, target_lang) for t in texts]

        # Keep track of empty strings to return them as-is
        non_empty_indices = [i for i, t in enumerate(texts) if t.strip()]
        non_empty_texts = [texts[i] for i in non_empty_indices]

        if not non_empty_texts:
            return texts

        # True batch processing with CTranslate2
        with self._lock:
            src_code = to_nllb_code(source_lang)
            tgt_code = to_nllb_code(target_lang)

            # Tokenize all non-empty texts
            source_tokens_batch = []

            for text in non_empty_texts:
                tokens = self._sp.encode(text.strip(), out_type=str)  # type: ignore[union-attr]
                source_tokens_batch.append([src_code, *tokens, "</s>"])

            # Call CTranslate2 translate_batch natively
            results = self._translator.translate_batch(  # type: ignore[union-attr]
                source_tokens_batch,
                batch_type="tokens",
                target_prefix=[[tgt_code]] * len(source_tokens_batch),
                beam_size=4,
                max_decoding_length=256,
            )

            # Decode all results
            decoded_results = []
            for res in results:
                out_tokens = res.hypotheses[0]
                # Strip the language token at the start
                if out_tokens and out_tokens[0] == tgt_code:
                    out_tokens = out_tokens[1:]
                decoded_results.append(self._sp_target.decode(out_tokens))  # type: ignore[union-attr]

            # Reassemble the final list including empty strings
            final_results = []
            decoded_idx = 0
            for text in texts:
                if not text.strip():
                    final_results.append(text)
                else:
                    final_results.append(decoded_results[decoded_idx])
                    decoded_idx += 1

            return final_results"""

    new_method = """    def translate_batch(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
    ) -> list[str]:
        if not texts:
            return []

        # If test mode, fallback or multiblock is needed, fallback to loop.
        # This keeps edge-cases safe while allowing normal text to be batched.
        if (
            not self.available
            or os.environ.get("NOVELTRAD_TRANSLATION_TEST_MODE") in {"1", "true", "yes"}
            or any("\\n" in t for t in texts)
        ):
            return [self.translate(t, source_lang, target_lang) for t in texts]

        # Keep track of empty strings to return them as-is
        non_empty_indices = [i for i, t in enumerate(texts) if t.strip()]
        non_empty_texts = [texts[i] for i in non_empty_indices]

        if not non_empty_texts:
            return texts

        # True batch processing with CTranslate2
        with self._lock:
            try:
                src_code = to_nllb_code(source_lang)
                tgt_code = to_nllb_code(target_lang)

                # Tokenize all non-empty texts
                source_tokens_batch = []

                for text in non_empty_texts:
                    tokens = self._sp.encode(text.strip(), out_type=str)  # type: ignore[union-attr]
                    source_tokens_batch.append([src_code, *tokens, "</s>"])

                # Call CTranslate2 translate_batch natively
                results = self._translator.translate_batch(  # type: ignore[union-attr]
                    source_tokens_batch,
                    batch_type="tokens",
                    target_prefix=[[tgt_code]] * len(source_tokens_batch),
                    beam_size=4,
                    max_decoding_length=256,
                )

                # Decode all results
                decoded_results = []
                for res in results:
                    out_tokens = res.hypotheses[0]
                    # Strip the language token at the start
                    if out_tokens and out_tokens[0] == tgt_code:
                        out_tokens = out_tokens[1:]
                    decoded_results.append(self._sp_target.decode(out_tokens))  # type: ignore[union-attr]
            except Exception as exc:
                logger.exception("NLLB translate_batch failed")
                return texts

        # Reassemble the final list including empty strings
        # outside of the lock
        final_results = []
        decoded_idx = 0
        for text in texts:
            if not text.strip():
                final_results.append(text)
            else:
                final_results.append(decoded_results[decoded_idx])
                decoded_idx += 1

        return final_results"""

    if old_method in content:
        content = content.replace(old_method, new_method)
        with open('src/backend/engines/nllb_engine.py', 'w') as f:
            f.write(content)
        print("Success")
    else:
        print("Failed to find old method")

replace_translate_batch()
