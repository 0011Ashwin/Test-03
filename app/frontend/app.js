/* Travel Concierge — app.js
   Clean Google-style UI for GenAI Academy ACAP · H2skill */

const AGENTS = ["logistics", "travel_researcher", "policy_auditor", "accountant"];

const travelForm         = document.getElementById("travel-form");
const travelInput        = document.getElementById("travel-input");
const submitBtn          = document.getElementById("submit-btn");
const btnLabel           = document.getElementById("btn-label");
const btnArrow           = document.getElementById("btn-arrow");
const btnSpinner         = document.getElementById("btn-spinner");
const landingSection     = document.getElementById("landing-section");
const processingSection  = document.getElementById("processing-section");
const resultLoading      = document.getElementById("result-loading");
const resultDone         = document.getElementById("result-done");
const resultText         = document.getElementById("result-text");
const loadingText        = document.getElementById("loading-text");
const newTripBtn         = document.getElementById("new-trip-btn");
const livePill           = document.getElementById("live-pill");

const sessionId = "trip-" + Math.random().toString(36).substring(2, 12);

// ── Chip helpers ────────────────────────────────────────────────────────────

function setChip(agent, state) {
    const chip = document.getElementById(`chip-${agent}`);
    const row  = document.getElementById(`row-${agent}`);
    if (!chip || !row) return;

    chip.className = "row-chip";
    row.classList.remove("active", "done");

    if (state === "running") {
        chip.classList.add("running");
        chip.textContent = "Running…";
        row.classList.add("active");
    } else if (state === "done") {
        chip.classList.add("done");
        chip.textContent = "✓ Done";
        row.classList.add("done");
    } else {
        chip.textContent = "Waiting";
    }
}

function setOutput(agent, text) {
    const el = document.getElementById(`out-${agent}`);
    if (!el || !text) return;
    el.textContent = text.slice(0, 250);
    el.classList.remove("hidden");
}

// ── Submit ──────────────────────────────────────────────────────────────────

travelForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = travelInput.value.trim();
    if (!message) return;

    // Show processing view
    landingSection.classList.add("hidden");
    processingSection.classList.remove("hidden");
    submitBtn.disabled = true;
    btnLabel.textContent = "Planning…";
    btnArrow.classList.add("hidden");
    btnSpinner.classList.remove("hidden");

    AGENTS.forEach((a) => setChip(a, "idle"));
    loadingText.textContent = "Connecting to AI agents…";

    try {
        const resp = await fetch("/api/chat_stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, session_id: sessionId }),
        });

        if (!resp.ok) throw new Error(`Server error ${resp.status}: ${await resp.text()}`);

        const reader  = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer    = "";
        let finalText = "";
        const runningAgents = new Set();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop();

            for (const raw of lines) {
                const line = raw.trim();
                if (!line) continue;

                // ── ndjson (progress / result) ──────────────────────────────
                if (line.startsWith("{")) {
                    try {
                        const data = JSON.parse(line);
                        if (data.type === "progress") {
                            loadingText.textContent = data.text;
                            // Activate the agent matching the message
                            for (const a of AGENTS) {
                                const keyword = a.replace("_", " ").split(" ")[0];
                                if (data.text.toLowerCase().includes(keyword) && !runningAgents.has(a)) {
                                    runningAgents.add(a);
                                    setChip(a, "running");
                                }
                            }
                        } else if (data.type === "result") {
                            finalText = data.text;
                            AGENTS.forEach((a) => setChip(a, "done"));
                            showResult(finalText);
                        }
                        continue;
                    } catch (_) { /* fall through to SSE */ }
                }

                // ── SSE (data: ...) ─────────────────────────────────────────
                if (line.startsWith("data:")) {
                    const payload = line.slice(5).trim();
                    if (!payload || payload === "[DONE]") continue;
                    try {
                        const event   = JSON.parse(payload);
                        const author  = event.author  || "";
                        const content = event.content || {};
                        const parts   = (content.parts || []);
                        const text    = parts.map((p) => p.text || "").join("");

                        if (AGENTS.includes(author)) {
                            if (!runningAgents.has(author)) {
                                runningAgents.add(author);
                                setChip(author, "running");
                                loadingText.textContent = `${agentLabel(author)} is working…`;
                            }
                            if (text) {
                                setOutput(author, text);
                                setChip(author, "done");
                                finalText = text;
                            }
                        }

                        if (author === "concierge_pipeline" && text) {
                            finalText = text;
                            AGENTS.forEach((a) => setChip(a, "done"));
                            showResult(finalText);
                        }
                    } catch (_) { /* ignore malformed */ }
                }
            }
        }

        if (finalText && resultDone.classList.contains("hidden")) {
            AGENTS.forEach((a) => setChip(a, "done"));
            showResult(finalText);
        }

    } catch (err) {
        console.error(err);
        loadingText.textContent = "Something went wrong: " + err.message;
        newTripBtn.classList.remove("hidden");
    }
});

// ── Show result ──────────────────────────────────────────────────────────────

function showResult(text) {
    resultLoading.classList.add("hidden");
    resultText.textContent = text;
    resultDone.classList.remove("hidden");
    newTripBtn.classList.remove("hidden");
    livePill.innerHTML = '<span style="width:6px;height:6px;background:#34A853;border-radius:50%;display:inline-block;margin-right:4px;"></span> Complete';
    livePill.style.color = "#34A853";
    livePill.style.background = "#E6F4EA";
}

// ── Agent label ─────────────────────────────────────────────────────────────

function agentLabel(key) {
    return {
        logistics:         "🛎️ Logistics",
        travel_researcher: "🔍 Travel Researcher",
        policy_auditor:    "⚖️ Policy Auditor",
        accountant:        "📝 Accountant",
    }[key] || key;
}

// ── Reset ────────────────────────────────────────────────────────────────────

function resetApp() {
    processingSection.classList.add("hidden");
    landingSection.classList.remove("hidden");

    travelInput.value   = "";
    submitBtn.disabled  = false;
    btnLabel.textContent = "Plan My Trip";
    btnArrow.classList.remove("hidden");
    btnSpinner.classList.add("hidden");

    AGENTS.forEach((a) => {
        setChip(a, "idle");
        const out = document.getElementById(`out-${a}`);
        if (out) { out.textContent = ""; out.classList.add("hidden"); }
    });

    resultLoading.classList.remove("hidden");
    resultDone.classList.add("hidden");
    resultText.textContent  = "";
    loadingText.textContent = "Initializing agents…";
    newTripBtn.classList.add("hidden");
    livePill.innerHTML = '<span class="live-dot"></span> Running';
    livePill.style.color = "";
    livePill.style.background = "";
}