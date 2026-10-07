FROM python:3.14-alpine

RUN apk add gcc python3-dev musl-dev

WORKDIR /dggiscord

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ARG VERSION=dev
ENV DGGISCORD_VERSION=$VERSION

ENTRYPOINT [ "python", "./dggiscord/app.py" ]
