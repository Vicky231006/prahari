import hashlib
import json
import os
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import redis
import chromadb
import google.generativeai as genai

from .corpus import RBI_CONTROLS

# App Config
app = FastAPI(
    title="PRAHARI RAG Explanation Service",
    description="Generates regulatory-cited explanations for security incidents using RBI CSF controls",
    version="1.0.0"
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

# Initialize Redis cache (24h TTL, Section 5)
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    redis_client.ping()
except Exception as e:
    print(f"[warning] Redis connection failed in RAG service: {e}")
    redis_client = None

# Initialize ChromaDB client with HTTP server fallback
chroma_client = None
collection = None

try:
    # Try connecting to HTTP ChromaDB server (Docker context)
    chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    print(f"[init] Connected to ChromaDB Server at {CHROMA_HOST}:{CHROMA_PORT}")
except Exception:
    # Fallback to local persistent database for standalone/tests
    try:
        chroma_client = chromadb.PersistentClient(path="./chroma_data")
        print("[init] Connected to local persistent ChromaDB")
    except Exception as e:
        print(f"[init] ChromaDB init failed, using in-memory Chroma: {e}")
        chroma_client = chromadb.EphemeralClient()

# Initialize collection and seed RBI controls
try:
    collection = chroma_client.get_or_create_collection(name="rbi_controls")
    # Check if empty
    if collection.count() == 0:
        print("[init] Seeding ChromaDB with RBI controls...")
        ids = [c["id"] for c in RBI_CONTROLS]
        documents = [c["summary"] for c in RBI_CONTROLS]
        metadatas = [{"control_no": c["control_no"], "title": c["title"], "keywords": ",".join(c["keywords"])} for c in RBI_CONTROLS]
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print(f"[init] Successfully seeded {collection.count()} controls")
except Exception as e:
    print(f"[error] Failed to initialize ChromaDB collection: {e}")


# Initialize Gemini API
if GEMINI_API_KEY and GEMINI_API_KEY != "your-gemini-api-key-here" and GEMINI_API_KEY != "test-key-not-real":
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-2.5-flash")
    print("[init] Google Gemini AI initialized successfully")
else:
    gemini_model = None
    print("[init] Gemini API key not set or placeholder. Falling back to deterministic RAG compiler.")


# Schemas
class ExplainRequest(BaseModel):
    contributing_signals: List[str]
    severity: str

class ExplainResponse(BaseModel):
    explanation: str
    regulatory_controls: List[Dict[str, Any]]


# Helper functions
def get_cache_key(signals: List[str], severity: str) -> str:
    """Generate MD5 hash key for caching (Section 5 RAG cache pattern)."""
    sorted_signals = sorted(list(set(signals)))
    raw_key = f"{','.join(sorted_signals)}:{severity}"
    return f"rag:cache:{hashlib.md5(raw_key.encode('utf-8')).hexdigest()}"


def query_relevant_controls(signals: List[str]) -> List[Dict[str, Any]]:
    """Retrieve relevant RBI controls from ChromaDB based on keywords/signals."""
    if not collection:
        return []
        
    try:
        # Build search query from contributing signals
        search_query = " ".join(signals)
        results = collection.query(
            query_texts=[search_query],
            n_results=3
        )
        
        controls = []
        if results and results["documents"]:
            for doc, meta, cid in zip(results["documents"][0], results["metadatas"][0], results["ids"][0]):
                controls.append({
                    "id": cid,
                    "control_no": meta["control_no"],
                    "title": meta["title"],
                    "summary": doc
                })
        return controls
    except Exception as e:
        print(f"[rag-err] ChromaDB query failed: {e}")
        # Manual keyword fallback if Chroma queries fail
        controls = []
        for ctrl in RBI_CONTROLS:
            if any(kw in signals or any(kw in sig for sig in signals) for kw in ctrl["keywords"]):
                controls.append({
                    "id": ctrl["id"],
                    "control_no": ctrl["control_no"],
                    "title": ctrl["title"],
                    "summary": ctrl["summary"]
                })
        return controls[:3]


def generate_local_explanation(signals: List[str], severity: str, controls: List[Dict[str, Any]]) -> str:
    """Deterministic, high-quality backup generator if Gemini API key is missing."""
    citations = [f"Control {c['control_no']}" for c in controls]
    citations_str = ", ".join(citations)
    
    signals_str = ", ".join(signals).replace("_", " ")
    
    explanation = (
        f"The fusion engine detected anomalous behavior involving {signals_str}. "
        f"This activity resulted in a {severity} severity alert due to potential policy violations. "
        f"Relevant compliance context: {citations_str}."
    )
    return explanation


@app.post("/api/explain", response_model=ExplainResponse)
async def explain_alert(req: ExplainRequest):
    """Generate regulatory cited explanation for an alert."""
    if not req.contributing_signals:
        return ExplainResponse(
            explanation="Normal behavioral activity. No active indicators detected.",
            regulatory_controls=[]
        )

    # 1. Check Redis cache first (Section 5)
    cache_key = get_cache_key(req.contributing_signals, req.severity)
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                print("[rag-cache] Cache hit for alert explanation")
                return ExplainResponse(
                    explanation=data["explanation"],
                    regulatory_controls=data["regulatory_controls"]
                )
            except Exception:
                pass

    # 2. Query ChromaDB for relevant controls
    controls = query_relevant_controls(req.contributing_signals)
    if not controls:
        # Ensure we always return at least one control citation (Control 13.2 correlation)
        controls = [{
            "id": "RBI-CS-06",
            "control_no": "13.2",
            "title": "Security Correlation & Incident Response",
            "summary": "Correlate distinct infrastructure alerts, behavioral anomalies, and transaction parameters."
        }]

    # 3. Generate explanation (Gemini vs Fallback)
    explanation = None
    if gemini_model:
        try:
            # Build prompt per Section 7
            controls_context = "\n".join([
                f"- Control {c['control_no']}: {c['title']} — {c['summary']}" 
                for c in controls
            ])
            
            prompt = (
                f"You are a cybersecurity expert at a national bank writing explaining notes for a regulatory audit.\n"
                f"Generate a 2-3 sentence plain-language explanation of a detected threat alert.\n\n"
                f"Alert Severity: {req.severity}\n"
                f"Active Threat Signals: {', '.join(req.contributing_signals)}\n\n"
                f"Retrieved RBI Controls Context:\n{controls_context}\n\n"
                f"Rules:\n"
                f"1. Explain what fired, why it's risky, and which control it violates.\n"
                f"2. Cite the control number specifically (e.g. 'Control {controls[0]['control_no']}').\n"
                f"3. Do not quote the control text verbatim, paraphrase it.\n"
                f"4. Keep it exactly to 2-3 sentences.\n"
                f"5. Do not use Markdown formatting in the sentences, return plain text."
            )
            
            response = gemini_model.generate_content(prompt)
            explanation = response.text.strip()
        except Exception as e:
            print(f"[rag-err] Gemini generation failed: {e}. Falling back.")
            
    if not explanation:
        explanation = generate_local_explanation(req.contributing_signals, req.severity, controls)

    payload = {
        "explanation": explanation,
        "regulatory_controls": controls
    }

    # 4. Cache response in Redis for 24 hours (Section 5)
    if redis_client:
        try:
            redis_client.setex(cache_key, 86400, json.dumps(payload))
            print("[rag-cache] Explanation cached successfully")
        except Exception as e:
            print(f"[rag-cache-err] Failed to cache explanation: {e}")

    return ExplainResponse(
        explanation=payload["explanation"],
        regulatory_controls=payload["regulatory_controls"]
    )


@app.post("/api/explain/stream")
async def explain_alert_stream(req: ExplainRequest):
    """SSE endpoint streaming the explanation word by word (Section 7)."""
    
    async def sse_generator():
        # Quick query for controls
        controls = query_relevant_controls(req.contributing_signals)
        if not controls:
            controls = [{
                "id": "RBI-CS-06",
                "control_no": "13.2",
                "title": "Security Correlation & Incident Response",
                "summary": "Correlate distinct infrastructure alerts, behavioral anomalies, and transaction parameters."
            }]
            
        controls_payload = {"type": "controls", "controls": [c["id"] for c in controls]}
        yield f"event: controls\ndata: {json.dumps(controls_payload)}\n\n"
        
        # Check cache
        cache_key = get_cache_key(req.contributing_signals, req.severity)
        if redis_client:
            cached = redis_client.get(cache_key)
            if cached:
                try:
                    data = json.loads(cached)
                    explanation = data["explanation"]
                    for word in explanation.split(" "):
                        text_payload = {"type": "text", "content": word + " "}
                        yield f"event: text\ndata: {json.dumps(text_payload)}\n\n"
                        await asyncio.sleep(0.05)
                    yield "event: end\ndata: [DONE]\n\n"
                    return
                except Exception:
                    pass

        # Generate and stream
        explanation = None
        if gemini_model:
            try:
                controls_context = "\n".join([
                    f"- Control {c['control_no']}: {c['title']} — {c['summary']}" 
                    for c in controls
                ])
                prompt = (
                    f"Write a 2-3 sentence explaining note for security audit.\n"
                    f"Alert Severity: {req.severity}\n"
                    f"Active Threat Signals: {', '.join(req.contributing_signals)}\n"
                    f"Retrieved RBI Controls:\n{controls_context}\n"
                    f"Cite control number specifically. Do not format with markdown."
                )
                response = gemini_model.generate_content(prompt)
                explanation = response.text.strip()
                
                # Stream explanation
                for word in explanation.split(" "):
                    text_payload = {"type": "text", "content": word + " "}
                    yield f"event: text\ndata: {json.dumps(text_payload)}\n\n"
                    await asyncio.sleep(0.05)
                    
            except Exception as e:
                print(f"[rag-stream-err] Gemini failed: {e}")
                
        if not explanation:
            explanation = generate_local_explanation(req.contributing_signals, req.severity, controls)
            for word in explanation.split(" "):
                text_payload = {"type": "text", "content": word + " "}
                yield f"event: text\ndata: {json.dumps(text_payload)}\n\n"
                await asyncio.sleep(0.05)

        # Cache it
        if redis_client:
            try:
                redis_client.setex(cache_key, 86400, json.dumps({
                    "explanation": explanation,
                    "regulatory_controls": controls
                }))
            except Exception:
                pass
                
        yield "event: end\ndata: [DONE]\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
