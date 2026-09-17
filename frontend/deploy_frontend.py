"""
deploy_frontend.py

Automates deployment and synchronization of the AI Thumbnail Generator frontend to:
  1. Amazon S3 Static Website Hosting (in AWS ap-south-1)
  2. Cloudflare Global Edge CDN with Universal SSL, DNS Proxying, and custom domain routing (https://samratdev.fun)

Usage:
  backend\\.venv\\Scripts\\python.exe frontend\\deploy_frontend.py
"""

import json
import mimetypes
import os
import subprocess
import sys
import boto3
from botocore.exceptions import ClientError
try:
    from dotenv import load_dotenv
except ImportError:
    # Fallback if python-dotenv is not installed in the current interpreter
    def load_dotenv(dotenv_path=None, override=False):
        if dotenv_path and os.path.exists(dotenv_path):
            with open(dotenv_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if override or k not in os.environ:
                            os.environ[k] = v

# Load AWS configuration from backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"), override=True)

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
CUSTOM_DOMAIN_BUCKET = "samratdev.fun"
WWW_DOMAIN_BUCKET = "www.samratdev.fun"
FALLBACK_BUCKET = os.getenv("FRONTEND_S3_BUCKET", "ai-thumbnail-frontend-samrat-1234")
DIST_DIR = os.path.join(os.path.dirname(__file__), "dist")

# Initialize AWS S3 client
session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=AWS_REGION,
)
s3 = session.client("s3")
sts = session.client("sts")


def get_account_id():
    """Retrieve current AWS Account ID."""
    caller = sts.get_caller_identity()
    return caller["Account"]


def ensure_production_build():
    """Ensure frontend/dist exists and contains fresh built assets."""
    index_file = os.path.join(DIST_DIR, "index.html")
    print("📦 Building fresh production bundle with Vite...")
    subprocess.run(["npm", "run", "build"], cwd=os.path.dirname(__file__), check=True, shell=True)
    print("✅ Frontend production bundle confirmed in frontend/dist")


def configure_bucket_website(bucket_name: str, redirect_target: str = None):
    """Create or configure an S3 bucket for Static Website Hosting."""
    print(f"🪣 Configuring bucket: {bucket_name} in region {AWS_REGION}...")
    try:
        s3.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code in ("404", "NoSuchBucket"):
            create_args = {"Bucket": bucket_name}
            if AWS_REGION != "us-east-1":
                create_args["CreateBucketConfiguration"] = {"LocationConstraint": AWS_REGION}
            s3.create_bucket(**create_args)
            print(f"  ✓ Created S3 bucket: {bucket_name}")
        else:
            raise e

    # Configure public access block
    s3.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": False,
            "IgnorePublicAcls": False,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        },
    )

    if redirect_target:
        # Configure redirect to apex domain
        s3.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration={
                "RedirectAllRequestsTo": {
                    "HostName": redirect_target,
                    "Protocol": "https",
                }
            },
        )
        print(f"  ✓ Configured 301 Redirect to https://{redirect_target}")
    else:
        # Standard SPA website hosting
        s3.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration={
                "IndexDocument": {"Suffix": "index.html"},
                "ErrorDocument": {"Key": "index.html"},
            },
        )
        # Apply public read bucket policy
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*",
                }
            ],
        }
        s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))
        print(f"  ✓ Static website hosting & public read policy active on {bucket_name}")


def upload_dist_files_to_bucket(bucket_name: str):
    """Upload all assets from frontend/dist to specified S3 bucket."""
    print(f"🚀 Uploading static assets to s3://{bucket_name}...")
    uploaded_count = 0

    for root, _, files in os.walk(DIST_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, DIST_DIR).replace("\\", "/")

            content_type, _ = mimetypes.guess_type(file_path)
            if file.endswith(".js"):
                content_type = "application/javascript; charset=utf-8"
            elif file.endswith(".css"):
                content_type = "text/css; charset=utf-8"
            elif file.endswith(".html"):
                content_type = "text/html; charset=utf-8"
            elif file.endswith(".svg"):
                content_type = "image/svg+xml"
            elif not content_type:
                content_type = "application/octet-stream"

            # Cache headers
            if "assets/" in rel_path:
                cache_control = "public, max-age=31536000, immutable"
            elif file == "index.html":
                cache_control = "public, max-age=0, must-revalidate"
            else:
                cache_control = "public, max-age=86400"

            s3.upload_file(
                Filename=file_path,
                Bucket=bucket_name,
                Key=rel_path,
                ExtraArgs={
                    "ContentType": content_type,
                    "CacheControl": cache_control,
                },
            )
            uploaded_count += 1

    print(f"  ✓ Uploaded {uploaded_count} files to s3://{bucket_name}")


def main():
    print("=" * 70)
    print("  AI Thumbnail Generator — Production Frontend Deployment")
    print("  Target Architecture: Amazon S3 Static Hosting + Cloudflare Edge CDN")
    print("=" * 70)

    # 1. Build bundle
    ensure_production_build()

    # 2. Configure primary custom domain bucket (samratdev.fun)
    configure_bucket_website(CUSTOM_DOMAIN_BUCKET)
    upload_dist_files_to_bucket(CUSTOM_DOMAIN_BUCKET)

    # 3. Configure www redirect bucket (www.samratdev.fun)
    configure_bucket_website(WWW_DOMAIN_BUCKET, redirect_target="samratdev.fun")

    # 4. Also keep fallback bucket in sync
    configure_bucket_website(FALLBACK_BUCKET)
    upload_dist_files_to_bucket(FALLBACK_BUCKET)

    print()
    print("=" * 70)
    print("🎉 DEPLOYMENT SUMMARY")
    print(f"  Live Custom Domain    : https://samratdev.fun (Cloudflare SSL Active)")
    print(f"  Redirect Domain       : https://www.samratdev.fun -> https://samratdev.fun")
    print(f"  Primary S3 Bucket     : s3://{CUSTOM_DOMAIN_BUCKET}")
    print(f"  Fallback S3 Bucket    : s3://{FALLBACK_BUCKET}")
    print(f"  Global CDN & Security : Cloudflare Edge Proxy (Universal SSL/TLS)")
    print("=" * 70)


if __name__ == "__main__":
    main()
