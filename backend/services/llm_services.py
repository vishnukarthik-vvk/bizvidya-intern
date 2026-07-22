import os
import json 
import re
from groq import Groq
from fastapi import HTTPException



class LLMServices:
    def __init__(self):
        self.clients = {
            1:Groq(api_key = os.getenv("GROQ_API_KEY")),
            2:Groq(api_key = os.getenv("GROQ_API_KEY")),
            3: Groq(api_key=os.getenv("GROQ_API_KEY_3")),
            4: Groq(api_key=os.getenv("GROQ_API_KEY_4")),
        }
    def generate(
            self,
            prompt,
            system_message = "you are a helpful AI assistant. Return only valid JSON.",
            client = 1,
            model = "openai/gpt-oss-120b",
            temperature = 0.7,
            max_tokens = 1500,
    ):
        try:
            response = self.clients[client].chat.completions.create( 
                model = model,
                messages=[
                    {
                        "role" :"system",
                        "content":system_message,
                    },
                    {
                        "role" : "user",
                        "content" : prompt,
                    },
                ],
                temperature = temperature,
                max_tokens = max_tokens,
                top_p = 1,
                stream = False,
            )

            raw = response.choices[0].message.content.strip()

            clean = re.sub(
                r"^```json\s*|```$",
                "",
                raw,
                flags=re.DOTALL,
            ).strip()

            return json.loads(clean), raw
        
        except Exception as e:
            raise HTTPException(
                status_code = 500,
                detail = str(e),
            )
        

    def generate_text(
            self,
            prompt,
            system_message,
            client = 1,
            temperature = 0.7,
            max_tokens = 1500,
            model = "openai/gpt-oss-120b",
    ):
        try:
            responses = self.clients[client].chat.completions.create(
                model = model,
                messages = [
                    {
                        "role" : "system",
                        "content": system_message
                    },{
                        "role": "user",
                        "content" : prompt,
                    },
                ],
                temperature=temperature,
                max_tokens = max_tokens,
                stream = False,
                stop = None,
            )
            return responses.choices[0].message.content.strip()
        
        except Exception as e:
            raise HTTPException(
                status_code = 500,
                detail=f"groq API error :{str(e)}",
            )
        
llm_services = LLMServices()