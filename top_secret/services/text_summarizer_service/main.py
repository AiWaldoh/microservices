from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os

llm_path = os.getenv("MODEL_PATH", "/app/models/TheBloke_dolphin-2.6-mistral-7B-GPTQ")


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
        temperature=0.7,
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


app = FastAPI()


# Define a request model for the API
class CompletionRequest(BaseModel):
    system_message: str
    prompt: str
    method: str = "direct"
    max_new_tokens: int
    temperature: float
    top_p: float = 0.95
    top_k: int = 40
    pipeline_type: str = "text-generation"


# Initialize your TextGenerator
# llm_path = "/media/aiwaldoh/LLM/models/TheBloke_dolphin-2.6-mistral-7B-GPTQ"
text_gen = TextGenerator(llm_path)


@app.post("/completion")
async def completion(request: CompletionRequest):
    try:
        response = text_gen.generate_text(
            prompt=request.prompt,
            system_message=request.system_message,
            method=request.method,
            max_new_tokens=request.max_new_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            top_k=request.top_k,
            pipeline_type=request.pipeline_type,
        )
        return {"result": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Run the app with a command like: uvicorn your_script_name:app --reload
