# 🛡️ OpsGuard — Architecture Overview

> **Autonomous Infrastructure Agent** — Self-healing ops powered by LLM decision-making.
> 
> *This document covers Phases 0–3. More phases incoming.*

---

## High-Level Vision

```mermaid
graph LR
    subgraph "💥 Chaos Engine"
        C[chaos.py]
    end

    subgraph "🐳 Docker Environment"
        W[web-prod<br/>Nginx]
        D[db-prod<br/>PostgreSQL]
        Z[Zombie Containers]
    end

    subgraph "👁️ Observer"
        O[observer.py]
    end

    subgraph "🧠 Agent Core"
        P[prompt.py] --> A[agent.py]
    end

    subgraph "🔧 Toolbox"
        S[safe.py]
        R[risky.py]
    end

    C -->|breaks| W
    C -->|breaks| D
    C -->|spawns| Z
    O -->|monitors| W
    O -->|monitors| D
    O -->|alerts| A
    A -->|uses| S
    A -->|uses| R
    S -->|fixes| W
    S -->|fixes| D
    R -->|restarts| D
    S -->|prunes| Z
```

---

## Phase Roadmap

```mermaid
gantt
    title OpsGuard Implementation Phases
    dateFormat X
    axisFormat %s

    section Phase 0
    Project Bootstrap & Docker Setup    :done, p0, 0, 1

    section Phase 1
    Web Log Saturation & Zombies        :done, p1, 1, 2

    section Phase 2
    DB Resilience & Negative Scenarios   :active, p2, 2, 3

    section Phase 3
    Chain Reactions & Verification       :p3, 3, 4

    section Phase 4+
    Coming Soon...                       :milestone, p4, 4, 4
```

---

## Project Structure

```
opsguard/
├── docker-compose.yml        # Container orchestration
├── app.py                    # Entrypoint — wires Observer + Agent
├── chaos.py                  # 💥 Fault injection engine
├── test_chain.py             # Manual chain-failure test (Phase 3)
│
├── core/
│   ├── agent.py              # 🧠 LangChain ReAct agent
│   └── prompt.py             # 📜 System prompt & decision rules
│
├── tools/
│   ├── safe.py               # 🔧 Low-risk tools (clean_logs, prune)
│   └── risky.py              # ⚠️  High-risk tools (restart_database)
│
├── utils/
│   ├── observer.py           # 👁️ System monitor & alarm producer
│   └── security.py           # 🔐 Human-approval decorator
│
└── logs/
    ├── web/                  # Nginx log volume
    └── db/                   # PostgreSQL log volume
```

---

## Phase 0 — Bootstrap

Basic Docker environment + initial wiring.

```mermaid
flowchart TD
    DC[docker-compose.yml] -->|starts| WP[web-prod — Nginx]
    DC -->|starts| DP[db-prod — PostgreSQL]
    APP[app.py] -->|initializes| AG[Agent]
    APP -->|initializes| OB[Observer]
```

---

## Phase 1 — Dynamic Observation & Smart Cleanup

**Focus:** Web server log bloat (Saturation, not Crash) + Zombie containers.

### Chaos Scenarios (Phase 1)

| Scenario | Target | Method | Severity |
|---|---|---|---|
| `fill_web_disk_trigger()` | `web-prod` | `dd` → 2GB garbage log | 🟡 Saturation |
| `create_zombie_containers(15)` | Host | 15× `alpine` exited | 🟠 Pollution |

### Observer Alarm Matrix (Phase 1)

```mermaid
flowchart TD
    OBS[Observer Loop<br/>every 30s] --> DISK{web-prod<br/>disk > 85%?}
    OBS --> ZOMB{Exited containers<br/>> 5?}

    DISK -->|Yes| A1["🟡 WEB_LOG_SATURATION<br/>Logs bloated!"]
    DISK -->|No| OK1[✅ OK]

    ZOMB -->|Yes| A2["🟠 ZOMBIE_OUTBREAK<br/>Dead containers!"]
    ZOMB -->|No| OK2[✅ OK]

    A1 --> AGENT[🧠 Agent]
    A2 --> AGENT

    AGENT -->|clean_logs web-prod| FIX1[Truncate logs]
    AGENT -->|prune_containers| FIX2[Docker system prune]
```

### Agent Decision Flow (Phase 1)

