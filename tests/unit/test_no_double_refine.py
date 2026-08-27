"""Product translate+refine must run refine_file once, never in-pipeline too."""
import time
from pathlib import Path

import pytest

from src.api import handlers


class FakeCheckpointManager:
    def start_job(self, translation_id, file_type, config, input_file_path):
        pass

    def cleanup_completed_job(self, translation_id):
        pass

    def mark_interrupted(self, translation_id):
        pass

    def mark_error(self, translation_id):
        pass

    def mark_partial(self, translation_id):
        pass

    def load_checkpoint(self, translation_id):
        return None

    def update_job_config(self, translation_id, config):
        pass


class FakeStateManager:
    def __init__(self, checkpoint_manager):
        self._checkpoint_manager = checkpoint_manager
        self.fields = {
            'logs': [],
            'stats': {'start_time': time.time(), 'total_chunks': 1, 'completed_chunks': 1},
        }

    def exists(self, translation_id):
        return True

    def set_translation_field(self, translation_id, field, value):
        self.fields[field] = value

    def get_translation_field(self, translation_id, field):
        return self.fields.get(field)

    def update_stats(self, translation_id, new_stats):
        self.fields.setdefault('stats', {}).update(new_stats)

    def get_checkpoint_manager(self):
        return self._checkpoint_manager


class FakeSocketIO:
    def emit(self, *args, **kwargs):
        pass


def _base_config(tmp_path, **overrides):
    config = {
        'file_type': 'txt',
        'text': 'Hello world. ' * 20,
        'output_filename': 'out.txt',
        'source_language': 'English',
        'target_language': 'French',
        'model': 'test-model',
        'llm_provider': 'ollama',
        'llm_api_endpoint': 'http://localhost:11434/api/generate',
        'prompt_options': {'refine': True},
        'refine_after': True,
    }
    config.update(overrides)
    return config


async def _run_job(config, tmp_path, monkeypatch):
    calls = {'translate': [], 'refine': []}
    checkpoint_manager = FakeCheckpointManager()
    state_manager = FakeStateManager(checkpoint_manager)

    async def fake_translate_file(**kwargs):
        calls['translate'].append(kwargs)
        Path(kwargs['output_filepath']).write_text('translated', encoding='utf-8')

    async def fake_refine_file(**kwargs):
        calls['refine'].append(kwargs)
        Path(kwargs['output_filepath']).write_text('refined', encoding='utf-8')

    monkeypatch.setattr(handlers, 'translate_file', fake_translate_file)
    monkeypatch.setattr(handlers, 'refine_file', fake_refine_file)
    monkeypatch.setattr(handlers, 'emit_update', lambda *a, **k: None)
    monkeypatch.setattr(handlers, 'notify', lambda *a, **k: None)

    await handlers.perform_actual_translation(
        'job-1', config, state_manager, str(tmp_path), FakeSocketIO()
    )
    return calls


@pytest.mark.asyncio
async def test_refine_after_clears_in_pipeline_flag_and_calls_refine_file_once(tmp_path, monkeypatch):
    config = _base_config(tmp_path)
    calls = await _run_job(config, tmp_path, monkeypatch)

    assert len(calls['translate']) == 1
    assert len(calls['refine']) == 1
    assert calls['translate'][0]['prompt_options']['refine'] is False
    assert calls['refine'][0]['prompt_options']['refine'] is False
    assert config['prompt_options']['refine'] is False


@pytest.mark.asyncio
async def test_epub_refine_after_does_not_request_in_pipeline_refine(tmp_path, monkeypatch):
    epub_path = tmp_path / 'book.epub'
    epub_path.write_bytes(b'PK\x05\x06' + b'\x00' * 18)
    config = _base_config(
        tmp_path,
        file_type='epub',
        file_path=str(epub_path),
        output_filename='out.epub',
    )
    config.pop('text', None)
    calls = await _run_job(config, tmp_path, monkeypatch)

    assert len(calls['translate']) == 1
    assert len(calls['refine']) == 1
    assert calls['translate'][0]['prompt_options'].get('refine') is False


def test_batch_controller_never_sets_prompt_options_refine_from_refine_after():
    source = (
        Path(__file__).resolve().parents[2]
        / 'src' / 'web' / 'static' / 'js' / 'translation' / 'batch-controller.js'
    ).read_text(encoding='utf-8')
    assert 'refine: refineAfter' not in source
    assert 'refine: false' in source
    assert 'refine_after: refineAfter' in source
