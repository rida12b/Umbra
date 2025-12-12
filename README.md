<p align="center">
  <img src="https://raw.githubusercontent.com/rida12b/Umbra/main/.github/assets/logo.png" alt="Umbra Logo" width="120">
</p>

<h1 align="center">🌑 Umbra</h1>

<p align="center">
  <strong>The Shadow Architect</strong><br>
  AI-powered architecture diagrams that update in real-time as you code.
</p>

<p align="center">
  <a href="https://pypi.org/project/umbra-architect/"><img src="https://img.shields.io/pypi/v/umbra-architect?color=blue&label=PyPI" alt="PyPI"></a>
  <a href="https://pypi.org/project/umbra-architect/"><img src="https://img.shields.io/pypi/dm/umbra-architect?color=green" alt="Downloads"></a>
  <a href="https://github.com/rida12b/Umbra/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License"></a>
  <a href="https://github.com/rida12b/Umbra/stargazers"><img src="https://img.shields.io/github/stars/rida12b/Umbra?style=social" alt="Stars"></a>
</p>

<p align="center">
  <a href="#-the-problem">Problem</a> •
  <a href="#-the-solution">Solution</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#-demo">Demo</a>
</p>

---

## 😰 The Problem

You're using **Cursor**, **Copilot**, or **ChatGPT** to write code faster than ever. But there's a catch:

> **You no longer understand your own codebase.**

- Documentation is always outdated
- Architecture diagrams are lies
- New team members are lost
- You forgot what that service does

## 💡 The Solution

**Umbra** watches your code and maintains a **living architecture diagram** that updates automatically.

```
Save file → Umbra detects → AI analyzes → Diagram updates
```

No more manual documentation. No more outdated diagrams. Just code.

## 🚀 Quick Start

### 1. Install

```bash
pip install umbra-architect
```

### 2. Configure

