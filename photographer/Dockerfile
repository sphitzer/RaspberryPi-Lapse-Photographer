FROM python:3.9

WORKDIR /code

VOLUME /output

#ghpoto2 setup steps
#RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y python-setuptools
#RUN pip install -v gphoto2 --no-binary :all:

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./src /code/src

#interval 3 caused problems... too fast for camera when saving both raw and jpeg??
CMD ["python", "./src/main.py", "--name", "squid2", "--outputpath", "/output", "--frames", "50", "--interval", "10"]
#CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]