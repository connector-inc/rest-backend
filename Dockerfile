# Use an official Python runtime as a parent image
FROM python:3.11-slim

RUN adduser --disabled-password --gecos '' localuser
USER localuser

WORKDIR /home/localuser/app

COPY --chown=localuser:localuser . /home/localuser/app/

SHELL ["/bin/bash", "-c"]

RUN python -m venv .venv
RUN source ./.venv/bin/activate
RUN python -m pip install --user .

EXPOSE $PORT

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 2"]

