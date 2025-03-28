from openai import OpenAI
import json
from pymongo import MongoClient
from bson import ObjectId
import time
import numpy as np

my_api_key = "your-api-key"
token_limit = 131000  # Token limit for the prompt

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

# Filter only computational modelling paper
query = {"CoMo-12_03": "yes"}

entries = list(collection.find(query))

# start_time= time.time()

# Reduce the dataset by filtering only relevant entries
filtered_data = [
    {key: str(entry.get(key, None)) if key == '_id' else entry.get(key, None) for key in
     ['_id', 'abstract', 'title', 'fulltext']}
    for entry in entries
]

# Load the JSON file
with open('mapping.json', 'r') as f:
    mapping = json.load(f)

# Extract the 'Taxonomy' section
taxonomy = mapping.get('Taxonomy', None)

# Parameters
max_attempts = 3  # Maximum number of retries for a single entry

# Extract the keys from the taxonomy JSON
taxonomy_keys = set(taxonomy.keys())
invalid_results = 0
sleeping_timestamps = np.arange(30, len(filtered_data), 30)


def approximate_token_count(text):
    # Approximate token count based on average character length per token
    return len(text) // 4


# Loop through each entry in the data
for i, entry in enumerate(filtered_data):
    # Serialize the entry and taxonomy JSON
    entry_json = json.dumps(entry, indent=2, ensure_ascii=False)
    taxonomy_json_str = json.dumps(taxonomy, indent=2, ensure_ascii=False)

    prompt = f"""
                You are a highly focused expert trained to classify research papers based on their content. 
                Your task is to determine the most appropriate topic from the provided taxonomy for each research paper.

                Here is the research paper entry as JSON:
                {entry_json}

                Here is the taxonomy with topics as keys and their associated keywords as values:
                {taxonomy_json_str}

                Your task:
                1. Read the Abstract and Full Text provided in the research paper JSON.
                2. Compare the content with the keywords in the taxonomy.
                3. Select the ONE best-matching topic from the taxonomy.
                   - The output must be EXACTLY one topic from the taxonomy, with a maximum of 3 words.
                   - Do NOT create new topics or deviate from the taxonomy list.
                   - If more than one topic matches, choose the most relevant one.
                4. Output ONLY the topic name (no explanations, no additional words, no code).

                Examples of correct outputs:
                - User Interface Design
                - Machine Learning
                - Data Security

                Examples of incorrect outputs:
                - User Interface Design in Applications (too long)
                - Novel Topic XYZ (not in taxonomy)
                - This paper belongs to Machine Learning (extra explanation)

                Now, analyze the given research paper and return the most relevant topic:
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

                # Check if the response matches one of the taxonomy keys
                if result in taxonomy_keys:
                    print(f"Valid result for entry {i}, after attempt {attempts + 1}: {result}")
                    break  # Valid response, exit the retry loop
                else:
                    attempts += 1


            except Exception as e:
                print(f"Error during OpenAI request for entry {i}: {e}")
                attempts += 1

        # If max attempts are reached, log the final result even if invalid
        if attempts == max_attempts:
            invalid_results += 1
            result = 'invalid result'

        if i in sleeping_timestamps:
            time.sleep(5)

    # Ensure _id is treated as ObjectId
    entry_id = ObjectId(entry['_id'])  # MongoDB _id of the current entry

    # Write the result back to the database
    collection.update_one(
        {"_id": entry_id},
        {"$set": {"como-tax-topic2": result}},
        upsert=True  # Create the field if it doesn't exist
    )
    print(f"LLM_category updated for entry ID: {entry_id}")
print(f'Invalid Results: {invalid_results}')

type_of_evaluation = mapping.get('Type of Evaluation', None)
type_of_evaluation_keys = set(type_of_evaluation.keys())

invalid_results = 0

time.sleep(5)

# Loop through each entry in the data
for i, entry in enumerate(filtered_data):
    # Serialize the entry and taxonomy JSON
    entry_json = json.dumps(entry, indent=2, ensure_ascii=False)
    type_of_evaluation_json_str = json.dumps(type_of_evaluation, indent=2, ensure_ascii=False)

    # Construct the prompt
    prompt = f"""
                You are a highly focused expert trained to classify research papers based on their content. 
                Your task is to determine the most appropriate Type of Evaluation from the provided Types of Evaluation json for each research paper.

                Here is the research paper entry as JSON:
                {entry_json}

                Here is the Types of Evaluation JSON file:
                {type_of_evaluation_json_str}

                Here are examples for type of evaluation:
                Quantitative Example: Task completion time in eye-tracking study
                Qualitative Example: User interviews on UX perception, Thematic analysis of usability feedback
                Benchmark Example: Performance comparison of text prediction models
                Anecdotal Example: Researcher reflections on prototyping experience

                Your task:
                1. Read the Abstract and Full Text provided in the research paper JSON.
                2. Select the ONE best-matching Type of Evaluation from the json file.
                   - The output must be EXACTLY one Type of Evaluation from the given file, with a maximum of 3 words.
                   - Do NOT create new Types of Evaluation or deviate from the list.
                   - If more than one Type of Evaluation matches, choose the most relevant one.
                4. Output ONLY the Type of Evaluation name (no explanations, no additional words, no code).

                Example of correct outputs:
                - Benchmark

                Examples of incorrect outputs:
                - Benchmark and Qualitative (more than one)
                - Statistical (not in the list)

                Now, analyze the given research paper and return the most relevant Type of Evaluation:
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

                # Check if the response matches one of the taxonomy keys
                if result in type_of_evaluation_keys:
                    print(f"Valid result for entry {i}, after attempt {attempts + 1}: {result}")
                    break  # Valid response, exit the retry loop
                else:
                    attempts += 1


            except Exception as e:
                print(f"Error during OpenAI request for entry {i}: {e}")
                attempts += 1

        # If max attempts are reached, log the final result even if invalid
        if attempts == max_attempts:
            invalid_results += 1
            result = 'invalid result'

    # Ensure _id is treated as ObjectId
    entry_id = ObjectId(entry['_id'])  # MongoDB _id of the current entry

    # Write the result back to the database
    collection.update_one(
        {"_id": entry_id},
        {"$set": {"como-tax-type_of_evaluation2": result}},
        upsert=True  # Create the field if it doesn't exist
    )
    print(f"TypOfEval updated for entry ID: {entry_id}")
