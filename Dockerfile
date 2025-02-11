# Use an official Python runtime as a parent image
FROM python:3.11

WORKDIR /app

COPY . /app/

# RUN mkdir certificates
# RUN openssl genrsa -out certificates/key.pem 2048
# RUN openssl req -new -key certificates/key.pem -out certificates/csr.pem -subj "/C=VN/ST=Ho Chi Minh City/L=Ho Chi Minh City/O=Connector Inc./CN=www.connector.rocks/emailAddress=powoftech@gmail.com"
# RUN openssl x509 -req -days 365 -in certificates/csr.pem -signkey certificates/key.pem -out certificates/cert.pem 

SHELL ["/bin/bash", "-c"]

RUN python -m venv .venv
RUN source ./.venv/bin/activate
RUN pip install -r requirements.txt

EXPOSE $PORT

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

