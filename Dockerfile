# Use an official Python runtime as a parent image
FROM python:3.11

RUN adduser --disabled-password --gecos '' localuser
USER localuser

WORKDIR /home/localuser/app

COPY --chown=localuser:localuser . /home/localuser/app/

# RUN mkdir certificates
# RUN openssl genrsa -out certificates/key.pem 2048
# RUN openssl req -new -key certificates/key.pem -out certificates/csr.pem -subj "/C=VN/ST=Ho Chi Minh City/L=Ho Chi Minh City/O=Connector Inc./CN=www.connector.rocks/emailAddress=powoftech@gmail.com"
# RUN openssl x509 -req -days 365 -in certificates/csr.pem -signkey certificates/key.pem -out certificates/cert.pem 

SHELL ["/bin/bash", "-c"]

RUN python -m venv .venv
RUN source ./.venv/bin/activate
RUN python -m pip install --user .

EXPOSE $PORT

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 2"]

