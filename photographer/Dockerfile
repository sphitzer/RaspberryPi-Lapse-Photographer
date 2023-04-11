FROM python:3.10.6


WORKDIR /code

VOLUME /output

#ghpoto2 setup steps
#RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y python-setuptools
#RUN pip install -v gphoto2 --no-binary :all:

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./src /code/src

# rework this to make output random if no name provided??
CMD ["python", "./src/main.py"]
#CMD ["python", "./src/main.py", "--name", "squid3", "--outputpath", "/output", "--frames", "5000", "--interval", "12", "--kafka-bootstrap-servers", "broker:9092"]
#CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8030"]

