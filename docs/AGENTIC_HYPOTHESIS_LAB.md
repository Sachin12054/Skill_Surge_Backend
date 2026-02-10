# Agentic Hypothesis Lab 🤖

## Tool-Using Multi-Agent System for Research Hypothesis Generation

The Hypothesis Lab now supports **two modes**:

### 1. **Standard Mode** (Fast, Simple)
- Single LLM calls with prompt chaining
- ~30-60 seconds per generation
- Good for quick hypothesis brainstorming

### 2. **Agentic Mode** (Advanced, Autonomous) ✨
- Multi-agent system with specialized roles
- Each agent can use external tools
- Autonomous research validation
- ~2-5 minutes per generation

---

## 🤖 Agent Architecture

```
┌─────────────────────────────────────────────────────┐
│              Supervisor (Router)                     │
│  Routes between agents based on workflow state       │
└─────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Research   │  │   Analyzer   │  │  Generator   │
│    Agent     │  │    Agent     │  │    Agent     │
└──────────────┘  └──────────────┘  └──────────────┘
        ▼                 ▼                 ▼
┌──────────────────────────────────────────────────────┐
│                  Critic Agent                        │
│         Final validation and scoring                 │
└──────────────────────────────────────────────────────┘
```

### **Research Agent** 🔬
**Tools:** ArXiv, Semantic Scholar, Novelty Checker

**Responsibilities:**
- Search for related academic papers
- Check if hypotheses are truly novel
- Find gaps in existing literature
- Verify no prior research exists

**Example Tool Use:**
```python
# Agent autonomously decides to check novelty
search_semantic_scholar("neural plasticity in deep learning")
check_hypothesis_novelty("Combining attention mechanisms with Hebbian learning")
```

### **Analyzer Agent** 🧠
**Tools:** Internal analysis (no external tools)

**Responsibilities:**
- Deep concept extraction from papers
- Identify key claims and findings
- Map methodologies used
- Build concept relationships

### **Generator Agent** 💡
**Tools:** Testability Scorer

**Responsibilities:**
- Generate 3-5 novel hypotheses
- Combine concepts creatively
- Validate each hypothesis for testability
- Refine based on tool feedback

**Example Tool Use:**
```python
# Agent validates each generated hypothesis
score_hypothesis_testability(
    hypothesis="Attention-based Hebbian learning improves transfer learning",
    methodology=["Controlled experiment", "A/B testing"]
)
```

### **Critic Agent** 🎯
**Tools:** Statistical Validator, Novelty Checker, Testability Scorer

**Responsibilities:**
- Rigorously evaluate all hypotheses
- Check for scientific validity
- Verify statistical claims
- Provide constructive feedback

**Example Tool Use:**
```python
# Agent performs multi-tool validation
validate_statistical_claim("95% accuracy improvement")
check_hypothesis_novelty(hypothesis_text)
analyze_research_feasibility(hypothesis, resources, timeframe)
```

---

## 🛠️ Available Tools

### Search Tools
| Tool | Purpose | Agent Use |
|------|---------|-----------|
| `search_arxiv` | Search ArXiv papers by keyword | Research Agent |
| `search_semantic_scholar` | Search with citation data | Research Agent, Critic |
| `find_related_concepts` | Discover related research terms | Research Agent |
| `check_hypothesis_novelty` | Verify uniqueness in literature | Research Agent, Critic |

### Validation Tools
| Tool | Purpose | Agent Use |
|------|---------|-----------|
| `execute_python_code` | Run statistical validation | Critic Agent |
| `validate_statistical_claim` | Check statistical assertions | Critic Agent |
| `score_hypothesis_testability` | Measure falsifiability | Generator, Critic |
| `analyze_research_feasibility` | Assess practical viability | Critic Agent |

---

## 📡 API Usage

### Enable Agentic Mode

```python
# Standard mode (default)
POST /api/v2/hypothesis/generate
{
  "paper_ids": ["uuid1", "uuid2"],
  "focus_area": "neural networks",
  "use_agentic": false  # Fast, simple
}

# Agentic mode (autonomous agents with tools)
POST /api/v2/hypothesis/generate
{
  "paper_ids": ["uuid1", "uuid2"],
  "focus_area": "neural networks",
  "use_agentic": true  # Slower, but more rigorous
}
```

### Response Includes Agent Activity

```json
{
  "hypotheses": [...],
  "agent_messages": [
    {"role": "research_agent", "content": "Found 5 related papers on ArXiv"},
    {"role": "generator_agent", "content": "Generated 3 hypotheses with tool validation"},
    {"role": "critic_agent", "content": "Validated all hypotheses using novelty checker"}
  ],
  "tool_results": {
    "research": {
      "completed": true,
      "tool_calls": 3,
      "findings": "Limited prior work combining these concepts"
    }
  }
}
```

---

## 🚀 Workflow Example

### User Request
> "Generate hypotheses about combining transformers with reinforcement learning"

### 1. Research Agent Activates
```
🔬 Research Agent: "Searching for related work..."
   Tool: search_arxiv("transformers reinforcement learning")
   Result: Found 12 papers
   
   Tool: check_hypothesis_novelty("Transformer-based policy networks")
   Result: Novelty score 0.6 - some existing work
```