Get a free API key from [Google AI Studio](https://aistudio.google.com/apikey), then:

```bash
# Set your API key
export GOOGLE_API_KEY="your-api-key"

# Or create a .env file in your project
echo "GOOGLE_API_KEY=your-api-key" > .env
```

### 3. Run

```bash
cd your-project
umbra watch .
```

That's it! Open `output/LIVE_ARCHITECTURE.md` to see your architecture.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 **Knowledge Base** | `UMBRA_KNOWLEDGE.md` - Single file = Full project context for any LLM |
| 🔍 **Smart Analysis** | AI understands semantic changes, not just syntax |
| 📊 **Live Diagrams** | Mermaid.js diagrams update in real-time |
| 💬 **Ask Umbra** | Chat with your codebase in natural language |
| 🏥 **Health Score** | Get an A-F grade for your architecture |
| ⚠️ **Auto Insights** | Detect god files, high coupling, issues |
| 🔐 **Security Scan** | Auto-detect vulnerabilities (SQL injection, secrets, etc.) |
| 📚 **Auto-Docs** | Generate module documentation automatically |
| 🎨 **Modern Dashboard** | Beautiful glassmorphism UI with Bento grid |
| 📝 **Auto Summary** | Natural language project description |
| 🕐 **Recent Changes** | AI-powered descriptions with detailed diffs |
| 🔎 **Search (Ctrl+K)** | Command palette to search your codebase |
| 📥 **SVG Export** | Download diagrams in vector format |
| 🐍 **Python Support** | Full Python codebase analysis |
| ⚛️ **JS/TS Support** | React, Next.js, Express, and more |

## 🎬 Demo

### Before: 40 files, no clue what's happening

```
my-project/
├── src/
│   ├── services/
│   │   ├── auth.py
│   │   ├── payments.py
│   │   ├── notifications.py
│   │   └── ...20 more files
│   ├── api/
│   └── utils/
└── ???
```

### After: Clear architecture in seconds

```mermaid
graph LR
    subgraph Core["Core Services"]
        API[API Gateway]
        Auth[Authentication]
        Payments[Payments]
    end
    
    subgraph External["External APIs"]
        Stripe[Stripe]
        Firebase[Firebase Auth]
    end
    
    subgraph Data["Data Stores"]
        DB[(PostgreSQL)]
    end
    
    API --> Auth
    API --> Payments
    Auth --> Firebase
    Payments --> Stripe
    Payments --> DB
```

Plus a human-readable summary:

> **Type:** FastAPI Backend  
> **Stack:** Python, PostgreSQL, Stripe, Firebase  
> **What it does:** E-commerce API with authentication and payment processing

## 📖 Commands

| Command | Description |
|---------|-------------|
| `umbra watch .` | 🚀 **All-in-one**: Scan + Docs + Security + Watch + Chat Server + Dashboard |
| `umbra watch . --open` | Same as above, auto-opens dashboard in browser |
| `umbra watch . --no-scan` | Skip initial scan, only watch for changes |
| `umbra watch . --no-docs` | Skip module documentation generation |
| `umbra watch . --no-security` | Skip security vulnerability scan |
| `umbra ask` | 💬 Chat with your codebase (interactive) |
| `umbra ask -q "How does auth work?"` | Ask a single question |
| `umbra insights` | 🏥 Show health score & issues |
| `umbra dashboard report.html` | 🎨 Export stunning HTML dashboard |
| `umbra scan .` | One-time full scan (no watch) |
| `umbra export report.html` | Simple HTML export |

### Output Files

| File | Purpose |
|------|---------|
| `output/LIVE_ARCHITECTURE.md` | Architecture diagram + recent changes |
| `output/UMBRA_KNOWLEDGE.md` | **Full project brain** - Everything an LLM needs |
| `output/dashboard.html` | Interactive visualization dashboard |

## 🛠️ Configuration

Create a `.env` file in your project:

```env
GOOGLE_API_KEY=your-api-key
GEMINI_MODEL=models/gemini-flash-latest
OUTPUT_FILE=./output/LIVE_ARCHITECTURE.md
DEBOUNCE_SECONDS=2
```

## 🤔 How It Works

1. **Watch** - Monitors your files for changes (Python, JS, TS)
2. **Analyze** - AI determines if the change is structural or cosmetic
3. **Update** - Only structural changes update the diagram
4. **Visualize** - Mermaid diagram renders in VS Code or browser

### What's "structural"?

| ✅ Updates Diagram | ❌ Ignored |
|-------------------|-----------|
| New service class | Renaming variables |
| External API call | Adding comments |
| Database connection | Formatting code |
| Inter-service communication | Test files |

## 🗺️ Roadmap

### Current (v0.6) - "Second Brain" Release
- [x] Python support
- [x] JavaScript/TypeScript support
- [x] Project summaries
- [x] HTML export
- [x] **Ask Umbra** - Chat with your codebase
- [x] **Health Score** - Architecture quality grading
- [x] **Insights** - Automatic issue detection
- [x] **Modern Dashboard** - Glassmorphism UI with Bento grid
- [x] **Hybrid Mode** - Watch + Chat server + Auto-refresh
- [x] **Recent Changes** - AI-powered change tracking with detailed diffs
- [x] **Search (Ctrl+K)** - Command palette search
- [x] **SVG Export** - Download diagrams
- [x] **Knowledge Base** - `UMBRA_KNOWLEDGE.md` = Full project brain for LLMs
- [x] **Auto-Documentation** - Module docs generated automatically
- [x] **Security Scanner** - Detect vulnerabilities automatically
- [x] **API Reference** - Auto-generated function/class reference

### Coming Soon
- [ ] **Intent Detection** - Classify changes as Bug Fix / Feature / Refactor
- [ ] **Session Timeline** - Chronological view of coding sessions
- [ ] **Quality Monitoring** - Track code metrics over time
- [ ] **Pattern Detection** - Detect AI assistant patterns
- [ ] **Git Integration** - AI analysis alongside git diff
- [ ] VS Code extension
- [ ] CI/CD integration (generate on PR)
- [ ] More languages (Go, Rust, Java)
- [ ] Click on diagram nodes to view file

### Future Vision
- [ ] **Rollback Warnings** - "This change broke X tests"
- [ ] **Dependency Alerts** - "New dependency added"
- [ ] **Team Collaboration** - Share architecture across team

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Clone
git clone https://github.com/rida12b/Umbra.git
cd Umbra

# Install
poetry install

# Test
poetry run pytest
```

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Stop documenting. Start understanding.</strong>
</p>

<p align="center">
  <a href="https://github.com/rida12b/Umbra">⭐ Star us on GitHub</a>
</p>