print(f'Invalid Results: {invalid_results}')

# Extract the the desired category
target_user_group = mapping.get('Target User Group', None)
target_user_group_keys = set(target_user_group.keys())

invalid_results = 0

# Loop through each entry in the data
for i, entry in enumerate(filtered_data):
    # Serialize the entry and taxonomy JSON
    entry_json = json.dumps(entry, indent=2, ensure_ascii=False)
    target_user_group_json_str = json.dumps(target_user_group, indent=2, ensure_ascii=False)

    # Construct the prompt
    prompt = f"""
            You are a highly focused expert trained to classify research papers based on their content. 
            Your task is to determine the most appropriate Target User Group from the provided Target User Group json for each research paper.

            Here is the research paper entry as JSON:
            {entry_json}

            Here is the Target User Group JSON file:
            {target_user_group_json_str}

            Your task:
            1. Read the Abstract and Full Text provided in the research paper JSON.
            2. Select the ONE best-matching Target User Group from the json file.
               - The output must be EXACTLY one Target User Group from the given file, with a maximum of 3 words.
               - Do NOT create new Target User Group or deviate from the list.
               - If more than one Target User Group matches, choose the most relevant one.
            4. Output ONLY the Target User Group name (no explanations, no additional words, no code).

            Example of correct outputs:
            - Designer
            - Researcher

            Examples of incorrect outputs:
            - I would say Designer, but .. (extra explanation)
            - Students (not in the list)

            Now, analyze the given research paper and return the most relevant Target User Group:
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

                # Check if the response matches one of the taxonomy keys
                if result in target_user_group_keys:
                    print(f"Valid result for entry {i}, after attempt {attempts + 1}: {result}")
                    break  # Valid response, exit the retry loop
                else:
                    attempts += 1


            except Exception as e:
                print(f"Error during OpenAI request for entry {i}: {e}")
                attempts += 1

        # If max attempts are reached, log the final result even if invalid
        if attempts == max_attempts:
            invalid_results += 1
            result = 'invalid result'

    # Ensure _id is treated as ObjectId
    entry_id = ObjectId(entry['_id'])  # MongoDB _id of the current entry

    # Write the result back to the database
    collection.update_one(
        {"_id": entry_id},
        {"$set": {"como-tax-target_user_group2": result}},
        upsert=True  # Create the field if it doesn't exist
    )
    print(f"TargetUserGroup updated for entry ID: {entry_id}")
print(f'Invalid Results: {invalid_results}')

# Extract the the desired category
research_problem = mapping.get('Research Problem', None)
research_problem_keys = set(research_problem.keys())

invalid_results = 0

# Loop through each entry in the data
for i, entry in enumerate(filtered_data):
    # Serialize the entry and taxonomy JSON
    entry_json = json.dumps(entry, indent=2, ensure_ascii=False)
    research_problem_json_str = json.dumps(research_problem, indent=2, ensure_ascii=False)

    # Construct the prompt
    prompt = f"""
                You are a highly focused expert trained to classify research papers based on their content. 
                Your task is to determine the most appropriate Research Problem from the provided Research Problem json for each research paper.

                Here is the research paper entry as JSON:
                {entry_json}

                Here is the Research Problem JSON file:
                {research_problem_json_str}

                Here are examples for research problems:
                Empirical Example: User behavior in VR, Impact of dark mode on reading speed
                Conceptual Example: Definition of digital well-being, Rethinking usability in AI-driven systems
                Constructive Example: Designing a new haptic feedback system, Developing a privacy-preserving chatbot

                Your task:
                1. Read the Abstract and Full Text provided in the research paper JSON.
                2. Select the ONE best-matching Research Problem from the json file.
                   - The output must be EXACTLY one Research Problem from the given file, with a maximum of 3 words.
                   - Do NOT create new Research Problems or deviate from the list.
                   - If more than one Research Problem matches, choose the most relevant one.
                4. Output ONLY the Research Problem name (no explanations, no additional words, no code).

                Examples of correct outputs:
                - Empirical
                - Conceptual
                - Constructive

                Examples of incorrect outputs:
                - Methodological (not in the List)
                - I would say Empirical, because .. (extra explanation)

                Now, analyze the given research paper and return the most relevant Research Problem:
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

                # Check if the response matches one of the taxonomy keys
                if result in research_problem_keys:
                    print(f"Valid result for entry {i}, after attempt {attempts + 1}: {result}")
                    break  # Valid response, exit the retry loop
                else:
                    attempts += 1


            except Exception as e:
                print(f"Error during OpenAI request for entry {i}: {e}")
                attempts += 1

        # If max attempts are reached, log the final result even if invalid
        if attempts == max_attempts:
            invalid_results += 1
            result = 'invalid result'

    # Ensure _id is treated as ObjectId
    entry_id = ObjectId(entry['_id'])  # MongoDB _id of the current entry

    # Write the result back to the database
    collection.update_one(
        {"_id": entry_id},
        {"$set": {"como-tax-research_problem2": result}},
        upsert=True  # Create the field if it doesn't exist
    )
    print(f"ResearchProblem updated for entry ID: {entry_id}")
