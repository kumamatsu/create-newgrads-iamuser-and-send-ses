import boto3
import botocore
import json
import io
import csv
import random
import string
import datetime

error_mail_template = './mail_template/error_mail_template.txt'
mail_template = './mail_template/user_mail_template.txt'

REGION="ap-northeast-1"
sns = boto3.client('sns',region_name=REGION)
iam = boto3.client('iam')
s3 = boto3.client('s3',region_name=REGION)
ses = boto3.client('ses',region_name=REGION)
ssm = boto3.client('ssm',region_name=REGION)

ERROR_SNS_TOPIC="OPE_SNS_TOPIC"

SUBJECT="Your IAM User has been registered."


def get_random_password():
    
    """
    処理内容：パスワード作成
    
    Returns
    --------
    shuffled_password : string
    パスワード
    
    """    
    random_source = string.ascii_letters + string.digits
    password = random.choice(random_source)
    
    for i in range(3):
        password += random.choice('!@#$%&*_+-=|')
        password += random.choice(string.ascii_lowercase)
        password += random.choice(string.ascii_uppercase)
        password += random.choice(string.digits)
    
    shuffled_password = ''.join(
        random.sample(password, len(password)))
    
    return shuffled_password


def get_account_id():
    """
    処理内容：AWSアカウントIDの取得
    
    Returns
    --------
    AccountIDの情報: str
        ex)123456789012
    
    """   
    res = boto3.client('sts').get_caller_identity()
    
    account_id = res['Account']
    return account_id


def delete_object(SRC_BUCKET_NAME,SRC_OBJECT_KEY_NAME):
    """
    処理内容：S3からCSVを削除
    Parameters
    ----------
    S3のバケット名 : str
    S3のオブジェクト名 : str
    
    """   
    
    try:
        s3.delete_object(
          Bucket=SRC_BUCKET_NAME, 
          Key=SRC_OBJECT_KEY_NAME
          )
    except Exception as e:
        send_error_sns(str(e))
        raise e
  

def get_ssm_param(param):
    """
    処理内容：SSMパラメータの取得
    
    Parameters
    ----------
    パラメータのKey : str
    
    Returns
    --------
    SSM ParameterのValue: str
    
    """
    try:
    
        response = ssm.get_parameter(
            Name=param,
            WithDecryption=True
            )
      
    except Exception as e:
        send_error_sns(str(e))
        raise e
    
    return response['Parameter']['Value']


def get_csv(SRC_BUCKET_NAME,SRC_OBJECT_KEY_NAME):
    """
    処理内容：S3に配置したCSVからIAM作成対象を読み込む
    
    Returns
    --------
    S3の情報 : list
    IAM作成対象のlist
    ex)['test.user,testgroup', 'test.user2,testgroup2',…]
    
    """    
    
    try:
    
        src_obj = s3.get_object(
            Bucket = SRC_BUCKET_NAME,
            Key = SRC_OBJECT_KEY_NAME,
            )
    
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "NoSuchKey":
            print(f"{SRC_OBJECT_KEY_NAME} does not exist")
            send_error_sns(str(e))
    
    except Exception as e:
        send_error_sns(str(e))
        raise e
    
    csv_list = src_obj['Body'].read().decode("utf-8").split()
    
    return csv_list


def create_iamuser(csv_list):
    """
    処理内容：IAMユーザーを作成する
    
    Parameters
    ----------
    S3の情報 : list
    IAM作成対象のlist
    ex)['test.user,testgroup,test@example.com', 'test.user2,testgroup2,test2@example.com',…]
    
    """
    
    try:
    
        for row in csv_list:
            user_info = row.split(',')
            temp_password = get_random_password()
            
            iam.create_user(
                UserName=user_info[0]
                )
            
            waiter_config = {
                'Delay': 3,
                'MaxAttempts': 5
            }
            
            waiter = iam.get_waiter('user_exists')
            
            waiter.wait(
                UserName=user_info[0],
                WaiterConfig=waiter_config
                )
            
            iam.create_login_profile(
                UserName=user_info[0],
                Password=temp_password,
                PasswordResetRequired=True
                )
            
            iam.add_user_to_group(
                GroupName=user_info[1],
                UserName=user_info[0]
                )
            
            send_ses(user_info,temp_password)
      
    except Exception as e:
        send_error_sns(str(e))
        raise e
  
  
def set_mail_content(user_info,temp_password):
    """
    SESメールで送信する内容を修正
    
    Parameters
    ----------
    error : str
      error message when error occurs
    lambda_name : str
    
    """
    
    with open(mail_template) as f:
        ses_body = f.read()
      
    ses_body = ses_body.replace('var_username', user_info[0])
    ses_body = ses_body.replace('var_password', temp_password)
    
    return ses_body


def send_ses(user_info,temp_password):
    """
    ユーザーにパスワードを送信するメール
    
    Parameters
    ----------
    S3の情報 : list
        IAM作成対象のlist
        ex)['test.user,testgroup,test@example.com']
    
    初回パスワード：str
    
    """
    
    ses_body = set_mail_content(user_info,temp_password)
    
    try:
    
        SOURCE_MAIL = get_ssm_param('SRC_SNS_MAIL')
        
        response = ses.send_email(
          Destination={
              'ToAddresses': [
                  user_info[2],
              ],
          },
          Message={
              'Body': {
                  'Text': {
                      'Charset': 'UTF-8',
                      'Data': ses_body,
                  },
              },
              'Subject': {
                  'Charset': 'UTF-8',
                  'Data': SUBJECT,
              },
          },
          Source=SOURCE_MAIL
        )
    
    except Exception as e:
        send_error_sns(str(e))
        raise e
    

def send_error_sns(error):
    """
    Lambdaが異常終了した際にSNSメールを送信
    
    Parameters
    ----------
    error : string
      error message when error occurs
    
    """
    now = datetime.datetime.now() + datetime.timedelta(hours=9)
    now = now.strftime('%Y/%m/%d %H:%M:%S')
    
    with open(error_mail_template) as f:
        data_lines = f.read()

    data_lines = data_lines.replace('ver_error_date', now)
    data_lines = data_lines.replace('ver_error', error)
    
    #メール文の整形
    error_sns_body = {}
    error_sns_body["default"] = data_lines + "\n"

    #送信先SNSトピックの指定
    ACCOUNT_ID = get_account_id()
    topic = 'arn:aws:sns:ap-northeast-1:'+ ACCOUNT_ID + ':' + ERROR_SNS_TOPIC
    #メール件名の指定
    subject = '[Lambda Error] [新卒研修アカウント]IAMユーザー作成Lambda' 

    #SNSへのパブリッシュ
    try:
        response = sns.publish(
            TopicArn = topic,
            Message = json.dumps(error_sns_body, ensure_ascii=False),
            Subject = subject,
            MessageStructure='json'
      )
    except Exception as e:
        print(str(e))
        raise e


def lambda_handler(event, context):
  
    SRC_BUCKET_NAME = get_ssm_param('SRC_BUCKET_NAME')
    SRC_OBJECT_KEY_NAME = get_ssm_param('SRC_OBJECT_KEY_NAME')
    
    csv_list = get_csv(SRC_BUCKET_NAME,SRC_OBJECT_KEY_NAME)
    create_iamuser(csv_list)
    delete_object(SRC_BUCKET_NAME,SRC_OBJECT_KEY_NAME)
