FROM python:alpine

RUN addgroup -g 1001 app \
    && adduser -u 1001 -S -D -G app -s /usr/sbin/nologin app

RUN apk update && apk upgrade && \
    apk add --no-cache tzdata

COPY . /app/
WORKDIR /app/
RUN pip install -r requirements.txt

USER app

EXPOSE 5000
ENTRYPOINT ["python"]
CMD ["server.py"]
HEALTHCHECK --interval=30m CMD wget -qO - 127.0.0.1:5000
