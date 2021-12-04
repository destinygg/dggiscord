FROM python:3.8-alpine

RUN apk add gcc python3-dev musl-dev

WORKDIR /dggiscord

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./dggiscord/app.py" ]
