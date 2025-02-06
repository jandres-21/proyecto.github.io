FROM python:3.11-slim-buster

WORKDIR /python-docker

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "/python-docker/my-app/run.py"]

