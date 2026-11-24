# ToDo AI

AI assistant for the todo app. It answers questions about a user's tasks with **RAG**: tasks are
indexed in **Qdrant** from [todo-api](https://github.com/Domiff/todo-api) events, the relevant ones
are found by meaning for each question, and an LLM (via **OpenRouter**) answers using only them.

## Stack

- **Python 3.14** + [uv](https://github.com/astral-sh/uv)
- [FastAPI](https://fastapi.tiangolo.com/) — HTTP API
- [Qdrant](https://qdrant.tech/) + `qdrant-client[fastembed]` — vector search; embeddings are computed
  locally with [FastEmbed](https://qdrant.github.io/fastembed/)
- **RabbitMQ** + [aio-pika](https://aio-pika.readthedocs.io/) — task events from todo-api
  ([CloudEvents](https://cloudevents.io/) JSON, parsed with pydantic)
- [httpx](https://www.python-httpx.org/) — requests to the LLM (OpenRouter, OpenAI-compatible API)

RabbitMQ, Qdrant and logging (Grafana / Loki) are not part of this repository: they run in the
separate **todo-infrastructure** stack.

## How it works

```
todo-api ──event──► RabbitMQ (todo.tasks) ──► todo-ai.tasks ──► consumer ──► Qdrant
                                                                              │
POST /ai/ask ──► search the user's tasks by meaning ◄─────────────────────────┘
                     │ found tasks
                     ▼
              system prompt + tasks + question ──► LLM ──► answer
```

- **Indexing.** Every task change in todo-api publishes an event with the full task. todo-ai reads
  its own queue `todo-ai.tasks`: `created` / `updated` → index the task, `deleted` → remove it.
  One task is one Qdrant point with `id = task_id`.
- **Embedding.** The vector is built from the task text: title, body and category. If only other
  fields change (status, priority, deadline), the embedding is not recomputed — only the payload
  is updated.
- **Search.** A question is embedded with the same model and searched among the **asking user's**
  tasks only (filter by `user_id`). Up to `RAG_TOP_K` tasks go into the prompt.
- **Answer.** The LLM gets a system prompt with the found tasks and is told to answer only from them.

## Getting started

### Environment variables

Copy `.env_template` to `.env` in the project root (it is gitignored):

```bash
cp .env_template .env
```

The variables:

```env
# LLM (OpenRouter)
API_KEY=                 # OpenRouter API key
AI_URL=https://openrouter.ai/api/v1
MODEL=                   # e.g. a free model, see https://openrouter.ai/models?max_price=0

# HTTP client proxy (optional)
PROXY=                   # e.g. http://127.0.0.1:10809; empty — no proxy
PROXY_HOSTS=["all://openrouter.ai"]   # httpx mount patterns that go through PROXY

# RabbitMQ (same credentials as in todo-infrastructure's .env)
RABBITMQ_USER=
RABBITMQ_PASSWORD=
RABBITMQ_HOST=localhost  # todo-rabbitmq when running in todo-network
RABBITMQ_PORT=5672

# Qdrant
QDRANT_HOST=localhost    # todo-qdrant when running in todo-network
QDRANT_PORT=6333
```

Optional RAG settings (`backend/core/settings.py`, `RagSettings`):

| Variable              | Default                        | Description                                                        |
|-----------------------|--------------------------------|--------------------------------------------------------------------|
| `RAG_COLLECTION`      | `tasks`                        | Qdrant collection name                                             |
| `RAG_EMBEDDING_MODEL` | `Qwen/Qwen3-Embedding-0.6B-Q`  | FastEmbed model; its vector size defines the collection            |
| `RAG_MODELS_DIR`      | `<project>/models`             | where the model is cached (~1.1 GB, ignored by git)                |
| `RAG_TOP_K`           | `5`                            | how many tasks go into the prompt                                  |
| `RAG_SCORE_THRESHOLD` | not set                        | minimum similarity; weaker matches are dropped                     |

> Changing `RAG_EMBEDDING_MODEL` to a model with another vector size needs a new collection
> (a different `RAG_COLLECTION`) and re-indexing: an existing collection is not recreated.

Server settings (`UvicornSettings`), all optional:

| Variable                      | Default   | Description                                                   |
|-------------------------------|-----------|---------------------------------------------------------------|
| `UVICORN_HOST`                | `0.0.0.0` | address to listen on                                          |
| `UVICORN_PORT`                | `8020`    | port (todo-api uses 8000, todo-auth 8010)                     |
| `UVICORN_PROXY_HEADERS`       | `true`    | trust `X-Forwarded-Proto` / `X-Forwarded-For` from a proxy    |
| `UVICORN_FORWARDED_ALLOW_IPS` | `*`       | which addresses may send these headers                        |
| `UVICORN_ROOT_PATH`           | empty     | path prefix, if a proxy serves the app under one              |

### Infrastructure

todo-ai needs, from todo-infrastructure:

- **RabbitMQ** with the queue `todo-ai.tasks` bound to the `todo.tasks` exchange by `tasks.#`
  (declared in `rabbitmq/definitions.json`, imported by the `rabbitmq-init` container);
- **Qdrant** (`qdrant/qdrant`, port 6333).

The Qdrant collection and its payload indexes (`user_id`, `completed`) are created on startup.

### Run

```bash
uv sync
uv run python -m backend.main
```

Or with auto-reload for development:

```bash
uv run fastapi dev --port 8020
```

`python -m backend.main` starts Uvicorn with the settings above; the app itself is
`backend.main:app` (`[tool.fastapi]` in `pyproject.toml`). On startup it connects to
RabbitMQ and Qdrant, creates the collection if needed and starts the queue consumer; if RabbitMQ or
Qdrant is not reachable, startup fails.

The first indexing or search downloads the embedding model from Hugging Face (~1.1 GB) into
`RAG_MODELS_DIR`, so it takes a few minutes. Behind a proxy, set `HTTPS_PROXY` in the environment:
`PROXY` from `.env` is used only by the HTTP client for the LLM.

## Docker Compose

1. Start todo-infrastructure (RabbitMQ with the `todo-ai.tasks` queue and Qdrant).

2. Set the Docker hosts in `.env`: `RABBITMQ_HOST=todo-rabbitmq`, `QDRANT_HOST=todo-qdrant`
   (as in `.env_template`).

3. Build and start the service:
   ```bash
   docker compose up -d --build
   ```

| Service      | Container | Port                 | Notes                                                          |
|--------------|-----------|----------------------|----------------------------------------------------------------|
| AI (Uvicorn) | `todo-ai` | 8020 (not published) | Reachable as `todo-ai:8020` from other services in `todo-network` |

The port is not published and the service is not behind Caddy: `POST /ai/ask` takes `user_id` from
the request body, so it must stay internal until it is authenticated (see [API](#api)).

The embedding model is not in the image: `./models` is mounted to `/app/models`
(`RAG_MODELS_DIR`). If the folder is empty, the model is downloaded there on the first indexing or
search and kept between restarts.

Proxy in Docker:

- `PROXY` must be reachable from the container. `127.0.0.1` or `0.0.0.0` there is the container
  itself, so point it to the host, e.g. `x` with
  `extra_hosts: ["host.docker.internal:host-gateway"]` in `docker-compose.yml`, and let the proxy
  listen on the Docker bridge, not only on `127.0.0.1`.
- Write values in `.env` without quotes when you start the image with `docker run --env-file`: it
  keeps the quotes, and `PROXY="http://..."` fails with `Unknown scheme for proxy URL`.
  `docker compose` strips them.
- The model download goes through `HTTPS_PROXY`, not `PROXY`; add it to `environment:` if Hugging
  Face is reachable only through the proxy.

## API

### `POST /ai/ask` (protected by JWT)

#### Request
```json
{"text": "Do I have tasks about the report?"}
```

#### Response
```json
{"text": "Yes, task 12: Prepare the weekly report."}
```

Interactive docs: `/docs` (only when `IS_DEBUG=true`).

## Project structure

```
backend/
├── main.py                 # app = create_app(); python -m backend.main runs Uvicorn
├── core/
│   ├── settings.py         # pydantic-settings: app, rabbitmq, http, ai, qdrant, rag, uvicorn
│   ├── setup.py            # create_app(), lifespan: connections, collection, consumer
│   ├── http.py             # shared httpx client (timeouts, limits, proxy per host)
│   └── logging.py          # JSON logging
├── infrastructures/
│   ├── rabbitmq.py         # connection, Event[DataT] envelope, consume() / consumer()
│   └── qdrant.py           # AsyncQdrantClient connection
├── rag/
│   ├── schemas.py          # TaskEventTypes, TaskData (event payload), SearchResult
│   ├── stores.py           # QdrantStore: collection, upsert, payload, delete, search
│   ├── services.py         # QdrantService: index_task, delete_task, search_tasks
│   └── handlers.py         # handle_task_event: dispatch by event type
└── assistant/
    ├── schemas.py          # QuestionSchema, AnswerSchema
    ├── services.py         # system prompt, context, LLM request, get_answer
    └── router.py           # POST /ai/ask
models/                     # embedding model cache (gitignored, mounted in Docker)
Dockerfile
docker-compose.yml          # ai service only; infrastructure is in todo-infrastructure
.env_template
```

## Events (RabbitMQ)

```
todo-api ──► todo.tasks (topic) ──tasks.#──► todo-ai.tasks ──► todo-ai
```

| Event type             | Action                          |
|------------------------|---------------------------------|
| `todo.task.created.v1` | index the task                  |
| `todo.task.updated.v1` | re-index the task               |
| `todo.task.deleted.v1` | remove the task from the index  |

The payload is todo-api's `TaskData`; todo-ai reads only the fields it needs (`task_id`, `user_id`,
`title`, `body`, `completed`, `deadline`, `priority`, `category`). An unknown event type is rejected.

If a message fails, it is logged as `Failed to handle message` and rejected without requeue; the
queue has no dead letter queue yet, so such a message is lost. If the consumer itself stops (for
example, the queue does not exist), it is logged as `Consumer stopped`.

Only changes made after todo-ai started are indexed; tasks created earlier have to be indexed once
separately.

## Logging

JSON lines to stdout:

| Message                     | Fields                                    |
|-----------------------------|-------------------------------------------|
| `rag index`                 | `task_id`, `user_id`, `action` (`upsert` / `update_payload`) |
| `rag delete`                | `task_id`                                 |
| `rag search`                | `user_id`, `found`, `scores`              |
| `Failed to handle message`  | `message_id`, `routing_key`, traceback    |
| `Consumer stopped`          | `queue`, traceback                        |

The `scores` of `rag search` help to choose `RAG_SCORE_THRESHOLD` for the model.

## Limitations

- Semantic search returns at most `RAG_TOP_K` tasks, so questions like "what are all my tasks?" or
  "how many tasks do I have?" see only part of them.
- Only the task text goes into the prompt, so the LLM does not see deadlines, status or priority.
- Free OpenRouter models are often rate-limited (`429`); LLM errors are returned as `500`.
