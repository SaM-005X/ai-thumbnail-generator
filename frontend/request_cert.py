import os
import sys
import time
import boto3
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"), override=True)

session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name="us-east-1",
)

acm = session.client("acm")
domain = "samratdev.fun"

cert_arn = None
for c in acm.list_certificates().get("CertificateSummaryList", []):
    if c.get("DomainName") == domain:
        cert_arn = c["CertificateArn"]
        print(f"Found existing certificate: {cert_arn}")
        break

if not cert_arn:
    print(f"Requesting new SSL certificate for {domain} and *.{domain}...")
    res = acm.request_certificate(
        DomainName=domain,
        ValidationMethod="DNS",
        SubjectAlternativeNames=[f"*.{domain}"],
        Options={"CertificateTransparencyLoggingPreference": "ENABLED"},
    )
    cert_arn = res["CertificateArn"]
    print(f"✅ Requested certificate: {cert_arn}")

# Poll briefly for DNS validation records
print("Fetching DNS validation records...")
for _ in range(5):
    time.sleep(3)
    cert_details = acm.describe_certificate(CertificateArn=cert_arn)["Certificate"]
    dvo = cert_details.get("DomainValidationOptions", [])
    if dvo and dvo[0].get("ResourceRecord"):
        break

print(f"Status: {cert_details.get('Status')}")
print(f"Certificate ARN: {cert_arn}")
print()
seen_records = set()
for d in dvo:
    record = d.get("ResourceRecord")
    if record:
        key = (record.get("Name"), record.get("Value"))
        if key not in seen_records:
            seen_records.add(key)
            print(f"Domain Name : {d.get('DomainName')}")
            print(f"Record Type : {record.get('Type')}")
            print(f"Record Name : {record.get('Name')}")
            print(f"Record Value: {record.get('Value')}")
            print("-" * 50)
