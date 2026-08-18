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

B1_COURSE = [
    {
        "key":"deployment-updates","title":"Clear Deployment Updates","skill_id":"tech.deployment","duration":20,
        "objective":"Report completed deployments and rollbacks with accurate Past Simple and deployment collocations.",
        "context":"You are updating your team after a production release.",
        "exercises":[
            {"type":"MULTIPLE_CHOICE","prompt":"Which sentence sounds natural in a deployment update?","options":["We deployed to production this morning.","We deployed on production this morning.","We have deploy to production."],"answer":"We deployed to production this morning.","error_type":"incorrect-preposition","explanation":"Use ‘deploy to production’ as the standard IT collocation."},
            {"type":"ERROR_CORRECTION","prompt":"Correct this sentence: “I've deployed the fix yesterday.”","answer":"I deployed the fix yesterday.","error_type":"present-perfect-vs-past-simple","explanation":"Use Past Simple with a finished time marker such as ‘yesterday’."},
            {"type":"WORK_UPDATE","prompt":"Write a short release update. Say what you deployed, what happened, and whether a rollback was needed.","answer":"","rubric_terms":["deploy","rollback"],"error_type":"deployment-update-clarity","explanation":"A useful release update states the action, result, and rollback status."},
        ],
        "summary":{"strong":["Deployment collocations","Past Simple updates"],"needs_work":["Finished time markers","Release outcomes"],"new_words":["deploy","rollback","breaking change"],"next_topic":"REST API explanations"},
    },
    {
        "key":"rest-explanations","title":"Explaining REST API Behavior","skill_id":"tech.rest","duration":20,
        "objective":"Explain endpoint behavior using precise HTTP and payload vocabulary.",
        "context":"You are documenting an endpoint for another backend team.",
        "exercises":[
            {"type":"MULTIPLE_CHOICE","prompt":"Which sentence describes a missing API resource precisely?","options":["The endpoint returns 404 when the resource does not exist.","The endpoint throws 404 when resource not exist.","The API is making a missing."],"answer":"The endpoint returns 404 when the resource does not exist.","error_type":"api-description-grammar","explanation":"Use ‘returns 404’ and a complete when-clause."},
            {"type":"ERROR_CORRECTION","prompt":"Correct this sentence: “The request payload contain user data.”","answer":"The request payload contains user data.","error_type":"subject-verb-agreement","explanation":"A singular subject such as ‘payload’ takes ‘contains’."},
            {"type":"TECHNICAL_EXPLANATION","prompt":"Explain why an idempotent request is safe to retry. Mention the request and its result.","answer":"","rubric_terms":["idempotent","request","result"],"error_type":"rest-explanation-clarity","explanation":"Define the property and connect it to the result of repeating a request."},
        ],
        "summary":{"strong":["HTTP vocabulary","Endpoint descriptions"],"needs_work":["Subject–verb agreement","Cause and result"],"new_words":["payload","idempotency","rate limiting"],"next_topic":"Authentication and authorization"},
    },
    {
        "key":"auth-explanations","title":"Authentication vs Authorization","skill_id":"tech.auth","duration":20,
        "objective":"Distinguish identity verification from access control in clear technical English.",
        "context":"You are explaining an access-control design during a code review.",
        "exercises":[
            {"type":"MULTIPLE_CHOICE","prompt":"What does authorization determine?","options":["What an authenticated user may access.","Whether the password is correctly typed.","How quickly the API responds."],"answer":"What an authenticated user may access.","error_type":"auth-concept-confusion","explanation":"Authentication verifies identity; authorization determines permissions."},
            {"type":"ERROR_CORRECTION","prompt":"Correct this sentence: “The user don't have permission to access this endpoint.”","answer":"The user doesn't have permission to access this endpoint.","error_type":"third-person-agreement","explanation":"Use ‘doesn’t’ with the third-person singular subject ‘user’."},
            {"type":"TECHNICAL_EXPLANATION","prompt":"Compare authentication and authorization in two sentences. Mention identity, permissions, and access.","answer":"","rubric_terms":["identity","permission","access"],"error_type":"auth-explanation-clarity","explanation":"A complete comparison covers identity first and permissions or access second."},
        ],
        "summary":{"strong":["Security terminology","Technical comparisons"],"needs_work":["Third-person agreement","Contrast markers"],"new_words":["identity","permission","access control"],"next_topic":"Daily stand-up communication"},
    },
    {
        "key":"standup-communication","title":"Effective Daily Stand-ups","skill_id":"professional.standup","duration":15,
        "objective":"Give a concise update about completed work, today’s plan, and blockers.",
        "context":"You have sixty seconds to update an international engineering team.",
        "exercises":[
            {"type":"MULTIPLE_CHOICE","prompt":"Which opening clearly reports completed work?","options":["Yesterday I fixed the connection-pool issue.","Yesterday I have fix connection pool.","Yesterday I am fixing it."],"answer":"Yesterday I fixed the connection-pool issue.","error_type":"standup-past-simple","explanation":"Use Past Simple for work completed yesterday."},
            {"type":"ERROR_CORRECTION","prompt":"Correct this sentence: “Today I working on the monitoring dashboard.”","answer":"Today I am working on the monitoring dashboard.","error_type":"missing-auxiliary","explanation":"Present Continuous needs the auxiliary verb ‘am’ with ‘I’."},
            {"type":"PROFESSIONAL_COMMUNICATION","prompt":"Write a three-part stand-up update: yesterday’s result, today’s plan, and your blocker or say that you have none.","answer":"","rubric_terms":["yesterday","today","blocker"],"error_type":"standup-structure","explanation":"A complete stand-up separates completed work, the next action, and blockers."},
        ],
        "summary":{"strong":["Concise updates","Past and present time frames"],"needs_work":["Auxiliary verbs","Explicit blockers"],"new_words":["blocker","connection pool","monitoring"],"next_topic":"B1 consolidation review"},
    },
]

LESSON_EXERCISES = B1_COURSE[0]["exercises"]
