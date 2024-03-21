FROM public.ecr.aws/lambda/python:3.12

COPY . ${LAMBDA_TASK_ROOT}

RUN pip3 install \
        --target ${LAMBDA_TASK_ROOT} \
        -r ${LAMBDA_TASK_ROOT}/requirements.txt

ENV PYTHONPATH=${LAMBDA_TASK_ROOT}:${PYTHONPATH}

CMD [ "main.lambda_handler" ]