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
const sessionId          = "trip-" + Math.random().toString(36).substring(2, 12);

// ── Markdown → HTML renderer (supports tables, blockquotes, lists) ──────────
function renderMarkdown(text) {
    if (!text) return "<p>Plan processed successfully.</p>";

    // Split into lines for table detection
    const lines = text.split("\n");
    let html = "";
    let i = 0;

    while (i < lines.length) {
        const line = lines[i];

        // Detect markdown table (|col|col| pattern)
        if (/^\|.+\|$/.test(line.trim()) && i + 1 < lines.length && /^\|[-| :]+\|$/.test(lines[i + 1].trim())) {
            html += "<table class='md-table'>";
            // Header row
            const headers = line.trim().split("|").filter(c => c.trim() !== "");
            html += "<thead><tr>" + headers.map(h => `<th>${processInline(h.trim())}</th>`).join("") + "</tr></thead>";
            i += 2; // skip header + separator
            html += "<tbody>";
            while (i < lines.length && /^\|.+\|$/.test(lines[i].trim())) {
                const cells = lines[i].trim().split("|").filter(c => c.trim() !== "");
                html += "<tr>" + cells.map(c => `<td>${processInline(c.trim())}</td>`).join("") + "</tr>";
                i++;
            }
            html += "</tbody></table>";
            continue;
        }

        // Blockquote
        if (/^> /.test(line)) {
            html += `<blockquote class='md-blockquote'>${processInline(line.slice(2))}</blockquote>`;
            i++; continue;
        }

        // HR
        if (/^---+$/.test(line.trim())) { html += "<hr class='md-hr'>"; i++; continue; }

        // Headings
        if (/^### /.test(line)) { html += `<h4>${processInline(line.slice(4))}</h4>`; i++; continue; }
        if (/^## /.test(line))  { html += `<h3>${processInline(line.slice(3))}</h3>`; i++; continue; }
        if (/^# /.test(line))   { html += `<h2>${processInline(line.slice(2))}</h2>`; i++; continue; }

        // List items
        if (/^[-•*] /.test(line.trim())) {
            html += "<ul>";
            while (i < lines.length && /^[-•*] /.test(lines[i].trim())) {
                html += `<li>${processInline(lines[i].trim().slice(2))}</li>`;
                i++;
            }
            html += "</ul>";
            continue;
        }

        // Paragraph
        if (line.trim()) {
            html += `<p>${processInline(line)}</p>`;
        }

        i++;
    }

    return html;
}

function processInline(text) {
    return text
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>")
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        .replace(/`(.+?)`/g, "<code>$1</code>");
}


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

let calendarAccessToken = null;
const GOOGLE_CLIENT_ID = "690192679158-3o5ule16jcnj0e5nv3if47mh2rfb9sm8.apps.googleusercontent.com"; // UPDATED!

travelForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = travelInput.value.trim();
    if (!message) return;

    // Trigger OAuth if we don't have a token, requires user gesture
    if (!calendarAccessToken && window.google) {
        const tokenClient = google.accounts.oauth2.initTokenClient({
            client_id: GOOGLE_CLIENT_ID,
            scope: "https://www.googleapis.com/auth/calendar.events",
            callback: (tokenResponse) => {
                if (tokenResponse && tokenResponse.access_token) {
                    calendarAccessToken = tokenResponse.access_token;
                    startTrip(message);
                }
            },
        });
        tokenClient.requestAccessToken();
    } else {
        startTrip(message);
    }
});

async function startTrip(message) {
    landingSection.classList.add("hidden");
    processingSection.classList.remove("hidden");
    submitBtn.disabled = true;
    btnLabel.textContent = "Planning…";
    btnArrow.classList.add("hidden");
    btnSpinner.classList.remove("hidden");

    AGENTS.forEach((a) => setChip(a, "idle"));
    loadingText.textContent = "Connecting to AI agents…";

    try {
        const payload = { message, session_id: sessionId };
        if (calendarAccessToken) {
            payload.calendar_token = calendarAccessToken;
        }

        const resp = await fetch("/api/chat_stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
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

                // ndjson (progress / result)
                if (line.startsWith("{")) {
                    try {
                        const data = JSON.parse(line);
                        if (data.type === "progress") {
                            loadingText.textContent = data.text;
                            for (const a of AGENTS) {
                                const kw = a.replace("_", " ").split(" ")[0];
                                if (data.text.toLowerCase().includes(kw) && !runningAgents.has(a)) {
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
                    } catch (_) { /* fall through */ }
                }

                // SSE events (data: ...)
                if (line.startsWith("data:")) {
                    const payload = line.slice(5).trim();
                    if (!payload || payload === "[DONE]") continue;
                    try {
                        const event   = JSON.parse(payload);
                        const author  = event.author  || "";
                        const content = event.content || {};
                        const text    = (content.parts || []).map(p => p.text || "").join("");

                        if (AGENTS.includes(author)) {
                            if (!runningAgents.has(author)) {
                                runningAgents.add(author);
                                setChip(author, "running");
                                loadingText.textContent = `${agentLabel(author)} is working…`;
                            }
                            if (text) {
                                setOutput(author, text);
                                setChip(author, "done");
                            }
                        }

                        if (author === "concierge_pipeline" && text) {
                            finalText = text;
                            AGENTS.forEach((a) => setChip(a, "done"));
                            showResult(finalText);
                        }
                    } catch (_) { /* ignore */ }
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
}

// ── Show result ──────────────────────────────────────────────────────────────

function showResult(text) {
    resultLoading.classList.add("hidden");
    resultText.innerHTML = renderMarkdown(text);
    resultDone.classList.remove("hidden");
    newTripBtn.classList.remove("hidden");
    livePill.innerHTML = '<span style="width:6px;height:6px;background:#34A853;border-radius:50%;display:inline-block;margin-right:4px;"></span> Complete';
    livePill.style.color      = "#34A853";
    livePill.style.background = "#E6F4EA";
}

function agentLabel(key) {
    return { logistics:"🛎️ Logistics", travel_researcher:"🔍 Travel Researcher",
             policy_auditor:"⚖️ Policy Auditor", accountant:"📝 Accountant" }[key] || key;
}

// ── Reset ────────────────────────────────────────────────────────────────────

function resetApp() {
    processingSection.classList.add("hidden");
    landingSection.classList.remove("hidden");
    travelInput.value    = "";
    submitBtn.disabled   = false;
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
    resultText.innerHTML    = "";
    loadingText.textContent = "Initializing agents…";
    newTripBtn.classList.add("hidden");
    livePill.innerHTML    = '<span class="live-dot"></span> Running';
    livePill.style.color  = "";
    livePill.style.background = "";
}