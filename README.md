# NeuralRevise

An autonomous web agent that combines browser automation, local or cloud LLM inference, and adaptive memory to complete tasks on web-based revision platforms without human intervention.

Built as a personal research project to explore how AI agents interact with real-world web environments, navigate bot detection systems, and improve their own performance over time through experience.

## What it does

The agent operates a real browser session, reads content from web pages, makes decisions using a language model, executes actions (clicks, form input, navigation), and learns from the outcomes of those actions. Over repeated runs it builds an accurate knowledge base that replaces LLM inference entirely for previously seen inputs, dramatically improving both speed and accuracy.

## Key features

- **Autonomous browser control** via Playwright and Chrome DevTools Protocol (CDP)
- **Multiple AI backends** --> Ollama (local), OpenRouter (cloud, free tier), or Google Gemini
- **Adaptive memory system** --> stores correct answers in a local JSON knowledge base, replacing LLM calls on repeat encounters
- **Cloudflare bot detection bypass** via CDP attachment to a real Chrome session
- **Atomic file writes** --> knowledge base is corruption-safe even on hard interrupts
- **Self-improving accuracy** --> agent improves with every run as the knowledge base grows

## Technical stack

- Python 3.12+
- Playwright (browser automation + CDP)
- Ollama / OpenRouter / Google Gemini (LLM inference)
- Chrome with remote debugging enabled

## Architecture

```
┌─────────────────────────────────────────────┐
│              Chrome (CDP)                   │
│  Real browser session, bypasses bot         │
│  detection by using genuine browser         │
│  fingerprints                               │
└────────────────────┬────────────────────────┘
                     │ Playwright CDP
┌────────────────────▼────────────────────────┐
│              Agent Core                     │
│  - Reads page content                       │
│  - Checks adaptive memory                   │
│  - Queries LLM if needed                    │
│  - Executes actions                         │
│  - Learns from outcomes                     │
└──────────┬─────────────────┬────────────────┘
           │                 │
┌──────────▼──────┐  ┌───────▼──────────────┐
│   LLM Backend   │  │   learned.json       │
│  Ollama /       │  │   Adaptive memory    │
│  OpenRouter /   │  │   Knowledge base     │
│  Gemini         │  │   (auto-generated)   │
└─────────────────┘  └──────────────────────┘
```

## How the adaptive memory works

On first encounter with an input, the agent queries the LLM. After acting, it reads the outcome from the page and stores the ground truth answer in `learned.json`. On subsequent encounters with the same input, the agent retrieves the answer directly from memory, bypassing LLM inference entirely. Over time, the agent converges toward near-perfect accuracy and near-instant response times.

`learned.json` is automatically created on first run and grows with every session.

## Installation

```bash
pip install playwright requests
playwright install chrome
```

Then pick your preferred AI backend:

| Script | Backend | Requires |
|---|---|---|
| `smartrevisor_ollama.py` | Local Ollama | Ollama running with a model pulled |
| `smartrevisor_openrouter.py` | OpenRouter API | Free API key from openrouter.ai |
| `smartrevisor_gemini.py` | Google Gemini | Free API key from aistudio.google.com |

## Setup

### 1. Configure your chosen script

Open the script and edit the config section at the top:

**Ollama:**
```python
OLLAMA_URL   = "http://localhost:11434/api/generate"  # Your Ollama instance IP
OLLAMA_MODEL = "llama3.1:8b"                          # Any pulled Ollama model
```

**OpenRouter:**
```python
OPENROUTER_KEY   = "YOUR_OPENROUTER_KEY_HERE"
OPENROUTER_MODEL = "openrouter/free"  # Or a specific free model
```

**Gemini:**
```python
GEMINI_KEY   = "YOUR_GEMINI_API_KEY_HERE"
GEMINI_MODEL = "gemini-2.0-flash"
```

### 2. Pull a model (Ollama only)

```bash
ollama pull llama3.1:8b
```

### 3. Launch Chrome with debugging enabled

**Windows:**
```cmd
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chromedev" --start-maximized
```

**macOS:**
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chromedev
```

**Linux:**
```bash
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chromedev
```

### 4. Run

```bash
python NeuralRevise_ollama.py
# or
python NeuralRevise_openrouter.py
# or
python NeuralRevise_gemini.py
```

Log into your target platform in the Chrome window that opens, then press Enter in the terminal as instructed.

## Findings

### Bot detection
Cloudflare's managed challenge successfully blocked all standard Playwright browser launches regardless of stealth patching. The only reliable bypass was attaching to an existing authenticated Chrome session via CDP, which presents genuine browser fingerprints indistinguishable from a real user.

### LLM accuracy
Tested with `llama3.1:8b` against OCR A-level Computer Science MCQ questions:

| Topic area | Accuracy |
|---|---|
| Boolean logic | ~90% |
| Hardware and architecture | ~80% |
| Databases and SQL | ~85% |
| Software methodology | ~65% |
| Data structures | ~80% |
| Programming concepts | ~85% |

Accuracy drops on methodology questions (Agile/Waterfall/Spiral) where answer options are nuanced. Short numeric answers caused index-matching issues with naive string matching, but is resolved with exact match priority in the answer selection logic. 

You can set a smarter model to train on the subset of questions; however, the bot has to be wrong only once, as it saves the correct answer into `learned.json`.

### Adaptive memory
After a full run through the question bank, the agent answered over 95% of questions from memory with near-instant response times, only falling back to LLM inference for newly encountered questions.

### Performance
- Local Ollama on CPU (i7-7700): ~20-30 seconds per LLM call
- OpenRouter free tier: ~1-2 seconds but 200 requests/day limit
- Google Gemini free tier: ~1-2 seconds, 1500 requests/day limit
- Memory hits: near-instant (~2 second delay to avoid rate limiting)

## Limitations

- Requires a real Chrome session as headless mode is detected and blocked by Cloudflare
- LLM inference on CPU is slow, GPU acceleration via Ollama significantly improves speed
- Free tier API alternatives have daily rate limits unsuitable for high-volume runs
- Knowledge base is platform and course-specific; `learned.json` does not transfer between different courses
- All was tested via Windows VM & AI model containerised in an LXC container. May not work with all systems. 

## Disclaimer

This project is intended for research and educational purposes, exploring autonomous agent behaviour, LLM performance benchmarking, and real-world bot detection mechanisms. 

## Author

Jack Ghafari - [jackghx.com](https://jackghx.com)
