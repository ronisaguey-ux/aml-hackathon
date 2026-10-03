"""
Benchmark Scenarios for AML Cycle 2 Leaderboard Evaluation.
Covers 66 scenarios across 6 core evaluation columns:
- Column C: Temporal State Updates & Tense Sensitivity (15 scenarios)
- Column G: Multi-Step Procedural Execution & Continuity (15 scenarios)
- Column B: Multi-Hop Relational Inference across Sessions (12 scenarios)
- Column D: Strict Rules & Constraints Preservation (8 scenarios)
- Column E: Streaming & Interleaved Incremental Events (8 scenarios)
- Column F: Governance, Evidence Boundaries & Negatives (8 scenarios)

Derived from public AML datasets: LoCoMo-Refined, PersonaMem, SWE, ScriptMem, BEAM, CLBench.
Includes 60+ realistic distractor templates for 50+ flood per scenario.
"""

from typing import List, Dict, Any

DISTRACTOR_TEMPLATES = [
    "Discussion on quarterly planning and roadmap milestones for the infrastructure squad.",
    "Reminder to review the open pull request for logging middleware cleanup.",
    "System alert: network latency increased by 15ms in us-east-1 during morning peak.",
    "Team lunch scheduled for Wednesday at 12:30 PM in the cafeteria annex.",
    "Summary of weekly retrospective meeting notes and action items for sprint 42.",
    "Please update your local dev environment with python 3.12 before next release.",
    "Reviewing latency graphs from the latest canary rollout on cluster beta-09.",
    "Security advisory regarding dependency version bumps in the authorization service.",
    "Discussion about refactoring the database connection pool configuration.",
    "Standup update: working on unit tests and property testing for the billing module.",
    "Team discussion about attending the upcoming open-source systems conference.",
    "The office espresso machine is being serviced this afternoon.",
    "Draft proposal for adopting structured JSON logging across all microservices.",
    "Notes from 1-on-1 meeting discussing Q4 professional development goals.",
    "Reminder: corporate travel expense reports are due by the 25th of this month.",
    "Investigation into intermittent DNS resolution timeouts on staging pods.",
    "Discussion regarding Prometheus metrics retention period and downsampling rules.",
    "Frontend team announced migration of icon assets to SVG sprite sheets.",
    "Hardware procurement ticket submitted for additional GPU development workstations.",
    "Vendor security questionnaire completed and returned to external audit team.",
    "Code review comments on the asynchronous event queue batching mechanism.",
    "Documentation updated for local Docker compose setup and environment variables.",
    "Alert: Disk usage exceeded 80% on build artifact storage node.",
    "Quarterly engineering all-hands presentation slides shared in team channel.",
    "Discussion on replacing Redis pub/sub with Kafka for cross-datacenter events.",
    "Customer feedback summary for the new dark mode theme in web portal.",
    "Database backup verification script ran successfully with zero checksum errors.",
    "Team brainstorming session on optimizing client-side bundle size.",
    "Reminder to complete the annual security compliance training module.",
    "Investigation into memory utilization patterns during batch CSV exports.",
    "Discussion about implementing OpenTelemetry tracing across internal gRPC calls.",
    "Product manager shared user research interview recordings for feedback.",
    "Kubernetes node auto-scaler threshold adjusted from 70% to 80% CPU target.",
    "Reviewing draft RFC for multi-tenant database partitioning strategy.",
    "Standup: pairing with Alex on debugging intermittent WebSocket disconnections.",
    "Security scan reported zero critical CVEs in current base container images.",
    "Discussion on migrating CI runner fleet from AWS EC2 to spot instances.",
    "Team retrospective highlighted need for better documentation on rollback procedures.",
    "Reminder: annual office holiday schedule posted on internal wiki.",
    "Discussion about standardizing error code formats across REST endpoints.",
    "Load test simulated 5,000 concurrent users against the checkout workflow.",
    "Meeting notes from architecture review board on micro-frontend boundaries.",
    "Investigation into slow Elasticsearch queries on customer audit log index.",
    "Design system team released v2.4 with improved accessibility contrast ratios.",
    "Standup: reviewing pull request for database index creation on user_sessions.",
    "Discussion on deprecating legacy v1 API endpoints by end of Q1.",
    "Incident post-mortem drafted for the 8-minute ingress controller blip.",
    "Engineering handbook updated with new guidelines for branch naming conventions.",
    "Team discussion about implementing rate limiting on the public signup endpoint.",
    "Automated end-to-end Cypress test suite completed in 4 minutes 12 seconds.",
    "Weekly sync with product operations regarding onboarding friction points.",
    "Reviewing cloud budget forecast and cost optimization opportunities for Q3.",
    "Notes from technical talk on distributed consensus and Raft implementations.",
    "Standup: waiting on code review for the Stripe webhook idempotency handler.",
    "Discussion about adding synthetic monitoring probes for critical checkout API.",
    "Reminder: laptop security update restart required before midnight Friday.",
    "Engineering book club selected 'Designing Data-Intensive Applications' for next month.",
    "Discussion on migrating internal documentation from Confluence to Markdown in git.",
    "Reviewing metrics dashboard for backend worker thread pool saturation.",
    "Team celebration planned for successful completion of SOC2 Type II audit."
]

