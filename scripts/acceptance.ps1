param([string]$BaseUrl = 'http://127.0.0.1:5173/api/v1')

$ErrorActionPreference = 'Stop'
$email = 'acceptance-' + [guid]::NewGuid().ToString('N') + '@example.com'
$registration = Invoke-RestMethod -Method Post -Uri "$BaseUrl/auth/register" -ContentType application/json -Body (@{
    email = $email; password = 'Acceptance123!'; display_name = 'Acceptance Learner'
} | ConvertTo-Json)
$headers = @{ Authorization = 'Bearer ' + $registration.access_token }
Invoke-RestMethod -Method Put -Uri "$BaseUrl/onboarding" -Headers $headers -ContentType application/json -Body (@{
    native_language = 'Russian'; target_cefr = 'B2'; specialization = 'Backend'; experience_level = 'Middle'
    technologies = @('Python', 'FastAPI'); professional_goals = @('Technical interviews')
    daily_learning_minutes = 20; preferred_exercise_types = @('lessons')
} | ConvertTo-Json) | Out-Null

$assessment = Invoke-RestMethod -Method Post -Uri "$BaseUrl/assessment/start" -Headers $headers
$assessmentId = $assessment.assessment_id
$question = $assessment.question
$placementAnswers = @(
    'We deployed it yesterday.', 'It is a throughput.', 'How a password is hashed',
    'Rate limiting was triggered', 'Yesterday I fixed a bug. Today I will test it.',
    'Authentication checks identity. Authorization controls access.',
    'I fixed a slow query and improved API latency.'
)
foreach ($answer in $placementAnswers) {
    $assessment = Invoke-RestMethod -Method Post -Uri "$BaseUrl/assessment/answer" -Headers $headers -ContentType application/json -Body (@{
        assessment_id = $assessmentId; item_key = $question.key; answer = $answer
    } | ConvertTo-Json)
    if (-not $assessment.completed) { $question = $assessment.question }
}
if (-not $assessment.completed -or $assessment.result.cefr -ne 'B1') {
    throw "Expected B1 placement: $($assessment | ConvertTo-Json -Compress)"
}

$before = (Invoke-RestMethod -Uri "$BaseUrl/skills" -Headers $headers).items
$answers = @{
    0 = @('WRONG', 'I deployed the fix yesterday.', 'We deployed the API and it worked; no rollback was needed.', 'We deployed to production this morning.')
    1 = @('The endpoint returns 404 when the resource does not exist.', 'The request payload contains user data.', 'An idempotent request is safe to retry because repeating the request produces the same result.')
    2 = @('WRONG', 'WRONG', 'Too short', 'What an authenticated user may access.', "The user doesn't have permission to access this endpoint.", 'Authentication verifies identity. Authorization determines permissions and access.')
    3 = @('Yesterday I fixed the connection-pool issue.', 'Today I am working on the monitoring dashboard.', 'Yesterday fixed.', 'Yesterday I fixed the connection pool; today I will add monitoring; I have no blocker.')
}
$keys = @('deployment-updates', 'rest-explanations', 'auth-explanations', 'standup-communication')
$expectedSteps = @(4, 3, 6, 4)
$lessons = @()
for ($module = 0; $module -lt 4; $module++) {
    $lesson = Invoke-RestMethod -Method Post -Uri "$BaseUrl/lessons/start" -Headers $headers
    if ($lesson.course_key -ne $keys[$module]) { throw "Unexpected module $($lesson.course_key)" }
    $answerIndex = 0
    while ($lesson.status -eq 'active') {
        $response = Invoke-RestMethod -Method Post -Uri "$BaseUrl/lessons/$($lesson.id)/answer" -Headers $headers -ContentType application/json -Body (@{
            answer = $answers[$module][$answerIndex]
        } | ConvertTo-Json)
        $lesson = $response.lesson
        $answerIndex++
        if ($answerIndex -gt 8) { throw 'Lesson retry loop detected' }
    }
    if ($lesson.total_steps -ne $expectedSteps[$module]) { throw "Unexpected step count for $($lesson.course_key)" }
    $lessons += [pscustomobject]@{ key = $lesson.course_key; steps = $lesson.total_steps; retries = $lesson.summary.retry_queue.Count }
}

$progress = Invoke-RestMethod -Uri "$BaseUrl/progress" -Headers $headers
$plan = Invoke-RestMethod -Uri "$BaseUrl/learning-plan" -Headers $headers
if ($progress.course_completed -ne 4 -or ($plan.days | Where-Object { -not $_.done })) { throw 'Course progress is inconsistent' }

$vocabulary = (Invoke-RestMethod -Uri "$BaseUrl/vocabulary" -Headers $headers).items
$latency = $vocabulary | Where-Object term -eq 'latency'
$rollback = $vocabulary | Where-Object term -eq 'rollback'
$goodReview = Invoke-RestMethod -Method Post -Uri "$BaseUrl/vocabulary/$($latency.id)/review" -Headers $headers -ContentType application/json -Body (@{
    recall_answer = 'latency'; context_sentence = 'We reduced API latency by adding a database index.'
} | ConvertTo-Json)
$badReview = Invoke-RestMethod -Method Post -Uri "$BaseUrl/vocabulary/$($rollback.id)/review" -Headers $headers -ContentType application/json -Body (@{
    recall_answer = 'undo'; context_sentence = 'The release failed.'
} | ConvertTo-Json)
if ($goodReview.quality -lt 3 -or $badReview.quality -ge 3) { throw 'Vocabulary scoring is inconsistent' }

