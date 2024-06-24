FROM amazon/aws-lambda-python:3.12

COPY ./requirements.txt ./requirements.txt
RUN pip install -r ./requirements.txt

COPY ./pyproject.toml ./pyproject.toml
COPY ./src ./src

RUN pip install .

CMD [ "apartment_check.lambda_function.lambda_handler" ] 
