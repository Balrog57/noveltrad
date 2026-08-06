"""Dependency composition and injection (SDD 5.9, 20.12 app/container.py).

Assembles the SQLite database, all repositories, services, the provider
factory and the logs into a single Container object used by Streamlit
(main.py) and the Worker (worker.py).
"""

from __future__ import annotations

from pathlib import Path

from noveltrad.core.config import AppConfig, load_config
from noveltrad.core.contracts import CompletionResponse, ValidationReport
from noveltrad.core.database import initialize_schema
from noveltrad.core.file_journal import FileJournal
from noveltrad.core.logging import LogService, setup_logger
from noveltrad.core.security import derive_key, load_or_create_salt
from noveltrad.modules.authentication.service import AuthenticationService
from noveltrad.modules.documents.repository import DocumentRepository
from noveltrad.modules.documents.service import DocumentService
from noveltrad.modules.export.service import ExportService
from noveltrad.modules.jobs.repository import JobRepository
from noveltrad.modules.jobs.service import JobService
from noveltrad.modules.jobs.worker_loop import WorkerLoop
from noveltrad.modules.projects.repository import ProjectRepository
from noveltrad.modules.projects.service import ProjectService
from noveltrad.modules.settings.repository import SettingsRepository
from noveltrad.modules.settings.service import SettingsService
from noveltrad.modules.system.health import HealthService
from noveltrad.modules.system.service import CleanupService, SystemRepository
from noveltrad.modules.translation.pipeline import TranslationService
from noveltrad.modules.translation.providers.factory import ProviderFactory
from noveltrad.modules.verification.service import VerificationService


class Container:
    """Wired application container shared by both processes."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or load_config()
        self.data_dir = Path(self.config.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for sub in ("tmp", "trash", "backups", "projects"):
            (self.data_dir / sub).mkdir(exist_ok=True)

        self.logger = setup_logger(self.config.log_level)
        self.database = initialize_schema(
            self.data_dir / "database.sqlite",
            backups_dir=self.data_dir / "backups",
        )
        conn = self.database.conn

        self.logs = LogService(conn, self.logger)
        self.journal = FileJournal(conn, self.data_dir)
        self.auth = AuthenticationService(self.config.app_password)

        salt = load_or_create_salt(self.data_dir)
        self.encryption_key = (
            derive_key(self.config.app_password or "", salt)
            if self.config.app_password
            else b"\x00" * 32
        )

        self.project_repo = ProjectRepository(conn)
        self.document_repo = DocumentRepository(conn)
        self.job_repo = JobRepository(conn)
        self.settings_repo = SettingsRepository(conn)
        self.system_repo = SystemRepository(conn)

        self.factory = ProviderFactory()
        self.project_service = ProjectService(conn, self.project_repo, self.logs, self.data_dir)
        self.document_service = DocumentService(conn, self.document_repo, self.logs, self.data_dir)
        self.job_service = JobService(conn, self.job_repo, self.logs)
        self.settings_service = SettingsService(
            conn, self.settings_repo, self.logs, self.encryption_key, self.factory
        )
        self.verification_service = VerificationService(conn)
        self.export_service = ExportService(conn, self.logs, self.data_dir)
        self.health_service = HealthService(conn, self.data_dir, self.system_repo)
        self.cleanup_service = CleanupService(conn, self.logs, self.data_dir, self.journal)

        self.system_repo.ensure_runtime_row()
        self._provider: object | None = None

    def build_worker(self) -> WorkerLoop:
        from noveltrad.modules.translation.prompt_loader import PromptLoader

        settings = self.settings_service.get_masked()
        provider = self._build_provider(settings)
        self._provider = provider
        self.translation_service = TranslationService(
            self.database.conn,
            provider,
            self.logs,
            self.data_dir,
            prompt_loader=PromptLoader(),
        )
        return WorkerLoop(
            self.job_service,
            self.translation_service,
            self.logs,
        )

    def _build_provider(self, settings):
        """Build the provider; returns a no-op stub when none is configured,
        so the Worker stays healthy before the first configuration (6.10)."""
        from noveltrad.modules.translation.providers.factory import ProviderFactory

        factory = ProviderFactory()
        if settings.provider is None or not settings.model:
            return _UnconfiguredProvider()
        if str(settings.provider) == "openai_compatible":
            factory.set_api_key(self._settings_api_key())
        return factory.create_from_settings(settings)

    def _settings_api_key(self) -> str | None:

        return self.settings_service._decrypt_api_key()

    def set_api_key(self, api_key: str | None) -> None:
        self.factory.set_api_key(api_key)

    def close(self) -> None:
        if self._provider is not None:
            import asyncio
            import contextlib

            with contextlib.suppress(Exception):
                asyncio.run(self._provider.close())  # type: ignore[attr-defined]
        self.database.close()


class _UnconfiguredProvider:
    """No-op provider stub: no model configured yet (healthy before config)."""

    async def validate_configuration(self, snapshot) -> ValidationReport:
        return ValidationReport(False, ("NO_PROVIDER",), ("no provider configured",))

    async def list_models(self) -> tuple[str, ...]:
        return ()

    async def complete(self, request) -> CompletionResponse:
        from noveltrad.core.exceptions import ProviderError

        raise ProviderError("NO_PROVIDER", False)

    async def close(self) -> None:
        pass
