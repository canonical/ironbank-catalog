FROM ubuntu:oracular
ENV VENV_PATH=/venv


# install node requirements and setup python virtual environment
RUN apt update && apt install -y git python3 python3.12-venv python3-pip tree
COPY requirements.txt requirements.txt
RUN python3 -m venv $VENV_PATH && $VENV_PATH/bin/pip install -r requirements.txt


# always activate the virtual environment
ENV PATH="$VENV_PATH/"bin":$PATH"
