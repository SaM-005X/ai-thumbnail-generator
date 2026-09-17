"""
deploy_lambda.py

Automates deployment of the AI Thumbnail Generator backend to:
  1. AWS Lambda (Python 3.12, 512MB RAM, 60s timeout, Mangum handler)
  2. Amazon API Gateway HTTP API ($default proxy route + CORS)

Requires AWS credentials with Lambda and API Gateway permissions.
"""

import json
import os
import sys
import time
import boto3
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "ai-thumbnails-samrat-1234")
LAMBDA_FUNCTION_NAME = "ai-thumbnail-backend"
API_NAME = "ai-thumbnail-api"
ROLE_NAME = "ai-thumbnail-lambda-role"
ZIP_PATH = os.path.join(os.path.dirname(__file__), "lambda_package.zip")

session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=AWS_REGION,
)

iam_client = session.client("iam")
lambda_client = session.client("lambda")
apigw_client = session.client("apigatewayv2")


def get_or_create_execution_role():
    """Ensure the IAM Execution Role exists with Lambda basic + S3 access."""
    print(f"🔑 Checking IAM role: {ROLE_NAME}...")
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    try:
        role = iam_client.get_role(RoleName=ROLE_NAME)
        role_arn = role["Role"]["Arn"]
        print(f"✅ Found existing role: {role_arn}")
        return role_arn
    except iam_client.exceptions.NoSuchEntityException:
        print(f"Creating new IAM role {ROLE_NAME}...")
        role = iam_client.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Description="Execution role for AI Thumbnail Generator Lambda",
        )
        role_arn = role["Role"]["Arn"]

        # Attach basic execution policy for CloudWatch logs
        iam_client.attach_role_policy(
            RoleName=ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )
        # Attach S3 Full Access (or scoped policy for the thumbnail bucket)
        iam_client.attach_role_policy(
            RoleName=ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess",
        )
        print(f"✅ Created role: {role_arn}")
        print("⏳ Waiting 10s for IAM role replication...")
        time.sleep(10)
        return role_arn


def deploy_lambda(role_arn: str):
    """Create or update the AWS Lambda function."""
    print(f"🚀 Deploying Lambda function: {LAMBDA_FUNCTION_NAME}...")

    if not os.path.exists(ZIP_PATH):
        print(f"❌ Error: {ZIP_PATH} not found. Run package_lambda.py first.")
        sys.exit(1)

    with open(ZIP_PATH, "rb") as f:
        zip_bytes = f.read()

    env_vars = {
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
        "SUPABASE_URL": os.getenv("SUPABASE_URL", ""),
        "SUPABASE_KEY": os.getenv("SUPABASE_KEY", ""),
        "SUPABASE_SERVICE_KEY": os.getenv("SUPABASE_SERVICE_KEY", ""),
        "S3_BUCKET_NAME": BUCKET_NAME,
        "ENVIRONMENT": "production",
    }


    try:
        lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        print("Updating existing Lambda code...")
        lambda_client.update_function_code(
            FunctionName=LAMBDA_FUNCTION_NAME,
            ZipFile=zip_bytes,
        )
        print("Waiting for Lambda code update to settle...")
        for _ in range(15):
            time.sleep(2)
            cfg = lambda_client.get_function_configuration(FunctionName=LAMBDA_FUNCTION_NAME)
            if cfg.get("LastUpdateStatus") != "InProgress":
                break
        print("Updating Lambda configuration...")
        lambda_client.update_function_configuration(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Role=role_arn,
            Handler="app.main.handler",
            Runtime="python3.12",
            Timeout=60,
            MemorySize=512,
            Environment={"Variables": env_vars},
        )
        print(f"✅ Lambda function updated.")
    except lambda_client.exceptions.ResourceNotFoundException:
        print("Creating new Lambda function...")
        lambda_client.create_function(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Runtime="python3.12",
            Role=role_arn,
            Handler="app.main.handler",
            Code={"ZipFile": zip_bytes},
            Description="AI Thumbnail Generator Backend (FastAPI + Mangum)",
            Timeout=60,
            MemorySize=512,
            Environment={"Variables": env_vars},
        )
        print(f"✅ Lambda function created.")

    func_info = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
    return func_info["Configuration"]["FunctionArn"]


