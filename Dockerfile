FROM python:3.10-slim-bullseye

RUN apt-get update && apt-get install -y git

WORKDIR /app

RUN pip install --upgrade setuptools wheel
RUN pip install --no-build-isolation git+https://github.com/aeyalcinoglu/brownie.git@master
RUN pip install git+https://github.com/aeyalcinoglu/dank_mids.git

COPY . .

CMD ["python3", "src/run.py"]