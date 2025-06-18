import os
from openai import AzureOpenAI

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

endpoint = os.environ["AZURE_OPENAI__ENDPOINT"]
api_key = os.environ["AZURE_OPENAI__API_KEY"]
deployment = os.environ["AZURE_OPENAI__EMBEDDING_MODEL"]
api_version = os.environ["AZURE_OPENAI__API_VERSION"]

client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=api_key,
    api_version=api_version,
)

print("Testing embedding call with:")
print("  endpoint:", endpoint)
print("  deployment:", deployment)
print("  api_version:", api_version)

try:
    response = client.embeddings.create(
        model=deployment,
        input=["hello world"],
    )
    print("Embedding call succeeded! Response:", response)
except Exception as e:
    print("Embedding call failed:", e)