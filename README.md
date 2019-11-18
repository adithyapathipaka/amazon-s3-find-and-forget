Amazon S3 Find and Forget
=========================

> Warning: This project is currently being developed and the code shouldn't be used in production.

Amazon S3 Find and Forget is a solution for helping customers to find and delete user data in Amazon S3.
It is designed to help customers to fulfil their GDPR’s Right To Be Forgotten obligations when operating in a large Data Lake in a performant, reliable, secure and cost-effective way.

- [Deployment](#deploy)
- [Monitoring the Solution](docs/MONITORING.md)
- [Automated Tests](docs/TESTING.md)

## Getting Started

### Deploy

1. Setup a virtual environment

```bash
virtualenv venv
source venv/bin/activate
```

2. Install the layers
```bash
pip install -r backend/lambda_layers/aws_sdk/requirements.txt -t backend/lambda_layers/aws_sdk/python
pip install -r backend/lambda_layers/decorators/requirements.txt -t backend/lambda_layers/decorators/python
```

3. Deploy using the CLI
```bash
aws cloudformation package --template-file templates/template.yaml --s3-bucket your-temp-bucket --output-template-file packaged.yaml
aws cloudformation deploy --template-file ./packaged.yaml --stack-name S3F2 --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND
```
