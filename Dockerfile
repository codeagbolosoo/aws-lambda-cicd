# Python Lambda Dockerfile
# Author: Abraham Agbolosoo
#
# Build: docker build -t my-python-lambda .
# Test:  docker run -p 9000:8080 my-python-lambda
#        curl -X POST http://localhost:9000/2015-03-31/functions/function/invocations -d '{"ping": true}'

FROM public.ecr.aws/lambda/python:3.12

# System dependencies (uncomment if needed)
# RUN dnf install -y gcc libpq-devel && dnf clean all

# Python dependencies - copy first for layer caching
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Application source
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# Lambda handler entrypoint
CMD ["src.handler.lambda_handler"]
