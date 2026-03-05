#!/usr/bin/env python3
"""
Smoke test for Gemini integration. Loads .env and calls the wrapper.
Run from project root: python test_gemini.py
Exits with 0 on success.
"""
from dotenv import load_dotenv

load_dotenv()

from ai.gemini_client import generate_text


def main():
    prompt = "Spune salut in romana."
    response = generate_text(prompt)
    print(response)
    assert response, "Empty response from Gemini"
    return 0


if __name__ == "__main__":
    exit(main())
