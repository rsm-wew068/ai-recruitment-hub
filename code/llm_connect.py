import os
import pyrsm as rsm
import google.generativeai as genai
import requests

# from google.genai import types
from typing import List


def query_llama(
    messages: List[dict],
    model: str = "llama-3",
    max_tokens: int = 4000,
    temperature: int = 0.4,
    api_key: str = "",
) -> dict:
    """
    Send a query to the Llama API

    Args:
        messages (list): List of dictionaries containing message role and content pairs
        model (str): The model to use. Defaults to "llama-3"
        max_tokens (int, optional): Maximum number of tokens to generate. Defaults to 4000
        temperature (int, optional): Controls randomness in the output. 0 is deterministic, higher values more random. Defaults to 0.4
        api_key (str, optional): Authentication token for API access. Defaults to ""

    Example:
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello!"}
        ]
        response = query_llama(messages, api_key="your-api-key")

    Returns:
        dict: The model's response
    """
    url = "https://traip13.tgptinf.ucsd.edu/v1/chat/completions"
    if not api_key or len(api_key) == 0:
        raise ValueError("LLAMA: API key is required")

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    data = {
        "messages": messages,
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,  # Adjust temperature for randomness (0 for deterministic)
        "stream": False,
        "n": 1,
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()  # Raise an exception for bad status codes

    return response.json()


def test_llama_connection(api_key: str, timeout: int = 20) -> bool:
    """Test connection to Llama API with a basic request"""
    import requests

    url = "https://traip13.tgptinf.ucsd.edu/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    data = {"messages": [], "model": "llama-3", "max_tokens": 1, "temperature": 0.4}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=20)
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        try:
            print(f"Response body: {response.json()}")
        except Exception:
            print(f"Response text: {response.text}")
        if response.status_code == 401:
            print("Authentication failed - check your API key")
            return False
        elif response.status_code == 404:
            print("API endpoint not found")
            return False
        elif response.status_code == 200:
            return True
        else:
            print(f"Unexpected status code: {response.status_code}")
            return False
    except requests.exceptions.Timeout:
        print(f"Connection timed out after {timeout} seconds")
        return False
    except requests.exceptions.ConnectionError:
        print("Could not connect to server")
        return False


def query_gemini(
    messages: List[dict],
    model: str = "gemini-2.0-flash",
    max_tokens: int = 4000,
    temperature: int = 0.4,
    api_key: str = "",
) -> dict:
    """
    Send a query to the Gemini API

    Args:
        messages (list): List of dictionaries containing message role and content pairs
        model (str): The model to use. Defaults to "gemini-2.0-flash"
        max_tokens (int, optional): Maximum number of tokens to generate. Defaults to 4000
        temperature (int, optional): Controls randomness in the output. 0 is deterministic, higher values more random. Defaults to 0.4
        api_key (str, optional): Authentication token for API access. Defaults to ""

    Returns:
        dict: The model's response
    """

    if not api_key or len(api_key) == 0:
        raise ValueError("Gemini: API key is required")

    # Convert OpenAI-style messages to Gemini format
    system_message = [msg["content"] for msg in messages if msg["role"] == "system"]
    user_messages = [msg["content"] for msg in messages if msg["role"] == "user"]

    # Combine system message (if any) with the user message
    prompt = ". ".join(system_message + user_messages)

    genai.configure(api_key=api_key)

    # Initialize the model
    model = genai.GenerativeModel(model_name=model)

    # Define the generation configuration using the specific class
    generation_config_obj = genai.types.GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
    )

    # Generate content using the correct parameter name 'generation_config'
    response = model.generate_content(
        contents=prompt, generation_config=generation_config_obj
    )

    return response.text


def get_response(
    input: str | List[str],
    template: callable,
    role: str = "You are a helpful assistant.",
    temperature: float = 0.4,
    max_tokens: int = 4000,
    md: bool = True,
    llm: str = "llama",
    model_name: str = None,
):
    """
    Function to get a response from the LLama API
    """
    messages = [
        {"role": "system", "content": role},
        {
            "role": "user",
            "content": template(input),
        },
    ]

    if llm == "llama":
        response = query_llama(
            messages=messages,
            api_key=os.getenv("LLAMA_API_KEY"),
            temperature=temperature,
            max_tokens=max_tokens,
        )["choices"][0]["message"]["content"]
    elif llm == "gemini":
        response = query_gemini(
            messages=messages,
            api_key=os.getenv("GEMINI_API_KEY"),
            temperature=temperature,
            max_tokens=max_tokens,
            model=model_name if model_name else 'gemini-2.0-flash'
        )
    else:
        raise ValueError("LLM: Invalid LLM specified")

    if md:
        return rsm.md(response)
    else:
        return response


if __name__ == "__main__":
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hi, how are you? What is your name?"},
    ]

    # Testing Llama connection
    try:
        print("\nTesting Llama connection ...")
        test_llama_connection(api_key=os.getenv("LLAMA_API_KEY"))
    except Exception as e:
        print(f"Error: {e}")

    # Testing Llama connection
    try:
        print("\nQuerying Llama ...")
        response = query_llama(messages, api_key=os.getenv("LLAMA_API_KEY"))
        print(response)
    except Exception as e:
        print(f"Error: {e}")

    try:
        print("\nQuerying Gemini ...")
        response = query_gemini(messages, api_key=os.getenv("GEMINI_API_KEY"))
        print(response)
    except Exception as e:
        print(f"Error: {e}")

    try:
        print("\nTesting get_response ...")

        def template(input):
            return f"""Evaluate the following statement for factual accuracy. If it's incorrect, provide the correct information:
            Statement: {input}
            Evaluation:"""

        response = get_response(
            "The capital of the Netherlands is Utrecht.",
            template=template,
            md=False,
            llm="llama",
        )
        print(response)

    except Exception as e:
        print(f"Error: {e}")
