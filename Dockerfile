FROM python:3-alpine

ARG container_name
ENV CONTAINER_NAME=$container_name

WORKDIR /$CONTAINER_NAME

RUN pip install --upgrade pip

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

CMD [ "python", "app.py"]
