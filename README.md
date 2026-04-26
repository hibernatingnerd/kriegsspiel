# Kriegsspiel

> **AI-powered wargame simulation platform — designed for rapid national security scenario analysis and strategy development**  
> _Developed at the SCSP 2026 National Security Technology Hackathon_

---

**Kriegsspiel** (German for "war game") is an open-source, modular simulation platform that fuses deterministic wargame engines with generative AI to deliver realistic, explainable, and autonomously adjudicated scenario outcomes. Born from the need to rapidly assess competitive strategies in complex operational environments, Kriegsspiel uniquely blends a rules-based state engine (for rigor and reproducibility) with a language model "Red Cell" (for creative and adaptive adversary play) — all with no need for a human umpire.

The result is a next-generation wargaming tool for researchers, analysts, and strategists seeking:

- **Fast and unbiased scenario resolution:** No more slow, inconsistent, or manually umpired games.
- **AI-driven adversarial play:** Simulate real-world opponents with dynamic, model-generated moves.
- **Transparency and auditability:** All state transitions, LLM prompts, and adjudications are logged, replayable, and easy to analyze.
- **Modularity and extensibility:** Swap in new scenarios, models, and rule sets with minimal friction.

---

## Why Kriegsspiel?

In defense, policy, and cyber domains, wargaming has always been a critical tool for exploring tactics and anticipating adversary strategies. Traditional methods, however, are time-consuming, require expert human umpires, and often lack rigorous reproducibility.

Kriegsspiel addresses these pain points through automation, audit-logging, and a modular design, empowering users to:

- **Test "what-if" scenarios at scale:** Instantly re-run scenarios with different assumptions, forces, or environment factors.
- **Stress-test AI models under adversarial pressure:** Evaluate LLMs as autonomous actors in procedurally complex games.
- **Educate and prototype:** Accelerate learning by letting students or analysts build, modify, and re-run scenarios with immediate feedback.

---

## Architecture Overview

The codebase is organized for modularity and clarity, separating scenario logic, UI/UX, and AI integration:

```
kriegsspiel/
├── backend/                  # Python API — scenario logic, Anthropic Claude LLM integration, game adjudication
├── dashboard/                # TypeScript/React frontend — live scenario setup, visualization, audit history
└── deterministic state engine/  # Core Python module — ruleset encoding, state transitions, and audit logs
```

### How the Platform Works

**1. Deterministic State Engine**  
Encapsulates the core mechanics: order classes, turn phases, terrain, force structure, and rules of engagement. All moves, transitions, and outcomes are fully deterministic and transparent, ensuring reproducibility, fairness, and auditability. This is the engine that guarantees "if you run the same scenario twice, you get the exact same outcome, step by step."

**2. Backend with LLM Integration**  
The backend is a Python service that:
- Orchestrates gameplay between blue (human or model-controlled) and red (LLM-controlled) teams.
- Integrates with Anthropic Claude via API: The LLM acts as the adversary, generating Red Cell decisions and providing rich narrative adjudications of ambiguity, partial observability, and chance events.
- Manages scenario state, validates orders, and exposes an API to the frontend.

**3. Dashboard Frontend**  
A user-friendly, real-time visualization tool built with React/TypeScript:
- Enables scenario setup, team assignments, and live play/refereeing.
- Provides graphical turn tracking, operational maps (if present), and a timeline of moves and adjudications.
- Lets users review detailed logs, replay games, or export data for analysis.
- Designed for both in-person demos and remote "distributed umpire" sessions.

---

## Example Workflow

1. **Start the backend** to host the engine and AI integration (Python).
2. **Launch the dashboard** for scenario setup, team play, and visualization (Node/React).

The platform can be configured to support:
- Human vs. Model (user vs. AI)
- Human vs. Human (classic)
- Model vs. Model (automated competitive wargaming)

All moves, AI prompts, and results are logged for post-hoc review — ideal for scientific analysis, training, or after-action reporting.

