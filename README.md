# Real-Time Voice Assistant

A real-time voice assistant with streaming ASR, LLM reasoning, and TTS synthesis. Features detailed latency budgeting, graceful degradation, and replay debugging.

## Features

- **Streaming Pipeline**: Audio in -> ASR -> LLM -> TTS -> Audio out
- **Latency Budget**: Decomposed end-to-end latency per component
- **WebSocket Orchestration**: Real-time bidirectional communication
- **Graceful Degradation**: Timeout handling, fallback responses
- **Replay Mode**: Feed recorded audio for debugging
- **Latency Visualization**: Per-request breakdown dashboard

## Architecture

```
Microphone → WebSocket → ASR (Deepgram/Whisper)
                              ↓
                         LLM Reasoning (streaming)
                              ↓
                         TTS Synthesis (ElevenLabs/Cartesia)
                              ↓
                         WebSocket → Speaker
```

## Tech Stack

- **ASR**: Deepgram (streaming) / OpenAI Whisper (local fallback)
- **LLM**: OpenAI GPT-4o / Ollama (local)
- **TTS**: ElevenLabs / Cartesia
- **Transport**: WebSockets (FastAPI)
- **Frontend**: Simple HTML/JS client

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add API keys
```

## Usage

```bash
# Start the voice assistant server
python src/server.py

# Open the web client
open http://localhost:8000

# Run with replay mode (recorded audio)
python src/server.py --replay recordings/test_session.wav

# View latency analysis
python src/latency_analysis.py
```

## Latency Budget

| Component | Target | Measurement |
|-----------|--------|-------------|
| ASR | < 300ms | Time from audio end to transcript |
| LLM TTFT | < 500ms | Time to first token from LLM |
| TTS TTFB | < 200ms | Time to first byte of audio |
| Overhead | < 100ms | WebSocket + processing |
| **Total** | **< 1.2s** | **End-to-end response time** |

## Phases

### Phase 1: Streaming Pipeline
- WebSocket server with audio streaming
- ASR integration (Deepgram or Whisper)
- LLM streaming response
- TTS streaming synthesis

### Phase 2: Latency Tracking
- Per-component timing instrumentation
- Latency budget visualization
- P50/P95 tracking across requests

### Phase 3: Resilience
- Timeout handling (no indefinite blocking)
- Graceful degradation on service failures
- Replay mode for debugging
- Fallback responses