print(f'Invalid Results: {invalid_results}')

openess = mapping.get('Openess', None)
openess_keys = set(openess.keys())

# openess_keys = ['Open Source','Closed Source']
# invalid_results = 0

# Loop through each entry in the data
for i, entry in enumerate(filtered_data):
    # Serialize the entry and taxonomy JSON
    entry_json = json.dumps(entry, indent=2, ensure_ascii=False)
    openess_json_str = json.dumps(openess, indent=2, ensure_ascii=False)
    # Construct the prompt
    prompt = f"""
                You are a highly focused expert trained to classify research papers based on their content. 
                Your task is to determine whether each research paper was published under Open Source or Closed Source.

                Here is the research paper entry as JSON:
                {entry_json}
                Here is the mapping: 
                {openess_json_str}

                Your task:
                1. Read the Abstract and Full Text provided in the research paper JSON.
                2. Based on the information from each entry, decide whether its (partly) open or closed source.
                3. Output Open Source, if the Data is openly available, and Closed Source, if not.
                4. If only the Source code is available, output Only Code openly available
                5. If only the Data is available, output Only Data openly available
                6. Output IN EVERY CASE one of the below options of correct outputs:

                Examples of correct outputs:
                - Open Source
                - Closed Source
                - Only Code openly available
                - Only Data openly available

                Examples of incorrect outputs:
                - Open Data (not in the desired anwsers)
                - Upon reviewing the abstract and full text, the following points are relevant: ... (additional explanation)

                Now, analyze the given research paper and return one of the correct output options. It is very important to not output any other 
                explanations, but rather only the correct output options (therefore the output must have a maximum of 4 words):
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

                # Check if the response matches one of the taxonomy keys
                if result in openess_keys:
                    print(f"Valid result for entry {i}, after attempt {attempts + 1}: {result}")
                    break  # Valid response, exit the retry loop
                else:
                    attempts += 1


            except Exception as e:
                print(f"Error during OpenAI request for entry {i}: {e}")
                attempts += 1

        # If max attempts are reached, log the final result even if invalid
        if attempts == max_attempts:
            invalid_results += 1
            result = 'invalid result'

    # Ensure _id is treated as ObjectId
    entry_id = ObjectId(entry['_id'])  # MongoDB _id of the current entry

    # Write the result back to the database
    collection.update_one(
        {"_id": entry_id},
        {"$set": {"como-tax-openess2": result}},
        upsert=True  # Create the field if it doesn't exist
    )
    print(f"Openess updated for entry ID: {entry_id}")
print(f'Invalid Results: {invalid_results}')

# Extract the the desired category
modelling_approach = mapping.get('Modelling Approach', None)
# Extract Theory-Driven and Data-Driven modelling types
theory_driven_types = set(mapping["Modelling Approach"]["Theory-Driven"].keys())
data_driven_types = set(mapping["Modelling Approach"]["Data Driven"].keys())
modelling_approach_keys = set(theory_driven_types) | set(data_driven_types)

invalid_results = 0

# Loop through each entry in the data
for i, entry in enumerate(filtered_data):
    # Serialize the entry and taxonomy JSON
    entry_json = json.dumps(entry, indent=2, ensure_ascii=False)
    modelling_approach_json_str = json.dumps(modelling_approach, indent=2, ensure_ascii=False)

    # Construct the prompt
    prompt = f"""
                        You are a highly focused expert trained to classify research papers based on their content. 
                        Your task is to determine the most appropriate Modelling Approach from the provided contribution json for each research paper.

                        Here is the research paper entry as JSON:
                        {entry_json}

                        Here is the Modelling Approach JSON file:
                        {modelling_approach_json_str}

                        Your task:
                        1. Read the Abstract and Full Text provided in the research paper JSON.
                        2. Select the ONE best-matching Modelling Approach from the json file.
                           - The output must be EXACTLY one Modelling Approach from the given file, with a maximum of 3 words.
                           - Choose topics as specific (low in the hierarchy of the json) as possible.
                           - Do NOT create new Modelling Approaches or deviate from the list.
                           - If more than one Modelling Approach matches, choose the most relevant one.
                        4. Output ONLY the Modelling Approach name (no explanations, no additional words, no code).

                        Cognitive Models Example: ACT-R (Adaptive Control of Thought-Rational), SOAR (State, Operator, and Result)
                        Reinforcement Learning Example: Q-Learning, Policy Gradient Methods
                        Mechanistic Models Example: Hick’s Law, Fitts’ Law
                        Supervised Machine Learning Example: Random Forest, Support Vector Machine (SVM)
                        Unsupervised Machine Learning Example: K-Means Clustering, Principal Component Analysis (PCA)
                        Bayesian & Probabilistic Models Example: Hidden Markov Model (HMM), Naïve Bayes Classifier
                        Deep Learning & Neural Networks Example: Convolutional Neural Networks (CNNs), Transformer

                        Now, analyze the given research paper and return the most relevant contribution type:
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

                # Check if the response matches one of the taxonomy keys
                if result in modelling_approach_keys:
                    print(f"Valid result for entry {i}, after attempt {attempts + 1}: {result}")
                    break  # Valid response, exit the retry loop
                else:
                    attempts += 1


            except Exception as e:
                print(f"Error during OpenAI request for entry {i}: {e}")
                attempts += 1

        # If max attempts are reached, log the final result even if invalid
        if attempts == max_attempts:
            invalid_results += 1
            result = 'invalid result'

    # Ensure _id is treated as ObjectId
    entry_id = ObjectId(entry['_id'])  # MongoDB _id of the current entry

    # Write the result back to the database
    collection.update_one(
        {"_id": entry_id},
        {"$set": {"como-tax-modelling_approach2": result}},
        upsert=True  # Create the field if it doesn't exist
    )
    print(f"ModellingApproach updated for entry ID: {entry_id}")