def setup_api_gateway(lambda_arn: str):
    """Create or update Amazon API Gateway HTTP API with Lambda proxy integration."""
    print(f"🌐 Configuring API Gateway HTTP API: {API_NAME}...")

    # Find existing API if any
    apis = apigw_client.get_apis().get("Items", [])
    api_id = None
    for api in apis:
        if api.get("Name") == API_NAME:
            api_id = api["ApiId"]
            print(f"Found existing API Gateway: {api_id}")
            break

    cors_config = {
        "AllowHeaders": ["*"],
        "AllowMethods": ["GET", "POST", "DELETE", "OPTIONS", "HEAD"],
        "AllowOrigins": ["*"],
        "MaxAge": 86400,
    }

    if not api_id:
        create_res = apigw_client.create_api(
            Name=API_NAME,
            ProtocolType="HTTP",
            CorsConfiguration=cors_config,
            Description="HTTP API router for AI Thumbnail Generator",
        )
        api_id = create_res["ApiId"]
        print(f"✅ Created API Gateway HTTP API: {api_id}")

    # Create or get integration
    integrations = apigw_client.get_integrations(ApiId=api_id).get("Items", [])
    integration_id = None
    if integrations:
        integration_id = integrations[0]["IntegrationId"]
    else:
        int_res = apigw_client.create_integration(
            ApiId=api_id,
            IntegrationType="AWS_PROXY",
            IntegrationUri=lambda_arn,
            PayloadFormatVersion="2.0",
        )
        integration_id = int_res["IntegrationId"]

    # Ensure $default route routes to integration
    routes = apigw_client.get_routes(ApiId=api_id).get("Items", [])
    has_default = any(r.get("RouteKey") == "$default" for r in routes)
    if not has_default:
        apigw_client.create_route(
            ApiId=api_id,
            RouteKey="$default",
            Target=f"integrations/{integration_id}",
        )
        print("✅ Configured $default proxy route.")

    # Ensure $default stage exists with auto-deploy
    stages = apigw_client.get_stages(ApiId=api_id).get("Items", [])
    has_default_stage = any(s.get("StageName") == "$default" for s in stages)
    if not has_default_stage:
        apigw_client.create_stage(
            ApiId=api_id,
            StageName="$default",
            AutoDeploy=True,
        )
        print("✅ Configured $default auto-deploy stage.")

    # Grant API Gateway permission to invoke Lambda
    statement_id = f"apigateway-invoke-{api_id}"
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_FUNCTION_NAME,
            StatementId=statement_id,
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com",
            SourceArn=f"arn:aws:execute-api:{AWS_REGION}:{lambda_arn.split(':')[4]}:{api_id}/*/*",
        )
        print("✅ Granted API Gateway permission to invoke Lambda.")
    except lambda_client.exceptions.ResourceConflictException:
        pass

    api_endpoint = f"https://{api_id}.execute-api.{AWS_REGION}.amazonaws.com"
    print("\n" + "=" * 60)
    print(f"🎉 Live Serverless API Endpoint: {api_endpoint}")
    print(f"   Interactive Docs: {api_endpoint}/docs")
    print(f"   Health Check:     {api_endpoint}/")
    print("=" * 60 + "\n")
    return api_endpoint


if __name__ == "__main__":
    try:
        role_arn = get_or_create_execution_role()
        lambda_arn = deploy_lambda(role_arn)
        setup_api_gateway(lambda_arn)
    except Exception as err:
        print(f"\n❌ Deployment error: {err}")
        sys.exit(1)
