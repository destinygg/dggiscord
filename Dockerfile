FROM python:3.11-alpine

RUN apk add gcc python3-dev musl-dev

WORKDIR /dggiscord

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT [ "python", "./dggiscord/app.py" ]
