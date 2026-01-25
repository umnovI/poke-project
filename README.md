# PokeAPI Retranslator & Caching Proxy

[RU]
Комплексный асинхронный прокси-сервер для PokeAPI. Проект реализует многоуровневое кэширование и трансформацию данных, демонстрируя строгий инженерный подход к сетевым протоколам, конкурентности (concurrency) и оптимизации хранения.

[EN]
A comprehensive asynchronous proxy server for PokeAPI. The project implements multi-level caching and data transformation, demonstrating a rigorous engineering approach to network protocols, concurrency, and storage optimization.

---

## 🚀 Key Engineering Features / Технические особенности

### 1. Hybrid Caching System (L1/L2)
* **L1 (Transport Layer):** Асинхронное кэширование через `Hishel` (FileStorage).
* **L2 (Persistent Layer):** Долговременное хранение в MySQL/MariaDB (SQLModel). Система умеет восстанавливать целостность данных (`localdata.py`), если кэш заголовков и контента рассинхронизирован.
* **EN:** Two-layer caching: fast transport cache via `Hishel` and a persistent layer in MySQL to ensure data availability and integrity even during external API downtime.

### 2. RFC 9110 Compliance (ETag Validation)
* Полноценная поддержка условных запросов (`If-None-Match`).
* Обработка "слабых" (weak) валидаторов и использование `hmac.compare_digest` для безопасного сравнения хэшей.
* Автоматическая обработка статусов `304 Not Modified`.
* **EN:** Full support for conditional requests. Handles "weak" validators and uses `hmac.compare_digest` for timing-attack-safe ETag comparison, reducing bandwidth by up to 99%.

### 3. High-Concurrency Architecture
* Использование `asyncio.TaskGroup` для параллельного сбора данных и агрегации детальной информации о покемонах без блокировки основного потока.
* Механизмы `asyncio.Lock` для предотвращения "Cache Stampede".
* **EN:** Powered by `asyncio.TaskGroup` for high-performance data aggregation. Implements `asyncio.Lock` to prevent redundant upstream requests during cache misses.

### 4. Open Source Contributions
* В процессе разработки был обнаружен и исправлен критический баг Race Condition в библиотеке `Hishel`. Исправление вошло в основной релиз [[PR #181]](https://github.com/karpetrosyan/hishel/pull/181).
* **EN:** Contributed to the `Hishel` core library by fixing a critical Race Condition bug discovered during stress testing of this project.

---

## 🛠 Tech Stack / Технологии

* **Backend:** FastAPI, HTTPX, Hishel.
* **Data:** SQLModel (SQLAlchemy), MySQL/MariaDB.
* **Serialization & Validation:** Pydantic v2, ujson.
* **Tools:** Blake2b (hashing), Pytest, Ruff.

---

## 📂 Project Structure / Структура

### [RU]
* **`app.py`**: Точка входа. Управление жизненным циклом (`lifespan`), middleware аналитики и роутинг с логикой ETag-валидации.
* **`api.py`**: Обработка сетевых вызовов. Фильтрация заголовков, трансформация ссылок и выполнение фоновых задач по синхронизации.
* **`dependencies.py`**: Слой зависимостей FastAPI. Инъекция логики запросов, пагинации и соблюдения стандартов RFC 9110.
* **`localdata.py`**: Логика "умного" персистентного кэша. Агрегация данных через `TaskGroup` и обеспечение целостности БД.
* **`db_config.py`**: Схемы SQLModel. Оптимизированы для работы с `MEDIUMBLOB` и индексацией хэшированных URL.
* **`schemas.py`**: Pydantic-модели. Использование `computed_field` для динамической генерации ETag и хэшей на основе контента.
* **`filters.py`**: Сервис параллельной фильтрации. Сбор и обогащение списков данных медиа-контентом в конкурентном режиме.
* **`utils.py`**: Низкоуровневые утилиты. Кастомная реализация `Paginator`, криптографическое хэширование и работа с base64.
* **`endpoints.py`**: Строго типизированные перечисления (Enum) всех эндпоинтов для исключения ошибок ручного ввода.
* **`shared_config.py`**: Глобальная конфигурация клиентов `httpx` и `hishel`, лимиты соединений и настройки кэша.

### [EN]
* **`app.py`**: Main entry point. Handles `lifespan` events, analytics middleware, and routing with ETag validation logic.
* **`api.py`**: Remote API handler. Manages header filtering, link transformation, and background synchronization tasks.
* **`dependencies.py`**: FastAPI dependency layer. Injects request logic, pagination, and RFC 9110 compliance checks.
* **`localdata.py`**: Smart persistent cache logic. Handles data aggregation via `TaskGroup` and ensures DB integrity.
* **`db_config.py`**: SQLModel schemas. Optimized for `MEDIUMBLOB` storage and hashed URL indexing.
* **`schemas.py`**: Pydantic models. Uses `computed_field` for dynamic ETag and hash generation based on payload content.
* **`filters.py`**: Parallel filtering service. Concurrently enriches data lists with media content.
* **`utils.py`**: Low-level utilities. Custom `Paginator`, Blake2b hashing, and base64 encoding/decoding.
* **`endpoints.py`**: Strongly typed Enums for all valid PokeAPI endpoints to prevent runtime typos.
* **`shared_config.py`**: Centralized configuration for `httpx` and `hishel` clients, including connection limits and TTL.
