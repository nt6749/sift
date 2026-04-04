import base64
import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

base_dir = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(base_dir, "key.env"))

file_path = os.path.join(base_dir, "prompt.txt")

def generate_payers_json():
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
    except FileNotFoundError:
        return "Error: The specified file was not found."

    prompt = prompt_content

    print(prompt)

if __name__ == "__main__":
    generate_payers_json()