$tutor1 = Invoke-WebRequest -Method Post -Uri "$BaseUrl/tutor/stream" -Headers $headers -ContentType application/json -Body (@{
    session_id = $null; message = 'I have deployed the fix yesterday.'; mode = 'free_conversation'
} | ConvertTo-Json)
$sessionMatch = [regex]::Match($tutor1.Content, 'session_id["\s:]+([0-9a-f-]+)')
if (-not $sessionMatch.Success) { throw 'Tutor session id is missing' }
$sessionId = $sessionMatch.Groups[1].Value
$null = Invoke-WebRequest -Method Post -Uri "$BaseUrl/tutor/stream" -Headers $headers -ContentType application/json -Body (@{
    session_id = $sessionId; message = 'Explain authentication and authorization.'; mode = 'free_conversation'
} | ConvertTo-Json)
$tutor3 = Invoke-WebRequest -Method Post -Uri "$BaseUrl/tutor/stream" -Headers $headers -ContentType application/json -Body (@{
    session_id = $sessionId; message = 'How are they different in an API?'; mode = 'free_conversation'
} | ConvertTo-Json)
function Get-TutorText([string]$content) {
    $tokens = foreach ($line in ($content -split "`n")) {
        if ($line.StartsWith('data: ')) {
            $payload = $line.Substring(6) | ConvertFrom-Json
            if ($null -ne $payload.token) { $payload.token }
        }
    }
    return $tokens -join ''
}
$tutor1Text = Get-TutorText $tutor1.Content
$tutor3Text = Get-TutorText $tutor3.Content
if ($tutor1Text -notmatch 'I deployed the fix yesterday' -or $tutor3Text -notmatch 'Authentication' -or $tutor3.Content -notmatch 'event: done') {
    throw 'Tutor correction, context, or stream completion failed'
}

# A failed review must be recorded and finish the lesson, not create an infinite retry loop.
$failedReviewLesson = Invoke-RestMethod -Method Post -Uri "$BaseUrl/lessons/start" -Headers $headers
$failedReviewAnswers = @('WRONG', 'I deployed the fix yesterday.', 'We deployed the API; no rollback was needed.', 'STILL WRONG')
foreach ($answer in $failedReviewAnswers) {
    $failedReviewResponse = Invoke-RestMethod -Method Post -Uri "$BaseUrl/lessons/$($failedReviewLesson.id)/answer" -Headers $headers -ContentType application/json -Body (@{ answer = $answer } | ConvertTo-Json)
    $failedReviewLesson = $failedReviewResponse.lesson
}
if ($failedReviewLesson.status -ne 'completed' -or $failedReviewLesson.total_steps -ne 4 -or $failedReviewResponse.requeued) {
    throw 'A failed review did not terminate correctly'
}
$completedSubmitStatus = 0
try {
    Invoke-RestMethod -Method Post -Uri "$BaseUrl/lessons/$($failedReviewLesson.id)/answer" -Headers $headers -ContentType application/json -Body (@{ answer = 'duplicate' } | ConvertTo-Json) | Out-Null
} catch {
    $completedSubmitStatus = [int]$_.Exception.Response.StatusCode
}
if ($completedSubmitStatus -ne 409) { throw "Expected 409 after completed lesson, received $completedSubmitStatus" }

$after = (Invoke-RestMethod -Uri "$BaseUrl/skills" -Headers $headers).items
$errors = (Invoke-RestMethod -Uri "$BaseUrl/errors" -Headers $headers).items
$skillIds = @{ 'deployment-updates' = 'tech.deployment'; 'rest-explanations' = 'tech.rest'; 'auth-explanations' = 'tech.auth'; 'standup-communication' = 'professional.standup' }
[pscustomobject]@{
    placement = [pscustomobject]@{ questions = 7; cefr = $assessment.result.cefr; dimensions = $assessment.result.dimensions }
    lessons = $lessons
    progress = [pscustomobject]@{ modules = "$($progress.course_completed)/$($progress.course_total)"; lessons = $progress.completed_lessons; achievement = $progress.achievements -contains 'B1 core course completed' }
    vocabulary = [pscustomobject]@{ correct_quality = $goodReview.quality; incorrect_quality = $badReview.quality }
    tutor = [pscustomobject]@{ correction = $tutor1Text -match 'I deployed the fix yesterday'; context = $tutor3Text -match 'Authentication'; done = $tutor3.Content -match 'event: done' }
    failed_review = [pscustomobject]@{ completed = $failedReviewLesson.status -eq 'completed'; steps = $failedReviewLesson.total_steps; duplicate_submit_status = $completedSubmitStatus }
    mastery = @($keys | ForEach-Object { $id = $skillIds[$_]; [pscustomobject]@{ skill = $id; before = ($before | Where-Object id -eq $id).mastery; after = ($after | Where-Object id -eq $id).mastery } })
    errors = @($errors.type)
} | ConvertTo-Json -Depth 7