---

## Prerequisites

| Component   | Version         | Purpose                                       |
| ----------- | --------------- | --------------------------------------------- |
| Python      | 3.10+           | Backend API, state engine, game logic         |
| Node.js     | 18+             | Dashboard (React frontend)                    |
| Anthropic API key | (free or paid) | For accessing Claude as autonomous adversary  |

*Other LLM providers can be integrated in the future or by forking the backend.*

---

## Setup Guide

### 1. Clone the repository

```bash
git clone https://github.com/hibernatingnerd/kriegsspiel.git
cd kriegsspiel
```

### 2. Set up environment variables

The backend requires your Anthropic API key to access Claude.  
Copy the example environment file and patch in your credentials:

```bash
cp .env.example .env
# Edit .env and insert your Anthropic API key
```

`.env.example`:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 3. Install & start the backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

- The backend will start serving a REST API for state transitions and LLM interaction.

### 4. Install & run the dashboard

In a new terminal:

```bash
cd dashboard
npm install
npm run dev
```

- By default, the dashboard is served at `http://localhost:3000`

---

## Usage Guide

Open your browser and go to `http://localhost:3000`.

From the dashboard you can:

- **Load or design new scenarios:** Define force compositions, rules of engagement, win conditions, and fog-of-war parameters.
- **Assign players:** Play as BLUE (human or model), with CLAUDE as adversary RED CELL.
- **Step through turns:** Submit orders for your side; the Red Cell LLM will evaluate the situation and return plausible adversary actions.
- **See live adjudication:** The platform narrates how orders are resolved, highlighting both deterministic outcomes and LLM-influenced decisions (including edge cases or ambiguous events).
- **Review logs:** Access the complete move-by-move audit trail, replay games, and export adjudication transcripts for reporting or research.

**Adapt the engine:**  
- Power users can author new rulesets, force types, and operational constraints by extending the core state engine.  
- Bring-your-own-model: The LLM interface in the backend is modular; swap in your own agent for scientific comparisons or research.

---

## Real-World Applications

- **Defense & policy:** Model adversary reactions in contingency planning without classified data.
- **AI Red Teaming:** Robustly test AI agents under adversarial and complex operational conditions.
- **Education & training:** Hands-on tool for students and professionals to learn wargame mechanics and strategy under uncertainty.
- **Research & prototyping:** Evaluate new rulesets, force compositions, AI models, or scenario templates with immediate feedback and full logging.

---

## Team & Hackathon Context

Built during the [SCSP 2026 National Security Technology Hackathon](https://expo.scsp.ai/hackathon/) — bringing together top engineers, designers, strategists, and defense experts from academia, industry, and government to prototype AI-driven solutions for critical security challenges.

- **Team roles:** AI/LLM integration, game design, UX/design, backend architecture, scenario development, test & evaluation.
- **Philosophy:** Open-source (MIT), reproducible science, community extensible — designed for rapid research and iteration.

---

## License

[MIT](LICENSE)  
Use, modify, or extend as you wish — attribution appreciated!

---

## Further Reading & References

- [Kriegsspiel (Chess Variant) — Wikipedia](https://en.wikipedia.org/wiki/Kriegsspiel)
- [Anthropic Claude API Documentation](https://docs.anthropic.com/)
- [SCSP Hackathon](https://expo.scsp.ai/hackathon/)
- [Wargaming in Defense — RAND Corporation](https://www.rand.org/topics/wargaming.html)
- [James Ryseff — RAND Corporation Author Page](https://www.rand.org/pubs/authors/r/ryseff_james.html)

---

## Feedback, Bugs, and Contributions

We welcome issues, feature requests, and pull requests! Please file bugs directly in [GitHub Issues](https://github.com/hibernatingnerd/kriegsspiel/issues).

---

> _Kriegsspiel is a research prototype. Please use responsibly and adhere to ethical AI development principles._
