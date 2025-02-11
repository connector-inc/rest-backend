# Connector API

## Installation

### 1. Generate certificates

- mkcert:

    ```shell
    sudo mkcert -install
    sudo mkcert localhost 127.0.0.1 ::1
    ```

### 2. Running the server

<!-- #### PowerShell

```shell
uv run uvicorn app.main:app `
    --env-file ./.env `
    --host 0.0.0.0 `
    --port 8000 `
    --ssl-keyfile ./certificates/key.pem `
    --ssl-certfile ./certificates/cert.pem `
    --workers 4 `
    --reload
``` -->

### Docker

```
docker build -t rest-backend .
docker run --name rest-backend -p 8000:8000 -d rest-backend
```
