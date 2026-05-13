"""WebSocket server for real-time voice assistant pipeline."""

import asyncio
import json
import os
import time
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.latency_tracker import LatencyStore, RequestLatency

load_dotenv()

app = FastAPI(title="Real-Time Voice Assistant")
latency_store = LatencyStore()

ASR_TIMEOUT = int(os.getenv("ASR_TIMEOUT_MS", "5000")) / 1000
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT_MS", "10000")) / 1000
TTS_TIMEOUT = int(os.getenv("TTS_TIMEOUT_MS", "5000")) / 1000

FALLBACK_RESPONSE = "I'm sorry, I'm experiencing a brief delay. Could you please repeat that?"


async def transcribe_audio(audio_data: bytes) -> str:
    """ASR: Convert audio to text using Deepgram."""
    # TODO: Integrate Deepgram streaming API
    # Placeholder for ASR integration
    await asyncio.sleep(0.1)  # Simulated latency
    return "Hello, how can you help me today?"


async def generate_response(transcript: str) -> str:
    """LLM: Generate response from transcript."""
    import openai

    client = openai.AsyncOpenAI()
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "gpt-4o"),
                messages=[
                    {"role": "system", "content": "You are a helpful voice assistant. Keep responses concise (2-3 sentences)."},
                    {"role": "user", "content": transcript},
                ],
                stream=False,
            ),
            timeout=LLM_TIMEOUT,
        )
        return response.choices[0].message.content
    except asyncio.TimeoutError:
        return FALLBACK_RESPONSE


async def synthesize_speech(text: str) -> bytes:
    """TTS: Convert text to speech audio."""
    # TODO: Integrate ElevenLabs/Cartesia TTS API
    # Placeholder for TTS integration
    await asyncio.sleep(0.1)  # Simulated latency
    return b""  # Would return audio bytes


@app.websocket("/ws/voice")
async def voice_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time voice interaction."""
    await websocket.accept()
    try:
        while True:
            audio_data = await websocket.receive_bytes()
            request_id = str(uuid.uuid4())[:8]
            latency = RequestLatency(request_id=request_id)

            # ASR
            start = time.perf_counter()
            try:
                transcript = await asyncio.wait_for(transcribe_audio(audio_data), timeout=ASR_TIMEOUT)
            except asyncio.TimeoutError:
                await websocket.send_json({"error": "ASR timeout", "fallback": FALLBACK_RESPONSE})
                continue
            latency.asr_latency_ms = (time.perf_counter() - start) * 1000

            # LLM
            start = time.perf_counter()
            response_text = await generate_response(transcript)
            latency.llm_total_ms = (time.perf_counter() - start) * 1000
            latency.llm_ttft_ms = latency.llm_total_ms  # Non-streaming; in streaming this would differ

            # TTS
            start = time.perf_counter()
            try:
                audio_response = await asyncio.wait_for(synthesize_speech(response_text), timeout=TTS_TIMEOUT)
            except asyncio.TimeoutError:
                await websocket.send_json({"text": response_text, "warning": "TTS timeout, text-only response"})
                latency.tts_total_ms = TTS_TIMEOUT * 1000
                latency_store.record(latency)
                continue
            latency.tts_ttfb_ms = (time.perf_counter() - start) * 1000
            latency.tts_total_ms = latency.tts_ttfb_ms

            latency_store.record(latency)

            await websocket.send_json({
                "request_id": request_id,
                "transcript": transcript,
                "response": response_text,
                "latency": latency.to_dict(),
            })

            if audio_response:
                await websocket.send_bytes(audio_response)

    except WebSocketDisconnect:
        pass


@app.get("/metrics")
async def get_metrics():
    """Return current latency metrics."""
    return {
        "total_requests": len(latency_store.requests),
        "percentiles": latency_store.get_percentiles(),
        "budget_check": latency_store.check_budget(),
    }


@app.get("/")
async def index():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head><title>Voice Assistant</title></head>
    <body>
        <h1>Real-Time Voice Assistant</h1>
        <button id="start">Start Recording</button>
        <button id="stop" disabled>Stop</button>
        <div id="output"></div>
        <script>
            // WebSocket voice client - connect to /ws/voice
            // Capture audio via MediaRecorder API, send chunks over WebSocket
            // Display transcript and response
            const output = document.getElementById('output');
            output.innerHTML = '<p>Click Start to begin. Ensure microphone access is granted.</p>';
        </script>
    </body>
    </html>
    """)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
