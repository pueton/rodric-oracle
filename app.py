import os
import base64
import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

class OracleResponse(BaseModel):
    reading: str
    saying: str

@app.post("/api/oracle", response_model=OracleResponse)
async def consult_oracle(file: UploadFile = File(...)):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="API key not configured on server.")

    image_bytes = await file.read()
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    mime_type = file.content_type or "image/jpeg"

    prompt = (
        "You are Rodric, an ancient Viking seer from Midgard. "
        "Analyse the shapes and patterns in this milk foam image. "
        "Respond ONLY as valid JSON without any Markdown or extra text:\n"
        '{"reading":"mystical interpretation of the milk foam pattern in old Norse Viking style in English, 3-5 sentences",'
        '"saying":"a wise Viking saying fitting the reading, 1-2 sentences"}'
    )

    payload = {
        "model": "claude-opus-4-5",
        "max_tokens": 1024,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": b64_image}},
                {"type": "text", "text": prompt}
            ]
        }]
    }

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    data = resp.json()
    raw = "".join(b.get("text", "") for b in data["content"])
    raw = raw.replace("```json", "").replace("```", "").strip()

    import json
    try:
        parsed = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not parse model response: " + raw)

    return OracleResponse(reading=parsed["reading"], saying=parsed["saying"])


# Serve static frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")
