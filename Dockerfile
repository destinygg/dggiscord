FROM python:3.7-alpine

WORKDIR /dggiscord

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./dggiscord/app.py" ]
