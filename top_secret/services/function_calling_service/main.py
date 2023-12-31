from typing import Any
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import os

llm_path = os.getenv("MODEL_PATH", "/app/models/TheBloke_gorilla-openfunctions-v1-GPTQ")


class TextGenerator:
    def __init__(self, model_path, system_message="You are a helpful assistant"):
        self.model_path = model_path
        self.system_message = system_message
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path, device_map="auto", trust_remote_code=False, revision="main"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=True)

    def generate_text(
        self,
        prompt,
        system_message=None,
        method="direct",
        max_new_tokens=1012,
        temperature=0.1,
        top_p=0.95,
        top_k=40,
        pipeline_type="text-generation",
    ):
        print("Generating text...")
        print(f"Prompt: {prompt}")
        print(f"System message: {system_message}")
        print(f"Method: {method}")
        print(f"Max new tokens: {max_new_tokens}")
        print(f"Temperature: {temperature}")
        print(f"Top p: {top_p}")
        print(f"Top k: {top_k}")
        print(f"Pipeline type: {pipeline_type}")

        # Use the system_message if provided, else use the one from __init__
        system_message = (
            system_message if system_message is not None else self.system_message
        )
        prompt_template = f"system\n{system_message}\nuser\n{prompt}\nassistant\n"

        if method == "direct":
            return self._generate_direct(
                prompt_template, max_new_tokens, temperature, top_p, top_k
            )
        elif method == "pipeline":
            return self._generate_pipeline(
                prompt_template,
                max_new_tokens,
                temperature,
                top_p,
                top_k,
                pipeline_type,
            )
        else:
            raise ValueError("Invalid method. Choose 'direct' or 'pipeline'.")

    def _generate_direct(
        self, prompt_template, max_new_tokens, temperature, top_p, top_k
    ):
        input_ids = self.tokenizer(
            prompt_template, return_tensors="pt"
        ).input_ids.cuda()
        output = self.model.generate(
            inputs=input_ids,
            temperature=temperature,
            do_sample=True,
            top_p=top_p,
            top_k=top_k,
            max_new_tokens=max_new_tokens,
        )
        full_text = self.tokenizer.decode(output[0])
        return self._extract_generated_text(full_text)

    def _generate_pipeline(
        self, prompt_template, max_new_tokens, temperature, top_p, top_k, pipeline_type
    ):
        pipe = pipeline(
            pipeline_type,
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            repetition_penalty=1.1,
        )
        full_text = pipe(prompt_template)[0]["generated_text"]
        return self._extract_generated_text(full_text)

    def _extract_generated_text(self, full_text):
        # Split the text and extract the part after the last "assistant\n"
        parts = full_text.split("assistant\n")
        generated_text = parts[-1].strip() if parts else ""

        # Remove specific tokens like "<s>" if they appear at the start or end
        generated_text = generated_text.replace("<|im_end|>", "").strip()

        return generated_text


# Initialize your TextGenerator
text_generator = TextGenerator(llm_path)


# Define a request model for the API
class FunctionRequest(BaseModel):
    prompt: str
    function: Any


# Initialize FastAPI app
app = FastAPI()

# Initialize your TextGenerator


@app.post("/function")
async def function(request: FunctionRequest):
    """
    Process a text generation request with an optional function parameter.

    This endpoint accepts a POST request with a JSON body containing two fields:
    'prompt' and 'function'. The 'prompt' is a string that represents the user's
    input or query.
    The 'function' is a flexible field that can accept any data type, allowing for
    a wide range
    of additional information or instructions to be included in the request.

    The endpoint processes this information using a text generation model and returns
    the generated text based on the provided 'prompt' and 'function'.

    Args:
        request (FunctionRequest): A request model that includes:
            - prompt (str): The input text or query for the text generation model.
            - function (Any): An optional field for additional data or instructions.
              This field is highly flexible and can include various data structures
              like lists, dictionaries, strings, etc.

    Returns:
        dict: A dictionary containing the generated text. The key 'result' maps to
        the generated text as a string.

    Raises:
        HTTPException: An exception is raised with status code 500 if there is any
        error during the processing of the request.

    Example of a valid request body:
    ```
    {
        "prompt": "Call me an Uber ride type \"Plus\" in Berkeley at zipcode 94704 in
          10 minutes",
        "function": [
            {
                "name": "Uber Carpool",
                "api_name": "uber.ride",
                "description": "Find suitable ride for customers given the location,
                type of ride, and the amount of time the customer is willing to wait as
                parameters",
                "parameters": [
                    {
                        "name": "loc",
                        "description": "Location of the starting place of the Uber ride"
                    },
                    {
                        "name": "type",
                        "enum": ["plus", "comfort", "black"],
                        "description": "Types of Uber ride user is ordering"
                    },
                    {
                        "name": "time",
                        "description": "The amount of time in minutes the customer is
                        willing to wait"
                    }
                ]
            }
        ]
    }
    ```

    Note:
        The 'function' field is designed to be highly flexible to accommodate various
        types of data structures and use cases. It should be structured in a way that
        the text generation model can interpret and utilize effectively.
    """

    # Example usage
    prompt = request.prompt
    functions = request.function

    functions_string = json.dumps(functions)
    prompt_template = (
        f"USER: <<question>> {prompt} <<function>> {functions_string}\nASSISTANT: "
    )

    # Generate text using TextGenerator

    try:
        # Modify this part as per how you want to handle 'function' parameter
        response = text_generator.generate_text(prompt_template, method="direct")
        print(response)
        return {"result": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Run the application
# Uncomment the following lines if you want to run the app using this script
# import uvicorn

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)
