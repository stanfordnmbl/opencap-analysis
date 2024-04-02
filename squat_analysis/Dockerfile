FROM stanfordnmbl/opensim-python:4.3

ARG FUNCTION_DIR="/function"

RUN apt-get update && \
    apt-get install -y \
    build-essential \
    python3-dev \
    g++ \
    make \
    cmake \
    unzip \
    libcurl4-openssl-dev

# Copy function code
RUN mkdir -p ${FUNCTION_DIR}
COPY ./requirements.txt /requirements.txt
# Install the requirements.txt
RUN python3.8 -m pip install --no-cache-dir -r  /requirements.txt
RUN python3.8 -m pip install --target ${FUNCTION_DIR} awslambdaric

ADD https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie /usr/bin/aws-lambda-rie
RUN chmod +x /usr/bin/aws-lambda-rie

COPY ./function ${FUNCTION_DIR}
RUN chmod +x ${FUNCTION_DIR}/entrypoint
WORKDIR ${FUNCTION_DIR}

ENTRYPOINT ["./entrypoint"]
CMD ["handler.handler"]
