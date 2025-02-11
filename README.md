# Connector API

## Installation

### 1. Generate certificates

- mkcert:

  ```shell
  sudo mkcert -install
  sudo mkcert localhost 127.0.0.1 ::1
  ```

### 2. Running the server

#### PowerShell

```shell
uvicorn app.main:app `
    --env-file ./.env `
    --host 0.0.0.0 `
    --port 8000 `
    --ssl-keyfile ./certificates/key.pem `
    --ssl-certfile ./certificates/cert.pem `
    --workers 4 `
    --reload
```

### Docker

```shell
docker build -t rest-backend .
docker run --name rest-backend -e PORT=10000 -p 10000:10000 -d rest-backend
```
