# Connector API

## Installation

### Docker

```shell
docker build -t rest-backend . --progress=plain --no-cache
docker run --name rest-backend -e PORT=10000 -p 10000:10000 -d rest-backend
```

### Local (coming soon)

- Development:

    ```shell
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-include .env
    ```

- Production:

    ```shell
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
    ```
