SKILLS = [
    ("grammar.past-simple", "Past Simple", "grammar", .35, "A2", "Describe completed past actions."),
    ("grammar.present-perfect", "Present Perfect", "grammar", .52, "B1", "Connect past experience to the present."),
    ("tech.http", "HTTP foundations", "technical_vocabulary", .35, "A2", "Explain requests, responses, headers, payloads and status codes."),
    ("tech.rest", "REST APIs", "technical_explanation", .48, "B1", "Discuss endpoints, resources and API behavior."),
    ("tech.auth", "Authentication & authorization", "technical_explanation", .56, "B1", "Clearly distinguish identity and permissions."),
    ("tech.database", "Databases & SQL", "technical_vocabulary", .50, "B1", "Explain queries, indexes, transactions, schemas and migrations."),
    ("tech.async", "Async programming", "technical_explanation", .62, "B2", "Discuss blocking, concurrency and race conditions."),
    ("tech.caching", "Caching & Redis", "technical_explanation", .60, "B2", "Explain cache hits, invalidation and latency trade-offs."),
    ("tech.deployment", "Docker & deployment", "professional_communication", .55, "B1", "Report deployments, rollbacks and breaking changes."),
    ("tech.observability", "Logging & monitoring", "technical_vocabulary", .61, "B2", "Discuss logs, metrics, traces and incidents."),
    ("tech.architecture", "Software architecture", "technical_explanation", .70, "B2", "Compare monoliths, microservices and event-driven systems."),
    ("professional.interview", "Technical interviews", "professional_communication", .65, "B2", "Give structured, concise technical answers."),
    ("professional.standup", "Daily stand-up", "professional_communication", .45, "B1", "Describe progress, plans and blockers."),
]

DEPENDENCIES = [
    ("grammar.present-perfect", "grammar.past-simple"),
    ("tech.rest", "tech.http"),
    ("tech.auth", "tech.rest"),
    ("tech.caching", "tech.database"),
    ("tech.architecture", "tech.rest"),
]

VOCABULARY = [
    ("deploy", "Make an application available in a target environment.", "Make software available for use.", ["deploy an application", "deploy to production"], ["deploy on production → deploy to production"]),
    ("rollback", "Return a system to a previous stable version.", "Undo a release.", ["roll back a deployment", "perform a rollback"], []),
    ("latency", "The time a system takes to respond.", "Response delay.", ["reduce latency", "low-latency API"], []),
    ("throughput", "The amount of work completed in a period.", "How much work a system handles.", ["improve throughput", "request throughput"], []),
    ("bottleneck", "A component that limits overall performance.", "The slowest limiting part.", ["become a bottleneck", "identify a bottleneck"], []),
    ("payload", "The meaningful data carried by a request or message.", "The data sent in a message.", ["request payload", "validate the payload"], []),
    ("idempotency", "The property of producing the same outcome after repeated operations.", "Safe repetition with the same result.", ["idempotent request", "idempotency key"], []),
    ("breaking change", "A change that is incompatible with existing consumers.", "A change that makes old clients stop working.", ["introduce a breaking change", "avoid breaking changes"], []),
    ("rate limiting", "Restricting how frequently a client can use a service.", "A request frequency limit.", ["apply rate limiting", "rate limit exceeded"], []),
    ("connection pool", "A reusable set of database connections.", "Connections kept ready for reuse.", ["configure a connection pool", "exhaust the pool"], []),
    ("race condition", "A fault caused by timing-dependent access to shared state.", "A timing bug between concurrent tasks.", ["prevent a race condition", "race-condition bug"], []),
    ("technical debt", "Future cost created by choosing a quicker design now.", "Work postponed by a short-term solution.", ["reduce technical debt", "accumulate technical debt"], []),
]

PLACEMENT_ITEMS = [
    {"key":"grammar-1","dimension":"grammar","difficulty":.46,"type":"choice","prompt":"Choose the natural sentence about a finished deployment.","options":["We have deployed it yesterday.","We deployed it yesterday.","We did deployed it yesterday."],"answer":"We deployed it yesterday."},
    {"key":"vocab-1","dimension":"vocabulary","difficulty":.48,"type":"choice","prompt":"Which phrase means that one component limits the whole system?","options":["It is a bottleneck.","It is a throughput.","It is a rollback."],"answer":"It is a bottleneck."},
    {"key":"tech-1","dimension":"technical_vocabulary","difficulty":.55,"type":"choice","prompt":"Authentication verifies identity. What does authorization determine?","options":["What a user may access", "How a password is hashed", "Whether a server is online"],"answer":"What a user may access"},
    {"key":"reading-1","dimension":"reading","difficulty":.58,"type":"choice","prompt":"The API returned 429 after a traffic spike. What most likely happened?","options":["Rate limiting was triggered", "The database migrated", "The token was refreshed"],"answer":"Rate limiting was triggered"},
    {"key":"writing-1","dimension":"writing","difficulty":.60,"type":"text","prompt":"Write 1–2 sentences for a stand-up: what did you finish yesterday and what will you do today?","answer":""},
    {"key":"explain-1","dimension":"technical_explanation","difficulty":.65,"type":"text","prompt":"Explain the difference between authentication and authorization in 2–3 sentences.","answer":""},
    {"key":"professional-1","dimension":"professional_communication","difficulty":.68,"type":"text","prompt":"Tell an interviewer how you have improved API performance in a previous project.","answer":""},
]

LESSON_EXERCISES = [
    {"type":"MULTIPLE_CHOICE","prompt":"Which sentence sounds natural in a deployment update?","options":["We deployed to production this morning.","We deployed on production this morning.","We have deploy to production."],"answer":"We deployed to production this morning."},
    {"type":"ERROR_CORRECTION","prompt":"Correct this sentence: “I've reduced the API latency yesterday.”","answer":"I reduced the API latency yesterday."},
    {"type":"TECHNICAL_INTERVIEW","prompt":"Imagine you're in a backend interview. Explain what you did in a previous project to reduce API latency. Use at least two of: throughput, bottleneck, caching, query.","answer":""},
]

