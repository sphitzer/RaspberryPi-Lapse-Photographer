FROM python:3.10.6

RUN apt-get -y update
RUN apt-get install -y ffmpeg

WORKDIR /code

#VOLUME /output

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./src /code/src
COPY ./.env /code/.env

#need to switch to fastapi for timelapse orchestration...
CMD ["python", "./src/main.py", "--name", "squid3",  "--timelapsedir", "/output", "--s3bucket", "timelapseuploadsfortwentyfivecents2", "--kafka-bootstrap-servers", "broker:9092"]

#CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]

