import base64
import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

base_dir = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(base_dir, "key.env"))

API_KEY = os.getenv("GEMINI_API_KEY")

file_path = os.path.join(base_dir, "prompt.txt")

PDF_PATH = os.path.join(base_dir, "aetna1.pdf")

client = genai.Client(api_key=API_KEY)


def generate_payers_json(pdf_paths: list[str]):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
    except FileNotFoundError:
        return "Error: The specified file was not found."

    prompt = prompt_content

    uploaded_files = []
    for path in pdf_paths:
        uploaded = client.files.upload(
            file=path,
            config={"mime_type": "application/pdf"}
        )
        uploaded_files.append(uploaded)

    contents = [prompt] + uploaded_files

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=contents
    )

    return response.text


if __name__ == "__main__":
    print(generate_payers_json([PDF_PATH]))
    