```mermaid
sequenceDiagram
    participant C as 💥 Chaos
    participant W as 🐳 web-prod
    participant O as 👁️ Observer
    participant A as 🧠 Agent

    C->>W: fill_web_disk_trigger() — 2GB garbage
    O->>W: df -h → 92% full
    O->>A: 🟡 WEB_LOG_SATURATION
    A->>W: clean_logs('web-prod')
    W-->>A: ✅ Disk now 12%
    Note over A: Done. No crash, just maintenance.
```

---

## Phase 2 — DB Resilience & Negative Scenarios

**Focus:** Teach the Agent to distinguish **fixable** vs **unfixable** database failures.

### Chaos Scenarios (Phase 2)

| # | Scenario | Target | Fixable? | Expected Agent Behavior |
|---|---|---|---|---|
| 1 | `trigger_db_garbage_flood()` | `db-prod` `/root/` | ❌ No | Clean → Fail → **STOP** |
| 2 | `trigger_config_corruption()` | `db-prod` conf | ❌ No | Report → **STOP** |
| 3 | `trigger_oom_kill()` | `db-prod` | ✅ Yes | `restart_database_risky` |
| 4 | `trigger_data_corruption()` | `db-prod` data | ❌ No | Report → **STOP** |

### Observer — Root Cause Tagging

```mermaid
flowchart TD
    CHK[check_database] --> STATUS{db-prod<br/>running?}

    STATUS -->|Running| NOOP["✅ No alarm<br/>(self-healed)"]
    STATUS -->|Exited / Stopped| LOGS[Read last 2min logs<br/>+ ExitCode]

    LOGS --> TAG1{"'No space left'<br/>in logs?"}
    LOGS --> TAG2{"'configuration file'<br/>in logs?"}
    LOGS --> TAG3{ExitCode == 137?}
    LOGS --> TAG4{"'checksum' or 'panic'<br/>in logs?"}

    TAG1 -->|Yes| D1["🔴 DB_CRASH<br/>Disk Full!"]
    TAG2 -->|Yes| D2["🔴 DB_CRASH<br/>Config Error!"]
    TAG3 -->|Yes| D3["🔴 DB_CRASH<br/>OOM Killer!"]
    TAG4 -->|Yes| D4["🔴 DB_CRASH<br/>DATA CORRUPTION!"]

    TAG1 -->|No| TAG2
    TAG2 -->|No| TAG3
    TAG3 -->|No| TAG4
    TAG4 -->|No| D5["🔴 DB_CRASH<br/>Unknown"]
```

### Agent Decision Tree (Phase 2)

```mermaid
flowchart TD
    ALARM["🔴 DB_CRASH Alarm"] --> TYPE{Root Cause?}

    TYPE -->|Disk Full| CL["clean_logs('db-prod')"]
    TYPE -->|OOM Kill| RS["restart_database_risky()"]
    TYPE -->|Config Error| STOP1["🛑 STOP<br/>Manual intervention needed"]
    TYPE -->|Data Corruption| STOP2["🛑 STOP<br/>Manual intervention needed"]

    CL --> RESULT{clean_logs<br/>output?}
    RESULT -->|"✅ SUCCESS<br/>Disk < 80%"| RS
    RESULT -->|"❌ FAIL<br/>Disk still > 80%"| STOP3["🛑 STOP<br/>Non-log data blocking disk"]

    RS --> APPROVAL{👤 Human<br/>Approval?}
    APPROVAL -->|Approved| RESTART["docker restart db-prod"]
    APPROVAL -->|Rejected| STOP4["🛑 Operation Cancelled"]
```

### Human Approval Gate

```mermaid
sequenceDiagram
    participant A as 🧠 Agent
    participant UI as 💬 Chainlit UI
    participant H as 👤 Human
    participant D as 🐳 db-prod

    A->>UI: "I want to run restart_database_risky()"
    UI->>H: ⚠️ Approve / Reject?
    H-->>UI: ✅ Approve
    UI-->>A: Go ahead
    A->>D: docker restart db-prod
    D-->>A: Container restarted
    A->>UI: "DB restored successfully."
```

---

## Phase 3 — Chain Reactions & Autonomous Verification

**Focus:** Multi-step remediation. Agent doesn't stop after one fix — it **verifies** and continues.

### Chain Failure Scenario

