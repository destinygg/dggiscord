FROM python:3.8-alpine

WORKDIR /dggiscord

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./dggiscord/app.py" ]
