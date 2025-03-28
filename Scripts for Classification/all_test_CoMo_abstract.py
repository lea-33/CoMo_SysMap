import os

import numpy as np
from openai import OpenAI
import json
from pymongo import MongoClient
from bson import ObjectId
import time

my_api_key = "your-api-key"
token_limit = 131000  # Token limit for the prompt

sleep_time_points = np.arange(100, 8000, 100)

def approximate_token_count(text):
    # Approximate token count based on average character length per token
    return len(text) // 4

# OpenAI client
openai_client = OpenAI(base_url="https://llm.scads.ai/v1", api_key=my_api_key)

# Find model with "llama" in name
for model in openai_client.models.list().data:
    model_name = model.id
    if "llama" in model_name:
        break

# Path to the certificate
tls_certificate_path = r"path-to-certificate\zert.pem"

# MongoDB connection string
CONNECTION_STRING = (
    "mongodb+srv://hci.9iakh.mongodb.net/"
    "?authSource=%24external&authMechanism=MONGODB-X509"
    f"&tls=true&tlsCertificateKeyFile={tls_certificate_path}"
)

mongo_client = MongoClient(CONNECTION_STRING)
db = mongo_client["HCI"]  # Replace with your database name
collection = db["ACM_paper_filter3"]  # Replace with your collection name

# Query all entries from the database
entries = list(collection.find())    #crashed after the first 5299 entries

# Reduce the dataset by filtering only relevant entries
filtered_data = [
    {key: str(entry.get(key, None)) if key == '_id' else entry.get(key, None) for key in ['_id', 'abstract']}
    for entry in entries
]

# Parameters
max_attempts = 2  # Maximum number of retries for a single entry
hci_keys = ['yes', 'no']
invalid_results = 0
como_results = 0
no_como_results = 0

# Loop through each entry in the data
for i, entry in enumerate(filtered_data):
    # Serialize the entry and taxonomy JSON
    entry_json = json.dumps(entry, indent=2, ensure_ascii=False)

    # Construct the prompt
    prompt = f"""
            You are an expert in analyzing research papers and determining their relevance to the field of Human-Computer Interaction (HCI). 
            Your task is to decide whether the given research paper is important in terms of developing computational models.
            We later want to classify paper into different Modelling Approaches, therefore we need to know if they use such techniques at all.

            Inclusion criteria:
            - It develops or utilizes a computational model. A computational model is a well-defined system that transforms inputs into outputs and can be theory-driven, data-driven, or a hybrid of both.
            - It investigates human-computer interaction (HCI) using computational methods. 
            - It is important, that the paper really makes use of those models and implements them in the research.
            Exclusion criteria (if any apply, classify as 'no'):
            - The paper only mentions computational methods without actively developing, evaluating, validating, or utilizing a computational model.
            - The study focuses purely on descriptive statistics or qualitative analysis without computational modeling.
            - It does not analyze the topic using computational approaches.
            
            {entry_json}

            Your task:
            1. Read the Abstract provided in the research paper JSON.
            2. Based on the content, classify whether the research paper utilizes computational models.
            3. Output ONLY "yes or "no" (no explanations, no additional words, no code).

            Example of correct outputs:
            - yes
            - no

            Now, analyze the given research paper and classify it:
            """

    # Check if the token count exceeds the limit
    token_count = approximate_token_count(prompt)
    if token_count > token_limit:
        print(f"Entry {i} exceeds token limit ({token_count} tokens). Marking as 'invalid entry'.")
        result = 'invalid entry'
    else:
        # Retry mechanism for generating the response
        attempts = 0
        while attempts < max_attempts:
            try:
                # Send the prompt to the model
                response = openai_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=model_name
                )

                # Extract the response content
                result = response.choices[0].message.content.strip()

                # Check if the response matches one of the valid keys
                if result in hci_keys:
                    print(f"Valid result for entry {i}, after attempt {attempts + 1}: {result}")
                    if result == 'computational modelling':
                        como_results += 1
                    else:
                        no_como_results += 1
                    break  # Valid response, exit the retry loop
                else:
                    print(f'Result invalid: {result}')
                    attempts += 1

            except Exception as e:
                print(f"Error during OpenAI request for entry {i}: {e}")
                attempts += 1

        # If max attempts are reached, log the final result even if invalid
        if attempts == max_attempts:
            invalid_results += 1
            result = 'invalid entry'

        if i in sleep_time_points:
            time.sleep(5)

    # Ensure _id is treated as ObjectId
    entry_id = ObjectId(entry['_id'])  # MongoDB _id of the current entry

    # Write the result back to the database
    collection.update_one(
        {"_id": entry_id},
        {"$set": {"CoMo-12_03": result}},
        upsert=True  # Create the field if it doesn't exist
    )

print(f'Invalid Results: {invalid_results}')
print(f'Related Results: {como_results}')
print(f'Unrelated Results: {no_como_results}')