print(f'Invalid Results: {invalid_results}')

improvement_proposal_keys = ['Yes', 'No']

invalid_results = 0

# Loop through each entry in the data
for i, entry in enumerate(filtered_data):
    # Serialize the entry and taxonomy JSON
    entry_json = json.dumps(entry, indent=2, ensure_ascii=False)

    # Construct the prompt
    prompt = f"""
                You are a highly focused expert trained to classify research papers based on their content. 
                Your task is to determine whether each research paper has a improvement proposal in it or not.

                Here is the research paper entry as JSON:
                {entry_json}


                Your task:
                1. Read the Abstract and Full Text provided in the research paper JSON.
                2. Based on the information from each entry, decide whether the authors propose an improvement for future research.
                3. Output Yes, if thy do so and No, if they don't.
                4. Output ONLY Yes or No (no explanations, no additional words, no code).

                Examples of correct outputs:
                - Yes
                - No

                Examples of incorrect outputs:
                - Yes, but they .. (additional explanation)
                - Kind of (not Yes or No)

                Now, analyze the given research paper and return whether they have an improvement proposal or not:
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

                # Check if the response matches one of the taxonomy keys
                if result in improvement_proposal_keys:
                    print(f"Valid result for entry {i}, after attempt {attempts + 1}: {result}")
                    break  # Valid response, exit the retry loop
                else:
                    attempts += 1


            except Exception as e:
                print(f"Error during OpenAI request for entry {i}: {e}")
                attempts += 1

        # If max attempts are reached, log the final result even if invalid
        if attempts == max_attempts:
            invalid_results += 1
            result = 'invalid result'

    # Ensure _id is treated as ObjectId
    entry_id = ObjectId(entry['_id'])  # MongoDB _id of the current entry

    # Write the result back to the database
    collection.update_one(
        {"_id": entry_id},
        {"$set": {"como-tax-improvement_proposal2": result}},
        upsert=True  # Create the field if it doesn't exist
    )
    print(f"ImprovementProposal updated for entry ID: {entry_id}")
print(f'Invalid Results: {invalid_results}')

ethics_keys = ['Ignored', 'Discussed', 'Discussed and Addressed']

invalid_results = 0

# Loop through each entry in the data
for i, entry in enumerate(filtered_data):
    # Serialize the entry and taxonomy JSON
    entry_json = json.dumps(entry, indent=2, ensure_ascii=False)

    # Construct the prompt
    prompt = f"""
            You are a highly focused expert trained to classify research papers based on their content. 
            Your task is to determine, whether Ethics are addressed, discussed or addressed and discussed in the research paper.

            Here is the research paper entry as JSON:
            {entry_json}


            Your task:
            1. Read the Abstract and Full Text provided in the research paper JSON.
            2. Based on the information from each entry, decide whether ethics are addressed and / or discussed.
            3. Output ONLY Ignored, Discussed or Discussed and Addressed (no explanations, no additional words, no code).

            Example of correct outputs:
            - Ignored
            - Discussed 
            - Discussed and Addressed

            Examples of incorrect outputs:
            - Ethics are discussed, but .. (extra explanation)
            - Mentioned (not in the list)

            Now, analyze the given research paper and return how Ethical Concerns are handled in the paper:
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

                # Check if the response matches one of the taxonomy keys
                if result in ethics_keys:
                    print(f"Valid result for entry {i}, after attempt {attempts + 1}: {result}")
                    break  # Valid response, exit the retry loop
                else:
                    attempts += 1


            except Exception as e:
                print(f"Error during OpenAI request for entry {i}: {e}")
                attempts += 1

        # If max attempts are reached, log the final result even if invalid
        if attempts == max_attempts:
            invalid_results += 1
            result = 'invalid result'

    # Ensure _id is treated as ObjectId
    entry_id = ObjectId(entry['_id'])  # MongoDB _id of the current entry

    # Write the result back to the database
    collection.update_one(
        {"_id": entry_id},
        {"$set": {"como-tax-ethics2": result}},
        upsert=True  # Create the field if it doesn't exist
    )
    print(f"Ethics updated for entry ID: {entry_id}")
