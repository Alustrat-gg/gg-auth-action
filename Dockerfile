FROM python:3.12-slim

ENV PIP_NO_CACHE_DIR 1
ENV PIP_ROOT_USER_ACTION ignore

ENV PATH "/root/.local/bin:${PATH}"
ENV PYTHONPATH "/root/.local/lib/python3.12/site-packages"

COPY requirements.txt .

RUN pip install --user --upgrade --no-cache-dir -r requirements.txt

WORKDIR /app
COPY oidc-exchange.py .
COPY fetch-credential.sh .

RUN chmod +x fetch-credential.sh
ENTRYPOINT ["/app/fetch-credential.sh"]