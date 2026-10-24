"""Smoke-тест схем Service."""

from pydantic import ValidationError

from app.modules.monitoring.schemas import ServiceCreate, ServiceUpdate

# Валидные данные
s = ServiceCreate(
    name="Stripe",
    url="https://api.stripe.com/health",
    interval_seconds=30,
)
print("created:", s)
print("url normalized:", s.url)  # HttpUrl → str

# Проверка нормализации url
s = ServiceCreate(name="Stripe", url="HTTPS://API.STRIPE.COM/health")
print("url normalized:", s.url)

# Невалидный URL
try:
    ServiceCreate(name="x", url="not-a-url")
except ValidationError as e:
    print("bad url:", e.error_count())

# interval < 10
try:
    ServiceCreate(name="x", url="https://a.com", interval_seconds=1)
except ValidationError as e:
    print("interval too small:", e.error_count())

# Update — только name
u = ServiceUpdate(name="New name")
print("update dump:", u.model_dump(exclude_unset=True))
# → {"name": "New name"} — только переданное

# Проверка пустого ServiceUpdate
u = ServiceUpdate().model_dump(exclude_unset=True)
print(u)
