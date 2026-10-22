"""Реестр всех ORM-моделей для Alembic.

Этот файл импортирует все модели, чтобы они зарегистрировались в Base.metadata.
Alembic через env.py импортирует только этот файл — так проще поддерживать.
"""

from app.modules.auth.models import User
from app.modules.monitoring.models import Service

__all__ = ["Service", "User"]