print(f'Invalid Results: {invalid_results}')

# Extract the the desired category
data_used = mapping.get('Data Used', None)
data_used_keys = set(data_used.keys())

invalid_results = 0

# Loop through each entry in the data
for i, entry in enumerate(filtered_data):
    # Serialize the entry and taxonomy JSON
    entry_json = json.dumps(entry, indent=2, ensure_ascii=False)
    data_used_json_str = json.dumps(data_used, indent=2, ensure_ascii=False)

    # Construct the prompt
    prompt = f"""
            You are a highly focused expert trained to classify research papers based on their content. 
            Your task is to determine the most appropriate Type of Data that is used to get the 
            results in the current paper. Take available Types from the provided json for each research paper.

            Here is the research paper entry as JSON:
            {entry_json}

            Here is the Type of Data that is used JSON file:
            {data_used_json_str}

            Your task:
            1. Read the Abstract and Full Text provided in the research paper JSON.
            2. Select the ONE best-matching Type of Data that is used from the json file.
               - The output must be EXACTLY one Type of Data that is used from the given file, with a maximum of 3 words.
               - Do NOT create new Type of Data that is used or deviate from the list.
               - If more than one Type of Data that is used matches, choose the most relevant one.
            4. Output ONLY the name of Type of Data that is used (no explanations, no additional words, no code).

            Examples of data-use:
            Visual Data (Screenshots, photos, videos, thermal images)
            Physiological Data (Heart rate, skin conductance, EEG, EMG)
            Behavioral Data (User interaction logs, movement data, eye gaze tracking)
            Textual and Linguistic Data (Natural language transcripts, textual input, human-written texts)
            Code and Programmatic Data (Source code, scripts, compiled binaries)
            Environmental and Contextual Data (Location data, environmental sensors, ambient noise)

            Example of correct outputs:
            - Text
            - Experimental Data

            Examples of incorrect outputs:
            - In general they use text, but .. (extra explanation)
            - Eye Tracking Data (not in the list)

            Now, analyze the given research paper and return the most relevant Type of data that is used for the paper:
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

                # Check if the response matches one of the taxonomy keys
                if result in data_used_keys:
                    print(f"Valid result for entry {i}, after attempt {attempts + 1}: {result}")
                    break  # Valid response, exit the retry loop
                else:
                    attempts += 1


            except Exception as e:
                print(f"Error during OpenAI request for entry {i}: {e}")
                attempts += 1

        # If max attempts are reached, log the final result even if invalid
        if attempts == max_attempts:
            invalid_results += 1
            result = 'invalid result'

    # Ensure _id is treated as ObjectId
    entry_id = ObjectId(entry['_id'])  # MongoDB _id of the current entry

    # Write the result back to the database
    collection.update_one(
        {"_id": entry_id},
        {"$set": {"como-tax-data_used2": result}},
        upsert=True  # Create the field if it doesn't exist
    )
    print(f"DataUsed updated for entry ID: {entry_id}")
print(f'Invalid Results: {invalid_results}')

# Extract the desired category
contribution = mapping.get('Contribution', None)
# Extract the keys from the taxonomy JSON
contribution_keys = set(contribution.keys())

invalid_results = 0

# Loop through each entry in the data
for i, entry in enumerate(filtered_data):
    # Serialize the entry and taxonomy JSON
    entry_json = json.dumps(entry, indent=2, ensure_ascii=False)
    contribution_json_str = json.dumps(contribution, indent=2, ensure_ascii=False)

    # Construct the prompt
    prompt = f"""
            You are a highly focused expert trained to classify research papers based on their content. 
            Your task is to determine the most appropriate contribution type from the provided contribution json for each research paper.

            Here is the research paper entry as JSON:
            {entry_json}

            Here is the contribution JSON file:
            {contribution_json_str}

            Here are examples for evry contribution type:
            Empirical Research Example: User study on AR interfaces, Eye-tracking in data visualization
            Artifact Example: Gesture-based text input, Accessibility tool for blind users
            Methodological Example: New usability testing framework
            Theoretical Example: Model of user trust in AI
            Dataset Example: Large-scale touchscreen interaction logs,  dataset of VR hand gestures
            Survey Example: Meta-analysis of UX studies, Survey on remote work challenges
            Opinion Example: Perspective on AI ethics in design, Critique of dark patterns in UI

            Your task:
            1. Read the Abstract and Full Text provided in the research paper JSON.
            2. Select the ONE best-matching contribution type from the json file.
               - The output must be EXACTLY one contribution type from the given file, with a maximum of 3 words.
               - Do NOT create new contribution type or deviate from the list.
               - If more than one contribution type matches, choose the most relevant one.
            4. Output ONLY the contribution type name (no explanations, no additional words, no code).

            Examples of correct outputs:
            - Opinion
            - Dataset

            Examples of incorrect outputs:
            - Opinion Paper and Research Paper (too long)
            - Other Contribution (not in taxonomy)
            - This paper belongs to Empirical Research (extra explanation)

            Now, analyze the given research paper and return the most relevant contribution type:
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

                # Check if the response matches one of the taxonomy keys
                if result in contribution_keys:
                    print(f"Valid result for entry {i}, after attempt {attempts + 1}: {result}")
                    break  # Valid response, exit the retry loop
                else:
                    attempts += 1


            except Exception as e:
                print(f"Error during OpenAI request for entry {i}: {e}")
                attempts += 1

        # If max attempts are reached, log the final result even if invalid
        if attempts == max_attempts:
            invalid_results += 1
            result = 'invalid result'

    # Ensure _id is treated as ObjectId
    entry_id = ObjectId(entry['_id'])  # MongoDB _id of the current entry

    # Write the result back to the database
    collection.update_one(
        {"_id": entry_id},
        {"$set": {"como-tax-contribution2": result}},
        upsert=True  # Create the field if it doesn't exist
    )
    print(f"Contribution updated for entry ID: {entry_id}")

print(f'Invalid Results: {invalid_results}')

# end_time = time.time()

# total_time = end_time-start_time
# print(f'Total time for one entry: {total_time} seconds')