### 2. Analyzer Agent Processes Papers
```
🧠 Analyzer Agent: "Extracting concepts..."
   Extracted: 15 concepts, 8 claims
   Identified methodologies: PPO, Actor-Critic, Attention mechanisms
```

### 3. Generator Agent Creates Hypotheses
```
💡 Generator Agent: "Generating 3 hypotheses..."
   Hypothesis 1: "Multi-head attention in value networks improves sample efficiency"
   
   Tool: score_hypothesis_testability(hypothesis_1)
   Result: 0.82 - Highly testable
   
   Refined hypothesis based on feedback
```

### 4. Critic Agent Validates
```
🎯 Critic Agent: "Evaluating hypotheses..."
   
   Tool: check_hypothesis_novelty(hypothesis_1)
   Result: Novelty 0.85 - Highly novel
   
   Tool: validate_statistical_claim("sample efficiency improvement")
   Result: Valid - testable claim
   
   Final score: 0.81/1.0 - Approved
```

---

## 🆚 Mode Comparison

| Feature | Standard Mode | Agentic Mode |
|---------|--------------|--------------|
| **Speed** | 30-60s | 2-5 min |
| **Novelty Check** | LLM inference | Real paper search |
| **Validation** | Prompt-based | Tool-based verification |
| **Research Depth** | Surface-level | Deep literature review |
| **Autonomy** | Scripted | Self-directed |
| **Cost** | Lower | Higher (more API calls) |
| **Best For** | Quick ideation | Rigorous research |

---

## 🔧 Installation

### 1. Install Dependencies
```bash
cd backend
pip install langchain-openai arxiv scipy httpx
```

### 2. Verify Tools Work
```python
from app.agents.tools import search_arxiv, check_hypothesis_novelty

# Test ArXiv search
papers = search_arxiv.invoke({"query": "machine learning", "max_results": 3})
print(f"Found {len(papers)} papers")

# Test novelty checker
result = check_hypothesis_novelty.invoke({
    "hypothesis": "Deep learning for climate prediction"
})
print(f"Novelty score: {result['novelty_score']}")
```

### 3. Use Agentic Mode
```bash
# Start backend
uvicorn app.main:app --reload

# Test agentic endpoint
curl -X POST http://localhost:8000/api/v2/hypothesis/generate \
  -H "Content-Type: application/json" \
  -d '{
    "paper_ids": ["your-paper-id"],
    "focus_area": "your research area",
    "use_agentic": true
  }'
```

---

## 🎯 Next Enhancements

- [ ] Add **AWS Bedrock** support (Claude 3.5 for better reasoning)
- [ ] Implement **ReAct prompting** for better tool selection
- [ ] Add **Neo4j integration** for knowledge graph reasoning
- [ ] Support **streaming responses** to show agent activity live
- [ ] Add **Letta memory** for user preference learning
- [ ] Implement **human-in-the-loop** approval for hypotheses

---

## 📚 Architecture Details

### LangGraph Workflow
```python
StateGraph
├── START → research_agent
├── research_agent → supervisor_router
│   └── → analyzer_agent
├── analyzer_agent → supervisor_router
│   └── → generator_agent
├── generator_agent → supervisor_router
│   └── → critic_agent
└── critic_agent → END
```

### Tool Invocation Pattern
Each agent uses LangChain's `create_react_agent`:
- Receives task description
- **Autonomously decides** which tools to use
- Executes tools
- Reasons about results
- Returns findings

### Example Agent Decision Loop
```
Agent: "I need to check if this hypothesis is novel"
  → Thinks: "I should search existing papers"
  → Action: search_semantic_scholar("hypothesis text")
  → Observes: Found 2 similar papers with 50 citations
  → Thinks: "Moderate existing work, novelty = 0.6"
  → Returns: Novelty assessment
```

---

## 🐛 Troubleshooting

### Tools Not Working
```bash
# Verify arxiv package
python -c "import arxiv; print('ArXiv OK')"

# Test Semantic Scholar API
curl "https://api.semanticscholar.org/graph/v1/paper/search?query=test"
```

### Agentic Mode Timeout
Increase timeframe in frontend:
```typescript
// mobile-app/app/hypothesis/generate.tsx
await new Promise(resolve => setTimeout(resolve, 5000)); // Increase to 5s
```

### Agent Stuck in Loop
Check supervisor routing logic in `hypothesis_agent_agentic.py`:
```python
def supervisor_router(state):
    # Add max iteration check
    if state.get("iteration", 0) > 10:
        return "END"
```

---

## 📊 Metrics & Monitoring

Track agent performance:
```python
{
  "tool_results": {
    "research": {
      "tool_calls": 3,
      "duration_ms": 2500,
      "papers_found": 5
    }
  },
  "agent_messages": [...],  # Full conversation log
  "total_duration_ms": 45000
}
```

---

**The Hypothesis Lab is now truly agentic** - agents autonomously search papers, validate claims, and reason about research gaps using real tools! 🎉
