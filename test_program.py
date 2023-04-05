from lambda_function import get_random_password
from lambda_function import get_csv
from lambda_function import create_iamuser
from lambda_function import get_account_id
from lambda_function import get_ssm_param

import string
import re
import boto3

# pytest test_program.py::test_get_random_password_lowercase
def test_get_random_password_lowercase():
    password = get_random_password()

    assert bool(re.search(r'[a-z]', password))
    

# pytest test_program.py::test_get_random_password_uppercase
def test_get_random_password_uppercase():
    password = get_random_password()

    assert bool(re.search(r'[A-Z]', password))
    
# pytest test_program.py::test_get_random_password_digits
def test_get_random_password_digits():
    password = get_random_password()

    assert bool(re.search(r'[0-9]', password))
    
    
# pytest test_program.py::test_get_random_password_symbol
def test_get_random_password_symbol():
    password = get_random_password()
    count = 0
    for symbol in '!@#$%&*_+-=|':
        if symbol in password:
            count += 1

    assert count == 3
    
    
# pytest test_program.py::test_get_random_password_forbiddensymbol
def test_get_random_password_forbiddensymbol():
    password = get_random_password()
    count = 0
    for symbol in '"\\':
        if symbol in password:
            count += 1

    assert count != 1
    
    
# def test_create_iamuser():
    
#     iam = boto3.client('iam')
    
#     create_iamuser(
#         ['test.user,developers,ope@example.com', 'test.user2,developers,ope@example.com']
#         )
#     response = iam.list_users()
#     print(response['Users'])
#     # for user in response['Users']:
#     #     if user['test.user']

#     assert res == 3

#pytest test_program.py::test_get_account_id
def test_get_account_id():
    account_id = get_account_id()
    
    assert account_id == "XXXXXXXXXXXX"
    assert account_id != "123456789012"


#pytest test_program.py::test_get_ssm_para
def test_get_ssm_param():
    SOURCE_MAIL = get_ssm_param('SRC_MAIL')
    SRC_BUCKET_NAME = get_ssm_param('SRC_BUCKET_NAME')
    SRC_OBJECT_KEY_NAME = get_ssm_param('SRC_OBJECT_KEY_NAME')
    
    assert SOURCE_MAIL == "ope@example.com"
    assert SRC_BUCKET_NAME == "s3-btc-xxxxxxxxxxxxxx"
    assert SRC_OBJECT_KEY_NAME == "xxxxxxxxx.csv"