def get_distractor_messages(count: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Generate count distractor messages from template pool with optional offset."""
    msgs = []
    total = len(DISTRACTOR_TEMPLATES)
    for i in range(count):
        idx = (offset + i) % total
        msgs.append({
            "role": "user",
            "content": f"[Background Note {i+1}] {DISTRACTOR_TEMPLATES[idx]}"
        })
    return msgs


SCENARIOS_COL_C_TEMPORAL: List[Dict[str, Any]] = [
    {
        "id": "temp_01_relocation",
        "category": "temporal",
        "user_id": "eval:harness:user_temp_01",
        "adds": [
            {
                "session_id": "sess_t01_a",
                "request_id": "req_t01_a",
                "messages": [
                    {"role": "user", "timestamp": 1704067200000, "content": "I am working as a frontend engineer in Berlin."}
                ]
            },
            {
                "session_id": "sess_t01_b",
                "request_id": "req_t01_b",
                "messages": [
                    {"role": "user", "timestamp": 1719835200000, "content": "Update: I moved to London and switched to systems programming."}
                ]
            }
        ],
        "query": "Where do I currently live and what is my role now?",
        "gold_contains": ["London", "systems programming"],
        "historical_contains": ["Berlin", "frontend engineer"],
        "expect_past": False
    },
    {
        "id": "temp_02_database_migration",
        "category": "temporal",
        "user_id": "eval:harness:user_temp_02",
        "adds": [
            {
                "session_id": "sess_t02_a",
                "request_id": "req_t02_a",
                "messages": [
                    {"role": "user", "timestamp": 1704067200000, "content": "Our main API database originally ran on PostgreSQL 14."}
                ]
            },
            {
                "session_id": "sess_t02_b",
                "request_id": "req_t02_b",
                "messages": [
                    {"role": "user", "timestamp": 1719835200000, "content": "We migrated the database service to ScyllaDB last month."}
                ]
            }
        ],
        "query": "What database did our main API originally run on before the migration?",
        "gold_contains": ["PostgreSQL 14"],
        "historical_contains": ["PostgreSQL 14"],
        "expect_past": True
    },
    {
        "id": "temp_03_no_timestamps_email",
        "category": "temporal",
        "user_id": "eval:harness:user_temp_03",
        "adds": [
            {
                "session_id": "sess_t03_a",
                "request_id": "req_t03_a",
                "messages": [
                    {"role": "user", "content": "My primary contact email is alex.dev@legacymail.org."}
                ]
            },
            {
                "session_id": "sess_t03_b",
                "request_id": "req_t03_b",
                "messages": [
                    {"role": "user", "content": "Correction: I updated my primary contact email to alex@quantumcore.io, please replace the old one."}
                ]
            }
        ],
        "query": "What is Alex's current active email address?",
        "gold_contains": ["alex@quantumcore.io"],
        "historical_contains": ["legacymail.org"],
        "expect_past": False
    },
    {
        "id": "temp_04_cloud_infrastructure",
        "category": "temporal",
        "user_id": "eval:harness:user_temp_04",
        "adds": [
            {
                "session_id": "sess_t04_a",
                "request_id": "req_t04_a",
                "messages": [
                    {"role": "user", "timestamp": 1700000000000, "content": "Our Kubernetes clusters were hosted on AWS us-east-1."}
                ]
            },
            {
                "session_id": "sess_t04_b",
                "request_id": "req_t04_b",
                "messages": [
                    {"role": "user", "timestamp": 1720000000000, "content": "Infrastructure announcement: We completed our cloud migration to GCP europe-west3."}
                ]
            }
        ],
        "query": "Which cloud provider and region currently hosts our primary Kubernetes cluster?",
        "gold_contains": ["GCP", "europe-west3"],
        "historical_contains": ["AWS", "us-east-1"],
        "expect_past": False
    },
    {
        "id": "temp_05_auth_standard_past",
        "category": "temporal",
        "user_id": "eval:harness:user_temp_05",
        "adds": [
            {
                "session_id": "sess_t05_a",
                "request_id": "req_t05_a",
                "messages": [
                    {"role": "user", "timestamp": 1690000000000, "content": "The application authentication token format was originally JWT with RS256 signatures."}
                ]
            },
            {
                "session_id": "sess_t05_b",
                "request_id": "req_t05_b",
                "messages": [
                    {"role": "user", "timestamp": 1715000000000, "content": "Security overhaul: Upgraded all session tokens to Paseto v4.local."}
                ]
            }
        ],
        "query": "What token format was previously used for session management before switching to Paseto?",
        "gold_contains": ["JWT with RS256"],
        "historical_contains": ["JWT with RS256"],
        "expect_past": True
    },
    {
        "id": "temp_06_salary_promotion",
        "category": "temporal",
        "user_id": "eval:harness:user_temp_06",
        "adds": [
            {
                "session_id": "sess_t06_a",
                "request_id": "req_t06_a",
                "messages": [
                    {"role": "user", "timestamp": 1680000000000, "content": "Maria joined as a Senior Software Engineer Level 4."}
                ]
            },
            {
                "session_id": "sess_t06_b",
                "request_id": "req_t06_b",
                "messages": [
                    {"role": "user", "timestamp": 1722000000000, "content": "Promotion announcement: Maria has been promoted to Principal Engineer Level 5."}
                ]
            }
        ],
        "query": "What is Maria's current title and engineering level?",
        "gold_contains": ["Principal Engineer", "Level 5"],
        "historical_contains": ["Senior Software Engineer", "Level 4"],
        "expect_past": False
    },
    {
        "id": "temp_07_frontend_stack_past",
        "category": "temporal",
        "user_id": "eval:harness:user_temp_07",
        "adds": [
            {
                "session_id": "sess_t07_a",
                "request_id": "req_t07_a",
                "messages": [
                    {"role": "user", "timestamp": 1675000000000, "content": "The customer web dashboard was originally built on Vue.js 2 with Webpack."}
                ]
            },
            {
                "session_id": "sess_t07_b",
                "request_id": "req_t07_b",
                "messages": [
                    {"role": "user", "timestamp": 1718000000000, "content": "Frontend rebuild: Customer dashboard has been rewritten in React 18 with Vite."}
                ]
            }
        ],
        "query": "What frontend framework did the customer dashboard originally employ before the rewrite?",
        "gold_contains": ["Vue.js 2"],
        "historical_contains": ["Vue.js 2"],
        "expect_past": True
    },
    {
        "id": "temp_08_deploy_cadence",
        "category": "temporal",
        "user_id": "eval:harness:user_temp_08",
        "adds": [
            {
                "session_id": "sess_t08_a",
                "request_id": "req_t08_a",
                "messages": [
                    {"role": "user", "timestamp": 1695000000000, "content": "Our release deployment cadence was manual bi-weekly releases on Tuesday mornings."}
                ]
            },
            {
                "session_id": "sess_t08_b",
                "request_id": "req_t08_b",
                "messages": [
                    {"role": "user", "timestamp": 1723000000000, "content": "DevOps update: Switched to continuous git-tag automated deploys triggered on push."}
                ]
            }
        ],
        "query": "How are production software releases currently deployed?",
        "gold_contains": ["continuous git-tag automated deploys"],
        "historical_contains": ["manual bi-weekly"],
        "expect_past": False
    },
    {
        "id": "temp_09_office_hq_past",
        "category": "temporal",
        "user_id": "eval:harness:user_temp_09",
        "adds": [
            {
                "session_id": "sess_t09_a",
                "request_id": "req_t09_a",
                "messages": [
                    {"role": "user", "timestamp": 1685000000000, "content": "The company headquarters was established on 5th Avenue in New York City."}
                ]
            },
            {
                "session_id": "sess_t09_b",
                "request_id": "req_t09_b",
                "messages": [
                    {"role": "user", "timestamp": 1721000000000, "content": "HQ relocation: We moved our corporate headquarters to Market Street in San Francisco."}
                ]
            }
        ],
        "query": "Where was the company headquarters originally located before the relocation?",
        "gold_contains": ["5th Avenue in New York City"],
        "historical_contains": ["5th Avenue in New York City"],
        "expect_past": True
    },
    {
        "id": "temp_10_database_replicas",
        "category": "temporal",
        "user_id": "eval:harness:user_temp_10",
        "adds": [
            {
                "session_id": "sess_t10_a",
                "request_id": "req_t10_a",
                "messages": [
                    {"role": "user", "timestamp": 1702000000000, "content": "The database read replica configuration consists of a single replica in Virginia."}
                ]
            },
            {
                "session_id": "sess_t10_b",
                "request_id": "req_t10_b",
                "messages": [
                    {"role": "user", "timestamp": 1724000000000, "content": "DB scaling: Expanded read replicas to a three-region topology in Dublin, Tokyo, and Oregon."}
                ]
            }
        ],
        "query": "What is the current read replica topology for our database cluster?",
        "gold_contains": ["Dublin, Tokyo, and Oregon"],
        "historical_contains": ["single replica in Virginia"],
        "expect_past": False
    },
    {
        "id": "temp_11_python_version_past",
        "category": "temporal",
        "user_id": "eval:harness:user_temp_11",
        "adds": [
            {
                "session_id": "sess_t11_a",
                "request_id": "req_t11_a",
                "messages": [
                    {"role": "user", "timestamp": 1692000000000, "content": "All core backend microservices are standardized on Python 3.9 runtime."}
                ]
            },
            {
                "session_id": "sess_t11_b",
                "request_id": "req_t11_b",
                "messages": [
                    {"role": "user", "timestamp": 1720500000000, "content": "Runtime upgrade: Backend services migrated to Python 3.12 with uv package manager."}
                ]
            }
        ],
        "query": "What Python runtime version was used for backend microservices prior to the upgrade?",
        "gold_contains": ["Python 3.9"],
        "historical_contains": ["Python 3.9"],
        "expect_past": True
    },
    {
        "id": "temp_12_oncall_lead",
        "category": "temporal",
        "user_id": "eval:harness:user_temp_12",
        "adds": [
            {
                "session_id": "sess_t12_a",
                "request_id": "req_t12_a",
                "messages": [
                    {"role": "user", "timestamp": 1724000000000, "content": "Jordan is assigned as the primary on-call engineer for the SRE rotation."}
                ]
            },
            {
                "session_id": "sess_t12_b",
                "request_id": "req_t12_b",
                "messages": [
                    {"role": "user", "timestamp": 1724604800000, "content": "Handover complete: Carlos is now the active primary on-call lead for SRE."}
                ]
            }
        ],
        "query": "Who is currently serving as the active primary on-call engineer?",
        "gold_contains": ["Carlos"],
        "historical_contains": ["Jordan"],
        "expect_past": False
    },
    {
        "id": "temp_13_pricing_tier_past",
        "category": "temporal",
        "user_id": "eval:harness:user_temp_13",
        "adds": [
            {
                "session_id": "sess_t13_a",
                "request_id": "req_t13_a",
                "messages": [
                    {"role": "user", "timestamp": 1689000000000, "content": "The subscription Pro tier pricing was set at 29 dollars per month."}
                ]
            },
            {
                "session_id": "sess_t13_b",
                "request_id": "req_t13_b",
                "messages": [
                    {"role": "user", "timestamp": 1719000000000, "content": "Pricing adjustment: The Pro tier has been updated to 49 dollars per month."}
                ]
            }
        ],
        "query": "What was the original monthly subscription price for the Pro tier before the revision?",
        "gold_contains": ["29 dollars"],
        "historical_contains": ["29 dollars"],
        "expect_past": True
    },
    {
        "id": "temp_14_cache_engine",
        "category": "temporal",
        "user_id": "eval:harness:user_temp_14",
        "adds": [
            {
                "session_id": "sess_t14_a",
                "request_id": "req_t14_a",
                "messages": [
                    {"role": "user", "timestamp": 1699000000000, "content": "Our API gateway session cache runs on Memcached."}
                ]
            },
            {
                "session_id": "sess_t14_b",
                "request_id": "req_t14_b",
                "messages": [
                    {"role": "user", "timestamp": 1722000000000, "content": "Cache infrastructure migration: Switched API gateway session cache to Redis Cluster 7.2."}
                ]
            }
        ],
        "query": "Which caching technology is currently deployed for API gateway sessions?",
        "gold_contains": ["Redis Cluster 7.2"],
        "historical_contains": ["Memcached"],
        "expect_past": False
    },
    {
        "id": "temp_15_domain_registrar_past",
        "category": "temporal",
        "user_id": "eval:harness:user_temp_15",
        "adds": [
            {
                "session_id": "sess_t15_a",
                "request_id": "req_t15_a",
                "messages": [
                    {"role": "user", "timestamp": 1682000000000, "content": "All corporate DNS domains were registered initially with GoDaddy."}
                ]
            },
            {
                "session_id": "sess_t15_b",
                "request_id": "req_t15_b",
                "messages": [
                    {"role": "user", "timestamp": 1717000000000, "content": "DNS administration: Domain registrations transferred to Cloudflare Registrar."}
                ]
            }
        ],
        "query": "Where were our DNS domains registered originally before migrating?",
        "gold_contains": ["GoDaddy"],
        "historical_contains": ["GoDaddy"],
        "expect_past": True
    }
]


SCENARIOS_COL_G_EXECUTION: List[Dict[str, Any]] = [
    {
        "id": "exec_01_db_migration",
        "category": "execution",
        "user_id": "eval:harness:user_exec_01",
        "adds": [
            {
                "session_id": "sess_e01",
                "request_id": "req_e01",
                "messages": [
                    {"role": "user", "content": "Step 1: Put cluster in maintenance mode: `vault-cli maintenance on --force`."},
                    {"role": "user", "content": "Step 2: Run schema migration script: `python -m db.migrate --target v4.2`."},
                    {"role": "user", "content": "Step 3: Validate table checksums with `db-verify --all-shards`."},
                    {"role": "user", "content": "Step 4: Disable maintenance mode: `vault-cli maintenance off`."}
                ]
            }
        ],
        "query": "How do I execute the schema migration on the vault cluster step by step?",
        "procedural_steps": [
            "Step 1: Put cluster in maintenance mode",
            "Step 2: Run schema migration script",
            "Step 3: Validate table checksums",
            "Step 4: Disable maintenance mode"
        ],
        "gold_contains": ["Step 2: Run schema migration script"]
    },
    {
        "id": "exec_02_debug_oom_trace",
        "category": "execution",
        "user_id": "eval:harness:user_exec_02",
        "adds": [
            {
                "session_id": "sess_e02",
                "request_id": "req_e02",
                "messages": [
                    {"role": "user", "content": "Diagnostic Trace: Worker process killed with exit code 137 (SIGKILL OOM)."},
                    {"role": "user", "content": "Root Cause: Memory leak in gRPC streaming buffer when batch size > 1000."},
                    {"role": "user", "content": "Repair Action: In `worker/config.yaml`, set `stream_buffer_limit: 256MB` and restart with `systemctl restart worker`."}
                ]
            }
        ],
        "query": "What are the troubleshooting steps to repair the worker process exit code 137 OOM crash?",
        "procedural_steps": [
            "Worker process killed with exit code 137",
            "stream_buffer_limit: 256MB"
        ],
        "gold_contains": ["stream_buffer_limit: 256MB", "systemctl restart worker"]
    },
    {
        "id": "exec_03_tls_cert_renewal",
        "category": "execution",
        "user_id": "eval:harness:user_exec_03",
        "adds": [
            {
                "session_id": "sess_e03",
                "request_id": "req_e03",
                "messages": [
                    {"role": "user", "content": "Step 1: Request certificate renewal via `certbot certonly --standalone -d api.domain.com`."},
                    {"role": "user", "content": "Step 2: Copy generated fullchain.pem to `/etc/ssl/certs/api.crt`."},
                    {"role": "user", "content": "Step 3: Test web server syntax using `nginx -t`."},
                    {"role": "user", "content": "Step 4: Reload web proxy gracefully with `systemctl reload nginx`."}
                ]
            }
        ],
        "query": "What is the procedure for renewing expired SSL certificates on the web gateway?",
        "procedural_steps": [
            "Step 1: Request certificate renewal",
            "Step 2: Copy generated fullchain",
            "Step 3: Test web server syntax",
            "Step 4: Reload web proxy"
        ],
        "gold_contains": ["certbot certonly", "systemctl reload nginx"]
    },
    {
        "id": "exec_04_rollback_k8s_deployment",
        "category": "execution",
        "user_id": "eval:harness:user_exec_04",
        "adds": [
            {
                "session_id": "sess_e04",
                "request_id": "req_e04",
                "messages": [
                    {"role": "user", "content": "Step 1: Identify previous healthy revision with `kubectl rollout history deployment/payment-svc`."},
                    {"role": "user", "content": "Step 2: Execute undo deployment via `kubectl rollout undo deployment/payment-svc --to-revision=12`."},
                    {"role": "user", "content": "Step 3: Monitor pod readiness with `kubectl rollout status deployment/payment-svc`."},
                    {"role": "user", "content": "Step 4: Verify Prometheus error rate dropped below 0.1 percent."}
                ]
            }
        ],
        "query": "What are the exact commands to rollback an unhealthy Kubernetes deployment?",
        "procedural_steps": [
            "Step 1: Identify previous healthy revision",
            "Step 2: Execute undo deployment",
            "Step 3: Monitor pod readiness",
            "Step 4: Verify Prometheus error rate"
        ],
        "gold_contains": ["kubectl rollout undo", "to-revision=12"]
    },
    {
        "id": "exec_05_restore_postgres_backup",
        "category": "execution",
        "user_id": "eval:harness:user_exec_05",
        "adds": [
            {
                "session_id": "sess_e05",
                "request_id": "req_e05",
                "messages": [
                    {"role": "user", "content": "Step 1: Stop client connections with `systemctl stop app-worker`."},
                    {"role": "user", "content": "Step 2: Drop corrupt database and re-create: `dropdb prod_db && createdb prod_db`."},
                    {"role": "user", "content": "Step 3: Restore binary snapshot: `pg_restore -d prod_db -j 4 /backups/prod_snapshot.dump`."},
                    {"role": "user", "content": "Step 4: Rebuild optimizer statistics: `vacuumdb --analyze prod_db`."},
                    {"role": "user", "content": "Step 5: Resume client traffic: `systemctl start app-worker`."}
                ]
            }
        ],
        "query": "What is the runbook procedure to restore PostgreSQL from a snapshot dump?",
        "procedural_steps": [
            "Step 1: Stop client connections",
            "Step 2: Drop corrupt database",
            "Step 3: Restore binary snapshot",
            "Step 4: Rebuild optimizer statistics",
            "Step 5: Resume client traffic"
        ],
        "gold_contains": ["pg_restore -d prod_db", "vacuumdb --analyze"]
    },
    {
        "id": "exec_06_setup_local_dev",
        "category": "execution",
        "user_id": "eval:harness:user_exec_06",
        "adds": [
            {
                "session_id": "sess_e06",
                "request_id": "req_e06",
                "messages": [
                    {"role": "user", "content": "Step 1: Clone workspace repository: `git clone git@github.com:org/core-engine.git`."},
                    {"role": "user", "content": "Step 2: Copy configuration template: `cp .env.example .env.local`."},
                    {"role": "user", "content": "Step 3: Synchronize python virtual environment: `uv sync`."},
                    {"role": "user", "content": "Step 4: Run unit test verification suite: `uv run pytest tests/`."}
                ]
            }
        ],
        "query": "How does an engineer configure the local dev environment step by step?",
        "procedural_steps": [
            "Step 1: Clone workspace repository",
            "Step 2: Copy configuration template",
            "Step 3: Synchronize python virtual environment",
            "Step 4: Run unit test verification"
        ],
        "gold_contains": ["uv sync", "uv run pytest"]
    },
    {
        "id": "exec_07_purge_redis_cache",
        "category": "execution",
        "user_id": "eval:harness:user_exec_07",
        "adds": [
            {
                "session_id": "sess_e07",
                "request_id": "req_e07",
                "messages": [
                    {"role": "user", "content": "Step 1: Connect to Redis cluster node: `redis-cli -c -h redis-prod.internal -p 6379`."},
                    {"role": "user", "content": "Step 2: Scan for expired token keys: `SCAN 0 MATCH auth:token:* COUNT 500`."},
                    {"role": "user", "content": "Step 3: Asynchronously unlink matching keys with `UNLINK`."},
                    {"role": "user", "content": "Step 4: Confirm free memory metric: `INFO memory`."}
                ]
            }
        ],
        "query": "What is the procedure to selectively purge session keys in Redis?",
        "procedural_steps": [
            "Step 1: Connect to Redis",
            "Step 2: Scan for expired token",
            "Step 3: Asynchronously unlink",
            "Step 4: Confirm free memory"
        ],
        "gold_contains": ["SCAN 0 MATCH auth:token", "INFO memory"]
    },
    {
        "id": "exec_08_rotate_api_secrets",
        "category": "execution",
        "user_id": "eval:harness:user_exec_08",
        "adds": [
            {
                "session_id": "sess_e08",
                "request_id": "req_e08",
                "messages": [
                    {"role": "user", "content": "Step 1: Provision secondary API key in third-party provider dashboard."},
                    {"role": "user", "content": "Step 2: Store key in Vault path: `vault kv put secret/apps/billing secondary_key=KEY_VAL`."},
                    {"role": "user", "content": "Step 3: Trigger rolling deployment of billing workers."},
                    {"role": "user", "content": "Step 4: Deactivate primary old key after 24 hours of zero traffic."}
                ]
            }
        ],
        "query": "What is the standard procedure for rotating application API credentials?",
        "procedural_steps": [
            "Step 1: Provision secondary API key",
            "Step 2: Store key in Vault",
            "Step 3: Trigger rolling deployment",
            "Step 4: Deactivate primary old key"
        ],
        "gold_contains": ["vault kv put secret/apps/billing", "rolling deployment"]
    },
    {
        "id": "exec_09_kafka_consumer_lag_fix",
        "category": "execution",
        "user_id": "eval:harness:user_exec_09",
        "adds": [
            {
                "session_id": "sess_e09",
                "request_id": "req_e09",
                "messages": [
                    {"role": "user", "content": "Step 1: Check partition consumer lag: `kafka-consumer-groups.sh --bootstrap-server kafka:9092 --describe --group analytics`."},
                    {"role": "user", "content": "Step 2: Expand topic partitions from 6 to 12 via `kafka-topics.sh --alter --partitions 12`."},
                    {"role": "user", "content": "Step 3: Scale consumer Kubernetes deployment to 12 replicas: `kubectl scale deployment/consumer --replicas=12`."},
                    {"role": "user", "content": "Step 4: Verify consumer rebalance and observe lag reduction."}
                ]
            }
        ],
        "query": "How do we resolve critical Kafka consumer lag on the event pipeline?",
        "procedural_steps": [
            "Step 1: Check partition consumer lag",
            "Step 2: Expand topic partitions",
            "Step 3: Scale consumer Kubernetes deployment",
            "Step 4: Verify consumer rebalance"
        ],
        "gold_contains": ["kafka-consumer-groups.sh", "partitions 12"]
    },
    {
        "id": "exec_10_fix_504_nginx",
        "category": "execution",
        "user_id": "eval:harness:user_exec_10",
        "adds": [
            {
                "session_id": "sess_e10",
                "request_id": "req_e10",
                "messages": [
                    {"role": "user", "content": "Step 1: Inspect reverse proxy timeout configuration in `/etc/nginx/conf.d/gateway.conf`."},
                    {"role": "user", "content": "Step 2: Increase backend read timeout: set `proxy_read_timeout 300s;` and `proxy_connect_timeout 60s;`."},
                    {"role": "user", "content": "Step 3: Validate Nginx syntax: `nginx -t`."},
                    {"role": "user", "content": "Step 4: Apply configuration reload: `systemctl reload nginx`."}
                ]
            }
        ],
        "query": "How to resolve 504 Gateway Timeout errors on long-running report downloads?",
        "procedural_steps": [
            "Step 1: Inspect reverse proxy timeout",
            "Step 2: Increase backend read timeout",
            "Step 3: Validate Nginx syntax",
            "Step 4: Apply configuration reload"
        ],
        "gold_contains": ["proxy_read_timeout 300s", "nginx -t"]
    },
    {
        "id": "exec_11_compile_native_extension",
        "category": "execution",
        "user_id": "eval:harness:user_exec_11",
        "adds": [
            {
                "session_id": "sess_e11",
                "request_id": "req_e11",
                "messages": [
                    {"role": "user", "content": "Step 1: Install build dependencies: `sudo apt-get install -y cmake clang libomp-dev`."},
                    {"role": "user", "content": "Step 2: Configure build directory: `cmake -B build -DCMAKE_BUILD_TYPE=Release`."},
                    {"role": "user", "content": "Step 3: Compile binary artifacts: `cmake --build build -j $(nproc)`."},
                    {"role": "user", "content": "Step 4: Execute test suite with `ctest --test-dir build --output-on-failure`."}
                ]
            }
        ],
        "query": "What are the instructions to build the native C++ library extension from source?",
        "procedural_steps": [
            "Step 1: Install build dependencies",
            "Step 2: Configure build directory",
            "Step 3: Compile binary artifacts",
            "Step 4: Execute test suite"
        ],
        "gold_contains": ["cmake -B build", "ctest --test-dir"]
    },
    {
        "id": "exec_12_pgo_optimization",
        "category": "execution",
        "user_id": "eval:harness:user_exec_12",
        "adds": [
            {
                "session_id": "sess_e12",
                "request_id": "req_e12",
                "messages": [
                    {"role": "user", "content": "Step 1: Compile instrumentation binary with `-fprofile-generate=/tmp/pgo`."},
                    {"role": "user", "content": "Step 2: Run representative benchmark training workload to collect runtime statistics."},
                    {"role": "user", "content": "Step 3: Recompile final optimized binary utilizing `-fprofile-use=/tmp/pgo -O3`."},
                    {"role": "user", "content": "Step 4: Verify 18 percent latency reduction in production canary."}
                ]
            }
        ],
        "query": "What is the profile-guided optimization build sequence?",
        "procedural_steps": [
            "Step 1: Compile instrumentation binary",
            "Step 2: Run representative benchmark",
            "Step 3: Recompile final optimized binary",
            "Step 4: Verify 18 percent latency"
        ],
        "gold_contains": ["-fprofile-generate", "-fprofile-use"]
    },
    {
        "id": "exec_13_reindex_elasticsearch",
        "category": "execution",
        "user_id": "eval:harness:user_exec_13",
        "adds": [
            {
                "session_id": "sess_e13",
                "request_id": "req_e13",
                "messages": [
                    {"role": "user", "content": "Step 1: Create target index schema with updated field mappings: `PUT /events_v2`."},
                    {"role": "user", "content": "Step 2: Trigger async reindexing: `POST /_reindex?wait_for_completion=false` with source `events_v1` and dest `events_v2`."},
                    {"role": "user", "content": "Step 3: Atomic alias swap: `POST /_aliases` removing `events_v1` and adding `events_v2` to alias `events`."},
                    {"role": "user", "content": "Step 4: Delete retired historical index: `DELETE /events_v1`."}
                ]
            }
        ],
        "query": "How do I perform a zero-downtime Elasticsearch index migration step by step?",
        "procedural_steps": [
            "Step 1: Create target index schema",
            "Step 2: Trigger async reindexing",
            "Step 3: Atomic alias swap",
            "Step 4: Delete retired historical index"
        ],
        "gold_contains": ["POST /_reindex", "POST /_aliases"]
    },
    {
        "id": "exec_14_wireguard_vpn_setup",
        "category": "execution",
        "user_id": "eval:harness:user_exec_14",
        "adds": [
            {
                "session_id": "sess_e14",
                "request_id": "req_e14",
                "messages": [
                    {"role": "user", "content": "Step 1: Generate cryptographic keypair: `wg genkey | tee privatekey | wg pubkey > publickey`."},
                    {"role": "user", "content": "Step 2: Create interface config file at `/etc/wireguard/wg0.conf` with Address and PrivateKey."},
                    {"role": "user", "content": "Step 3: Bring up network interface: `wg-quick up wg0`."},
                    {"role": "user", "content": "Step 4: Enable persistent boot service: `systemctl enable wg-quick@wg0`."}
                ]
            }
        ],
        "query": "What are the configuration steps to stand up a WireGuard VPN tunnel?",
        "procedural_steps": [
            "Step 1: Generate cryptographic keypair",
            "Step 2: Create interface config",
            "Step 3: Bring up network interface",
            "Step 4: Enable persistent boot"
        ],
        "gold_contains": ["wg genkey", "wg-quick up wg0"]
    },
    {
        "id": "exec_15_debug_mysql_deadlock",
        "category": "execution",
        "user_id": "eval:harness:user_exec_15",
        "adds": [
            {
                "session_id": "sess_e15",
                "request_id": "req_e15",
                "messages": [
                    {"role": "user", "content": "Step 1: Inspect recent engine deadlocks: `SHOW ENGINE INNODB STATUS\\G`."},
                    {"role": "user", "content": "Step 2: Locate active locking transaction threads in `sys.innodb_lock_waits`."},
                    {"role": "user", "content": "Step 3: Terminate the blocking query connection: `KILL <blocking_trx_id>`."},
                    {"role": "user", "content": "Step 4: Add composite index on `(order_id, user_id)` to resolve recurring deadlock condition."}
                ]
            }
        ],
        "query": "What are the troubleshooting steps to diagnose and resolve active database deadlocks?",
        "procedural_steps": [
            "Step 1: Inspect recent engine deadlocks",
            "Step 2: Locate active locking transaction",
            "Step 3: Terminate the blocking query",
            "Step 4: Add composite index"
        ],
        "gold_contains": ["SHOW ENGINE INNODB STATUS", "sys.innodb_lock_waits"]
    }
]


SCENARIOS_COL_B_MULTIHOP: List[Dict[str, Any]] = [
    {
        "id": "multi_01_lab_location",
        "category": "multihop",
        "user_id": "eval:harness:user_multi_01",
        "adds": [
            {
                "session_id": "sess_m01_hop1",
                "request_id": "req_m01_hop1",
                "messages": [
                    {"role": "user", "content": "Elena Rostova is the director of the Helix Propulsion Lab."}
                ]
            },
            {
                "session_id": "sess_m01_hop2",
                "request_id": "req_m01_hop2",
                "messages": [
                    {"role": "user", "content": "The Helix Propulsion Lab is headquartered at Aerospace Park in Toulouse, France."}
                ]
            }
        ],
        "query": "In which city is the aerospace facility directed by Elena Rostova located?",
        "hop1_contains": ["Elena Rostova", "Helix Propulsion Lab"],
        "hop2_contains": ["Helix Propulsion Lab", "Toulouse"],
        "gold_contains": ["Toulouse"]
    },
    {
        "id": "multi_02_founder_alma_mater",
        "category": "multihop",
        "user_id": "eval:harness:user_multi_02",
        "adds": [
            {
                "session_id": "sess_m02_hop1",
                "request_id": "req_m02_hop1",
                "messages": [
                    {"role": "user", "content": "Project Quasar was established by quantum physicist Dr. Vikram Mehta."}
                ]
            },
            {
                "session_id": "sess_m02_hop2",
                "request_id": "req_m02_hop2",
                "messages": [
                    {"role": "user", "content": "Dr. Vikram Mehta earned his doctorate degree at the University of Cambridge."}
                ]
            }
        ],
        "query": "Which academic institution conferred the doctoral degree of Project Quasar's founder?",
        "hop1_contains": ["Project Quasar", "Dr. Vikram Mehta"],
        "hop2_contains": ["Dr. Vikram Mehta", "University of Cambridge"],
        "gold_contains": ["University of Cambridge"]
    },
    {
        "id": "multi_03_satellite_orbit",
        "category": "multihop",
        "user_id": "eval:harness:user_multi_03",
        "adds": [
            {
                "session_id": "sess_m03_hop1",
                "request_id": "req_m03_hop1",
                "messages": [
                    {"role": "user", "content": "The HyperSpectra thermal sensor is carried aboard the Nimbus-9 spacecraft."}
                ]
            },
            {
                "session_id": "sess_m03_hop2",
                "request_id": "req_m03_hop2",
                "messages": [
                    {"role": "user", "content": "The Nimbus-9 spacecraft operates in sun-synchronous orbit at an altitude of 705 kilometers."}
                ]
            }
        ],
        "query": "At what operational orbit altitude does the vehicle carrying the HyperSpectra thermal sensor fly?",
        "hop1_contains": ["HyperSpectra", "Nimbus-9"],
        "hop2_contains": ["Nimbus-9", "705 kilometers"],
        "gold_contains": ["705 kilometers"]
    },
    {
        "id": "multi_04_auth_service_db",
        "category": "multihop",
        "user_id": "eval:harness:user_multi_04",
        "adds": [
            {
                "session_id": "sess_m04_hop1",
                "request_id": "req_m04_hop1",
                "messages": [
                    {"role": "user", "content": "The core Orion authentication gateway is developed and maintained by Team Sentinel."}
                ]
            },
            {
                "session_id": "sess_m04_hop2",
                "request_id": "req_m04_hop2",
                "messages": [
                    {"role": "user", "content": "Team Sentinel hosts all their service persistence on an AWS Aurora PostgreSQL cluster."}
                ]
            }
        ],
        "query": "What underlying database technology supports the authentication service built by Team Sentinel?",
        "hop1_contains": ["Orion authentication", "Team Sentinel"],
        "hop2_contains": ["Team Sentinel", "Aurora PostgreSQL"],
        "gold_contains": ["Aurora PostgreSQL"]
    },
    {
        "id": "multi_05_microservice_maintainer_city",
        "category": "multihop",
        "user_id": "eval:harness:user_multi_05",
        "adds": [
            {
                "session_id": "sess_m05_hop1",
                "request_id": "req_m05_hop1",
                "messages": [
                    {"role": "user", "content": "David Chen is the sole maintainer for the payment webhook processing daemon."}
                ]
            },
            {
                "session_id": "sess_m05_hop2",
                "request_id": "req_m05_hop2",
                "messages": [
                    {"role": "user", "content": "David Chen works out of the company engineering center in Toronto."}
                ]
            }
        ],
        "query": "In which city is the software engineer in charge of the payment webhook daemon located?",
        "hop1_contains": ["David Chen", "payment webhook"],
        "hop2_contains": ["David Chen", "Toronto"],
        "gold_contains": ["Toronto"]
    },
    {
        "id": "multi_06_library_author_institution",
        "category": "multihop",
        "user_id": "eval:harness:user_multi_06",
        "adds": [
            {
                "session_id": "sess_m06_hop1",
                "request_id": "req_m06_hop1",
                "messages": [
                    {"role": "user", "content": "The high-throughput FastGraph serialization library was created by Sophie Dubois."}
                ]
            },
            {
                "session_id": "sess_m06_hop2",
                "request_id": "req_m06_hop2",
                "messages": [
                    {"role": "user", "content": "Sophie Dubois spent seven years conducting research at Bell Labs in New Jersey."}
                ]
            }
        ],
        "query": "Which research institution did the author of the FastGraph serialization library work at?",
        "hop1_contains": ["FastGraph", "Sophie Dubois"],
        "hop2_contains": ["Sophie Dubois", "Bell Labs"],
        "gold_contains": ["Bell Labs"]
    },
    {
        "id": "multi_07_cve_package_maintainer",
        "category": "multihop",
        "user_id": "eval:harness:user_multi_07",
        "adds": [
            {
                "session_id": "sess_m07_hop1",
                "request_id": "req_m07_hop1",
                "messages": [
                    {"role": "user", "content": "Critical vulnerability CVE-2025-4102 was resolved in release tag v3.4.1."}
                ]
            },
            {
                "session_id": "sess_m07_hop2",
                "request_id": "req_m07_hop2",
                "messages": [
                    {"role": "user", "content": "Release tag v3.4.1 was reviewed, signed, and published by maintainer Liam Vance."}
                ]
            }
        ],
        "query": "Who signed and published the software release that mitigated vulnerability CVE-2025-4102?",
        "hop1_contains": ["CVE-2025-4102", "v3.4.1"],
        "hop2_contains": ["v3.4.1", "Liam Vance"],
        "gold_contains": ["Liam Vance"]
    },
    {
        "id": "multi_08_hardware_fabrication_city",
        "category": "multihop",
        "user_id": "eval:harness:user_multi_08",
        "adds": [
            {
                "session_id": "sess_m08_hop1",
                "request_id": "req_m08_hop1",
                "messages": [
                    {"role": "user", "content": "Our distributed training clusters run on Nova-T400 tensor acceleration cards."}
                ]
            },
            {
                "session_id": "sess_m08_hop2",
                "request_id": "req_m08_hop2",
                "messages": [
                    {"role": "user", "content": "Nova-T400 tensor acceleration cards are fabricated by HyperSilicon at their foundry in Yokohama."}
                ]
            }
        ],
        "query": "In which city is the foundry that fabricates the accelerator cards for our distributed training cluster?",
        "hop1_contains": ["Nova-T400", "training cluster"],
        "hop2_contains": ["Nova-T400", "Yokohama"],
        "gold_contains": ["Yokohama"]
    },
    {
        "id": "multi_09_rendering_engine_developer",
        "category": "multihop",
        "user_id": "eval:harness:user_multi_09",
        "adds": [
            {
                "session_id": "sess_m09_hop1",
                "request_id": "req_m09_hop1",
                "messages": [
                    {"role": "user", "content": "The desktop client UI framework is built directly on the CanvasGL rendering pipeline."}
                ]
            },
            {
                "session_id": "sess_m09_hop2",
                "request_id": "req_m09_hop2",
                "messages": [
                    {"role": "user", "content": "The CanvasGL rendering pipeline was authored in Rust by graphics architect Marcus Brandt."}
                ]
            }
        ],
        "query": "Who is the graphics programmer who authored the rendering pipeline powering the desktop client UI?",
        "hop1_contains": ["desktop client", "CanvasGL"],
        "hop2_contains": ["CanvasGL", "Marcus Brandt"],
        "gold_contains": ["Marcus Brandt"]
    },
    {
        "id": "multi_10_incident_commander_title",
        "category": "multihop",
        "user_id": "eval:harness:user_multi_10",
        "adds": [
            {
                "session_id": "sess_m10_hop1",
                "request_id": "req_m10_hop1",
                "messages": [
                    {"role": "user", "content": "The high-severity data center power outage INC-8821 was commanded by Priya Patel."}
                ]
            },
            {
                "session_id": "sess_m10_hop2",
                "request_id": "req_m10_hop2",
                "messages": [
                    {"role": "user", "content": "Priya Patel serves as the Vice President of Infrastructure Reliability."}
                ]
            }
        ],
        "query": "What leadership position is held by the person who commanded incident INC-8821?",
        "hop1_contains": ["INC-8821", "Priya Patel"],
        "hop2_contains": ["Priya Patel", "Vice President of Infrastructure Reliability"],
        "gold_contains": ["Vice President of Infrastructure Reliability"]
    },
    {
        "id": "multi_11_conference_sponsor_org",
        "category": "multihop",
        "user_id": "eval:harness:user_multi_11",
        "adds": [
            {
                "session_id": "sess_m11_hop1",
                "request_id": "req_m11_hop1",
                "messages": [
                    {"role": "user", "content": "The keynote address at the European Systems Summit was delivered by the lead developer of LatticeMQ."}
                ]
            },
            {
                "session_id": "sess_m11_hop2",
                "request_id": "req_m11_hop2",
                "messages": [
                    {"role": "user", "content": "LatticeMQ is an open-source message queue governed by the Linux Foundation."}
                ]
            }
        ],
        "query": "Which governing body oversees the message queue system presented during the European Systems Summit keynote?",
        "hop1_contains": ["European Systems Summit", "LatticeMQ"],
        "hop2_contains": ["LatticeMQ", "Linux Foundation"],
        "gold_contains": ["Linux Foundation"]
    },
    {
        "id": "multi_12_patent_assignee_firm",
        "category": "multihop",
        "user_id": "eval:harness:user_multi_12",
        "adds": [
            {
                "session_id": "sess_m12_hop1",
                "request_id": "req_m12_hop1",
                "messages": [
                    {"role": "user", "content": "The distributed lossless vector compression patent US-991284 was invented by Kai Tanaka."}
                ]
            },
            {
                "session_id": "sess_m12_hop2",
                "request_id": "req_m12_hop2",
                "messages": [
                    {"role": "user", "content": "Kai Tanaka formally assigned all intellectual property rights to Lumina Systems Inc."}
                ]
            }
        ],
        "query": "To which corporate entity is the vector compression patent US-991284 assigned?",
        "hop1_contains": ["US-991284", "Kai Tanaka"],
        "hop2_contains": ["Kai Tanaka", "Lumina Systems"],
        "gold_contains": ["Lumina Systems"]
    }
]


SCENARIOS_COL_D_RULES: List[Dict[str, Any]] = [
    {
        "id": "rule_01_friday_deploy",
        "category": "rule",
        "user_id": "eval:harness:user_rule_01",
        "adds": [
            {
                "session_id": "sess_r01",
                "request_id": "req_r01",
                "messages": [
                    {"role": "user", "content": "Deployment Policy: Engineers must never deploy changes directly to production on Fridays after 2 PM UTC."}
                ]
            }
        ],
        "query": "What is the policy regarding Friday production deployments?",
        "gold_contains": ["never deploy changes directly to production on Fridays after 2 PM UTC"]
    },
    {
        "id": "rule_02_pii_logging_restriction",
        "category": "rule",
        "user_id": "eval:harness:user_rule_02",
        "adds": [
            {
                "session_id": "sess_r02",
                "request_id": "req_r02",
                "messages": [
                    {"role": "user", "content": "Security Rule: Developers must never log unmasked credit card numbers, CVVs, or Social Security numbers to standard output or log sinks."}
                ]
            }
        ],
        "query": "What are the logging restrictions regarding sensitive customer PII?",
        "gold_contains": ["never log unmasked credit card numbers"]
    },
    {
        "id": "rule_03_pr_terraform_signoff",
        "category": "rule",
        "user_id": "eval:harness:user_rule_03",
        "adds": [
            {
                "session_id": "sess_r03",
                "request_id": "req_r03",
                "messages": [
                    {"role": "user", "content": "Infrastructure Governance: All pull requests modifying Terraform configuration must always require mandatory review and approval from at least one Principal SRE."}
                ]
            }
        ],
        "query": "What approvals are mandatory before merging changes to cloud Terraform infrastructure?",
        "gold_contains": ["mandatory review and approval from at least one Principal SRE"]
    },
    {
        "id": "rule_04_encryption_transit_tls",
        "category": "rule",
        "user_id": "eval:harness:user_rule_04",
        "adds": [
            {
                "session_id": "sess_r04",
                "request_id": "req_r04",
                "messages": [
                    {"role": "user", "content": "Network Security Mandate: All inter-service communication across VPC boundaries must always enforce mutual TLS 1.3 encryption with certificate pinning."}
                ]
            }
        ],
        "query": "What is the network protocol requirement for inter-service communication across VPC boundaries?",
        "gold_contains": ["mutual TLS 1.3 encryption"]
    },
    {
        "id": "rule_05_secret_rotation_schedule",
        "category": "rule",
        "user_id": "eval:harness:user_rule_05",
        "adds": [
            {
                "session_id": "sess_r05",
                "request_id": "req_r05",
                "messages": [
                    {"role": "user", "content": "Credential Policy: Service account authentication keys and database passwords must always rotate every 90 days and possess minimum 32 characters."}
                ]
            }
        ],
        "query": "What is the policy regarding credential rotation frequency and length?",
        "gold_contains": ["rotate every 90 days"]
    },
    {
        "id": "rule_06_analytics_retention_purge",
        "category": "rule",
        "user_id": "eval:harness:user_rule_06",
        "adds": [
            {
                "session_id": "sess_r06",
                "request_id": "req_r06",
                "messages": [
                    {"role": "user", "content": "Data Privacy Mandate: Raw user interaction telemetry and clickstream event records must never be retained for longer than 30 days."}
                ]
            }
        ],
        "query": "What is the maximum allowed retention period for raw user clickstream logs?",
        "gold_contains": ["never be retained for longer than 30 days"]
    },
    {
        "id": "rule_07_api_rate_limit_policy",
        "category": "rule",
        "user_id": "eval:harness:user_rule_07",
        "adds": [
            {
                "session_id": "sess_r07",
                "request_id": "req_r07",
                "messages": [
                    {"role": "user", "content": "API Gateway Policy: Unauthenticated public endpoints must always enforce an absolute threshold of 60 requests per minute per IP address."}
                ]
            }
        ],
        "query": "What rate limit constraints apply to unauthenticated public API requests?",
        "gold_contains": ["60 requests per minute"]
    },
    {
        "id": "rule_08_immutable_backup_lock",
        "category": "rule",
        "user_id": "eval:harness:user_rule_08",
        "adds": [
            {
                "session_id": "sess_r08",
                "request_id": "req_r08",
                "messages": [
                    {"role": "user", "content": "Disaster Recovery Mandate: Production snapshot archives must always be replicated to write-once S3 Glacier buckets with Object Lock compliance mode for 365 days."}
                ]
            }
        ],
        "query": "What is the compliance requirement for production snapshot archive immutability?",
        "gold_contains": ["Object Lock compliance mode for 365 days"]
    }
]


SCENARIOS_COL_E_STREAMING: List[Dict[str, Any]] = [
    {
        "id": "stream_01_iot_telemetry",
        "category": "streaming",
        "user_id": "eval:harness:user_stream_01",
        "adds": [
            {
                "session_id": "sess_s01",
                "request_id": "req_s01_t1",
                "messages": [{"role": "user", "content": "Sensor-Omega telemetry stream: Battery 98%, Temp 21.2C."}]
            },
            {
                "session_id": "sess_s01",
                "request_id": "req_s01_t2",
                "messages": [{"role": "user", "content": "Sensor-Omega telemetry stream: Battery 92%, Temp 23.8C."}]
            },
            {
                "session_id": "sess_s01",
                "request_id": "req_s01_t3",
                "messages": [{"role": "user", "content": "Sensor-Omega telemetry stream: Battery 84%, Temp 27.5C."}]
            }
        ],
        "query": "What is the latest reported battery level and temperature for Sensor-Omega?",
        "gold_contains": ["Battery 84%", "27.5C"]
    },
    {
        "id": "stream_02_shopping_cart_events",
        "category": "streaming",
        "user_id": "eval:harness:user_stream_02",
        "adds": [
            {
                "session_id": "sess_s02",
                "request_id": "req_s02_t1",
                "messages": [{"role": "user", "content": "Shopping session: User added 2x Wireless Headphones to cart."}]
            },
            {
                "session_id": "sess_s02",
                "request_id": "req_s02_t2",
                "messages": [{"role": "user", "content": "Shopping session: User removed 1x Wireless Headphones and added 1x USB-C Cable."}]
            },
            {
                "session_id": "sess_s02",
                "request_id": "req_s02_t3",
                "messages": [{"role": "user", "content": "Shopping session: Cart updated: 1x Wireless Headphones, 1x USB-C Cable, 1x Power Adapter."}]
            }
        ],
        "query": "What merchandise is currently in the customer's active shopping cart?",
        "gold_contains": ["1x Wireless Headphones, 1x USB-C Cable, 1x Power Adapter"]
    },
    {
        "id": "stream_03_ci_build_progress",
        "category": "streaming",
        "user_id": "eval:harness:user_stream_03",
        "adds": [
            {
                "session_id": "sess_s03",
                "request_id": "req_s03_t1",
                "messages": [{"role": "user", "content": "Build pipeline #9910: Job queued in worker queue."}]
            },
            {
                "session_id": "sess_s03",
                "request_id": "req_s03_t2",
                "messages": [{"role": "user", "content": "Build pipeline #9910: Unit tests failed at step 4 with error assert 404 == 200."}]
            },
            {
                "session_id": "sess_s03",
                "request_id": "req_s03_t3",
                "messages": [{"role": "user", "content": "Build pipeline #9910: Retry initiated with commit patch 88ab1."}]
            },
            {
                "session_id": "sess_s03",
                "request_id": "req_s03_t4",
                "messages": [{"role": "user", "content": "Build pipeline #9910: Status passed and container image pushed to registry."}]
            }
        ],
        "query": "What is the final execution outcome of build pipeline #9910?",
        "gold_contains": ["Status passed and container image pushed"]
    },
    {
        "id": "stream_04_stock_ticker_ticks",
        "category": "streaming",
        "user_id": "eval:harness:user_stream_04",
        "adds": [
            {
                "session_id": "sess_s04",
                "request_id": "req_s04_t1",
                "messages": [{"role": "user", "content": "Market stream tick: Symbol NXTC trading at $142.50."}]
            },
            {
                "session_id": "sess_s04",
                "request_id": "req_s04_t2",
                "messages": [{"role": "user", "content": "Market stream tick: Symbol NXTC trading at $144.10."}]
            },
            {
                "session_id": "sess_s04",
                "request_id": "req_s04_t3",
                "messages": [{"role": "user", "content": "Market stream tick: Symbol NXTC trading at $148.75."}]
            }
        ],
        "query": "What was the most recent transaction price recorded for ticker symbol NXTC?",
        "gold_contains": ["$148.75"]
    },
    {
        "id": "stream_05_package_tracking_scans",
        "category": "streaming",
        "user_id": "eval:harness:user_stream_05",
        "adds": [
            {
                "session_id": "sess_s05",
                "request_id": "req_s05_t1",
                "messages": [{"role": "user", "content": "Logistics tracking parcel PKG-5512: Departed sorting facility in Memphis, TN."}]
            },
            {
                "session_id": "sess_s05",
                "request_id": "req_s05_t2",
                "messages": [{"role": "user", "content": "Logistics tracking parcel PKG-5512: Arrived at distribution hub in Newark, NJ."}]
            },
            {
                "session_id": "sess_s05",
                "request_id": "req_s05_t3",
                "messages": [{"role": "user", "content": "Logistics tracking parcel PKG-5512: Out for delivery with courier in Brooklyn, NY."}]
            }
        ],
        "query": "Where was package PKG-5512 last reported in transit?",
        "gold_contains": ["Out for delivery with courier in Brooklyn, NY"]
    },
    {
        "id": "stream_06_ticket_reassignment",
        "category": "streaming",
        "user_id": "eval:harness:user_stream_06",
        "adds": [
            {
                "session_id": "sess_s06",
                "request_id": "req_s06_t1",
                "messages": [{"role": "user", "content": "Customer support ticket #4418 opened and assigned to agent Liam."}]
            },
            {
                "session_id": "sess_s06",
                "request_id": "req_s06_t2",
                "messages": [{"role": "user", "content": "Customer support ticket #4418 escalated and transferred to agent Sarah."}]
            },
            {
                "session_id": "sess_s06",
                "request_id": "req_s06_t3",
                "messages": [{"role": "user", "content": "Customer support ticket #4418 transferred to Tier 3 Specialist Marcus."}]
            }
        ],
        "query": "Which representative is currently assigned to support ticket #4418?",
        "gold_contains": ["Tier 3 Specialist Marcus"]
    },
    {
        "id": "stream_07_container_replica_count",
        "category": "streaming",
        "user_id": "eval:harness:user_stream_07",
        "adds": [
            {
                "session_id": "sess_s07",
                "request_id": "req_s07_t1",
                "messages": [{"role": "user", "content": "HPA scaling event: Service `auth-api` running with 4 active replicas."}]
            },
            {
                "session_id": "sess_s07",
                "request_id": "req_s07_t2",
                "messages": [{"role": "user", "content": "HPA scaling event: Traffic spike detected, `auth-api` scaled to 8 active replicas."}]
            },
            {
                "session_id": "sess_s07",
                "request_id": "req_s07_t3",
                "messages": [{"role": "user", "content": "HPA scaling event: Peak sustained, `auth-api` reached maximum capacity of 16 active replicas."}]
            }
        ],
        "query": "How many pod replicas are currently serving the authentication service?",
        "gold_contains": ["16 active replicas"]
    },
    {
        "id": "stream_08_canary_traffic_split",
        "category": "streaming",
        "user_id": "eval:harness:user_stream_08",
        "adds": [
            {
                "session_id": "sess_s08",
                "request_id": "req_s08_t1",
                "messages": [{"role": "user", "content": "Canary deployment controller: Routing 5 percent of production traffic to version 2.1."}]
            },
            {
                "session_id": "sess_s08",
                "request_id": "req_s08_t2",
                "messages": [{"role": "user", "content": "Canary deployment controller: Incremented traffic weight to 25 percent."}]
            },
            {
                "session_id": "sess_s08",
                "request_id": "req_s08_t3",
                "messages": [{"role": "user", "content": "Canary deployment controller: Verification successful, promoted version 2.1 to 100 percent of traffic."}]
            }
        ],
        "query": "What percentage of production traffic is routed to the new release version 2.1?",
        "gold_contains": ["100 percent of traffic"]
    }
]


SCENARIOS_COL_F_GOVERNANCE: List[Dict[str, Any]] = [
    {
        "id": "gov_01_absent_root_password",
        "category": "governance",
        "user_id": "eval:harness:user_gov_01",
        "adds": [
            {
                "session_id": "sess_g01",
                "request_id": "req_g01",
                "messages": [
                    {"role": "user", "content": "Configured local Docker container with port mapping 8080:80."},
                    {"role": "user", "content": "Reviewed the pull request for frontend styling updates."}
                ]
            }
        ],
        "query": "What is the root SSH password for the production bastion host?",
        "expected_negative": True
    },
    {
        "id": "gov_02_unrecorded_board_meeting",
        "category": "governance",
        "user_id": "eval:harness:user_gov_02",
        "adds": [
            {
                "session_id": "sess_g02",
                "request_id": "req_g02",
                "messages": [
                    {"role": "user", "content": "Sprint planning meeting reviewed tickets for database query caching."},
                    {"role": "user", "content": "Updated the swagger API specification with new response models."}
                ]
            }
        ],
        "query": "What was decided regarding executive stock option compensation during the board meeting?",
        "expected_negative": True
    },
    {
        "id": "gov_03_nonexistent_employee_contact",
        "category": "governance",
        "user_id": "eval:harness:user_gov_03",
        "adds": [
            {
                "session_id": "sess_g03",
                "request_id": "req_g03",
                "messages": [
                    {"role": "user", "content": "The engineering team welcome lunch was attended by Alice, Bob, and Charlie."},
                    {"role": "user", "content": "Alice works on distributed consensus and Bob maintains the frontend."}
                ]
            }
        ],
        "query": "What is the personal mobile phone number and residential address of Robert Langdon?",
        "expected_negative": True
    },
    {
        "id": "gov_04_undisclosed_funding_round",
        "category": "governance",
        "user_id": "eval:harness:user_gov_04",
        "adds": [
            {
                "session_id": "sess_g04",
                "request_id": "req_g04",
                "messages": [
                    {"role": "user", "content": "Our team completed the technical roadmap for the third fiscal quarter."},
                    {"role": "user", "content": "We planned performance optimizations for the search indexer."}
                ]
            }
        ],
        "query": "How much venture capital funding was raised during the secret Series C investment round?",
        "expected_negative": True
    },
    {
        "id": "gov_05_missing_private_jwt_key",
        "category": "governance",
        "user_id": "eval:harness:user_gov_05",
        "adds": [
            {
                "session_id": "sess_g05",
                "request_id": "req_g05",
                "messages": [
                    {"role": "user", "content": "Implemented user interface modal for account settings."},
                    {"role": "user", "content": "Added unit test coverage for the responsive navigation navbar."}
                ]
            }
        ],
        "query": "What is the 4096-bit private RSA key used to sign production JWT authorization tokens?",
        "expected_negative": True
    },
    {
        "id": "gov_06_untracked_incident_cause",
        "category": "governance",
        "user_id": "eval:harness:user_gov_06",
        "adds": [
            {
                "session_id": "sess_g06",
                "request_id": "req_g06",
                "messages": [
                    {"role": "user", "content": "We conducted regular load testing against the staging environment yesterday."},
                    {"role": "user", "content": "All staging metrics were normal and latency stayed under 200ms."}
                ]
            }
        ],
        "query": "What was the identified root cause of the severe billing system blackout on November 12th?",
        "expected_negative": True
    },
    {
        "id": "gov_07_unregistered_client_sla",
        "category": "governance",
        "user_id": "eval:harness:user_gov_07",
        "adds": [
            {
                "session_id": "sess_g07",
                "request_id": "req_g07",
                "messages": [
                    {"role": "user", "content": "Our active commercial contracts include Acme Logistics and Stark Industries."},
                    {"role": "user", "content": "Stark Industries renewed their annual support subscription."}
                ]
            }
        ],
        "query": "What are the specific SLA financial penalty clauses defined in the contract for Cyberdyne Dynamics?",
        "expected_negative": True
    },
    {
        "id": "gov_08_unknown_hardware_location",
        "category": "governance",
        "user_id": "eval:harness:user_gov_08",
        "adds": [
            {
                "session_id": "sess_g08",
                "request_id": "req_g08",
                "messages": [
                    {"role": "user", "content": "Kubernetes cluster deployed in Google Cloud europe-west3 with 12 worker nodes."},
                    {"role": "user", "content": "Pod autoscaler configured to maintain 75% target CPU utilization."}
                ]
            }
        ],
        "query": "What physical datacenter rack position and hardware chassis serial number hosts worker node 4?",
        "expected_negative": True
    }
]

ALL_SCENARIOS: List[Dict[str, Any]] = (
    SCENARIOS_COL_C_TEMPORAL
    + SCENARIOS_COL_G_EXECUTION
    + SCENARIOS_COL_B_MULTIHOP
    + SCENARIOS_COL_D_RULES
    + SCENARIOS_COL_E_STREAMING
    + SCENARIOS_COL_F_GOVERNANCE
)