```mermaid
sequenceDiagram
    participant C as 💥 Chaos
    participant D as 🐳 db-prod
    participant O as 👁️ Observer
    participant A as 🧠 Agent
    participant H as 👤 Human

    C->>D: Write 3GB to /var/log/postgres_crash.log
    Note over D: Disk → 100%
    C->>D: docker stop db-prod
    Note over D: Status → Exited

    O->>O: Detect disk full + DB down
    O->>A: 🔴 DB_CRASH — Disk Full!

    A->>A: Step 1 — Clean first, restart later
    A->>D: clean_logs('db-prod')
    D-->>A: ✅ SUCCESS — Disk now 15%

    A->>A: Step 2 — Disk OK, but DB still down!
    A->>A: Plan restart

    A->>H: ⚠️ Approve restart_database_risky?
    H-->>A: ✅ Approved

    A->>D: docker restart db-prod
    D-->>A: Container running

    O->>O: Rapid check (2s interval)
    O->>A: ✅ db-prod is Running

    A->>A: Step 3 — Verified. All clear.
    A->>H: ✅ "Issue fully resolved."
```

### Rapid Check Mechanism

```mermaid
stateDiagram-v2
    [*] --> Normal: check_interval = 30s
    Normal --> RapidMode: trigger_rapid_check()
    RapidMode --> RapidMode: check_interval = 2s
    RapidMode --> Normal: After 60s timeout
    
    note right of RapidMode
        Used after Agent performs
        a fix — get instant feedback
    end note
```

### Verification Protocol

```mermaid
flowchart LR
    FIX["🔧 Agent runs<br/>a tool"] --> VERIFY{"Service<br/>running?"}
    VERIFY -->|No| NEXT["Plan next<br/>action"]
    VERIFY -->|Yes| DONE["✅ Fully<br/>resolved"]
    NEXT --> FIX
```

> **Key Rule:** Never send "Final Answer" until the root service is confirmed **Running**.

---

## Tool Inventory

| Tool | File | Risk | Approval | Phase |
|---|---|---|---|---|
| `clean_logs(container)` | `safe.py` | 🟢 Safe | No | 1 |
| `prune_containers(reason)` | `safe.py` | 🟢 Safe | No | 1 |
| `restart_database_risky(reason)` | `risky.py` | 🔴 Risky | ✅ Required | 2 |

---

## Alarm Catalog

| Alarm Code | Source | Severity | Auto-Fixable | Phase |
|---|---|---|---|---|
| `WEB_LOG_SATURATION` | Observer → disk | 🟡 Warning | ✅ `clean_logs` | 1 |
| `ZOMBIE_OUTBREAK` | Observer → docker | 🟠 Warning | ✅ `prune_containers` | 1 |
| `DB_CRASH — Disk Full` | Observer → logs | 🔴 Critical | ⚠️ Conditional | 2 |
| `DB_CRASH — OOM Killer` | Observer → exit code | 🔴 Critical | ✅ `restart_database` | 2 |
| `DB_CRASH — Config Error` | Observer → logs | 🔴 Critical | ❌ Manual only | 2 |
| `DB_CRASH — Data Corruption` | Observer → logs | 🔴 Critical | ❌ Manual only | 2 |

---

## Docker Topology

```mermaid
graph TB
    subgraph "Host Machine"
        subgraph "Docker Engine"
            WP["🌐 web-prod<br/>nginx:alpine<br/>restart: always<br/>:8080 → :80"]
            DP["🗄️ db-prod<br/>postgres:13-alpine<br/>restart: no<br/>shm: 64mb"]
            Z1["💀 zombie-1<br/>alpine<br/>Exited"]
            Z2["💀 zombie-2<br/>alpine<br/>Exited"]
            ZN["💀 ... ×15"]
        end

        subgraph "Volumes"
            V1["./logs/web"]
            V2["./logs/db"]
            V3["db-data"]
        end

        WP --- V1
        DP --- V2
        DP --- V3
    end

    subgraph "OpsGuard Agent Process"
        APP["app.py"]
        OBS["Observer"]
        AGT["Agent"]
        APP --> OBS
        APP --> AGT
    end

    OBS -.->|monitors| WP
    OBS -.->|monitors| DP
    AGT -.->|executes commands| WP
    AGT -.->|executes commands| DP
```

---

## What's Next? (Phase 4+)

```
🔮 Upcoming phases may include:
   • Multi-service dependency graphs
   • Predictive alerting (before failure)
   • Auto-scaling decisions
   • Incident post-mortem generation
   • ... and more chaos 💥
```

---

<sub>Generated for OpsGuard project — Architecture v0.3 (through Phase 3)</sub>
