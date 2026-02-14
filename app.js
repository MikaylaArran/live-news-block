const YT_API_KEY = "AIzaSyAVR2WX1JGHOlxkXu2FJ6RlH12MppWfWpg";

const CHANNELS = [
  { name: "SKY NEWS", channelId: "UCoMdktPbSTixAyNGwb-UYkQ" },
  { name: "NBC NEWS", channelId: "UCeY0bbntWzzVIaj2z3QigXg" },
  { name: "CBS NEWS", channelId: "UC8p1vwvWtl6T73JiExfWs1g" },
  { name: "ABC NEWS", channelId: "UCBi2mrWuNuyYy4gbM6fU18Q" },
  { name: "DW NEWS", channelId: "UCknLrEdhRCp1aegoMqRaCZg" },
  { name: "AL JAZEERA", channelId: "UCNye-wNBqNL5ZzHSJj3l8Bg" },
  { name: "FRANCE 24", channelId: "UCQfwfsi5VrQ8yKZ-UWmAEFg" },
  { name: "EURONEWS", channelId: "UCSrZ3UV4jOidv8ppoVuvW9Q" }
];

const tabs = document.getElementById("tabs");
const player = document.getElementById("player");

async function fetchLiveVideo(channelId) {
  const url =
    "https://www.googleapis.com/youtube/v3/search" +
    "?part=snippet" +
    "&channelId=" + channelId +
    "&eventType=live" +
    "&type=video" +
    "&key=" + YT_API_KEY;

  try {
    const res = await fetch(url);
    const data = await res.json();

    if (data.items && data.items.length > 0) {
      return data.items[0].id.videoId;
    } else {
      return null;
    }
  } catch (e) {
    console.error("YouTube API error:", e);
    return null;
  }
}

function setPlayer(videoId) {
  player.src =
    "https://www.youtube.com/embed/" +
    videoId +
    "?autoplay=1&mute=1&playsinline=1";
}

function activateTab(tabEl) {
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  tabEl.classList.add("active");
}

async function createTabs() {
  for (const ch of CHANNELS) {
    const tab = document.createElement("div");
    tab.className = "tab";
    tab.innerText = ch.name;
    tabs.appendChild(tab);

    tab.onclick = async () => {
      activateTab(tab);
      const videoId = await fetchLiveVideo(ch.channelId);

      if (videoId) {
        setPlayer(videoId);
      } else {
        player.src = "";
        alert("No live stream right now for " + ch.name);
      }
    };
  }

  // auto-load first channel
  const firstTab = tabs.children[0];
  activateTab(firstTab);
  const firstVideo = await fetchLiveVideo(CHANNELS[0].channelId);
  if (firstVideo) setPlayer(firstVideo);
}
}

// ============================
// TOP NEWS: load data/top_news.json
// ============================
async function loadTopNewsFromJson() {
  // IMPORTANT: your index.html must have an element like:
  // <div id="top-news-list"></div>
  const el = document.getElementById("top-news-list");
  if (!el) {
    console.warn("Missing #top-news-list element in HTML.");
    return;
  }

  // show loading state
  el.innerHTML = "Loading news...";

  try {
    // GitHub Pages friendly: RELATIVE path (no leading slash)
    const res = await fetch("data/top_news.json", { cache: "no-store" });
    if (!res.ok) throw new Error("top_news.json not found (HTTP " + res.status + ")");

    const data = await res.json();

    // support either {items: []} or {results: []}
    const items = (data.items || data.results || []).slice(0, 10);

    if (!items.length) {
      el.innerHTML = "No news yet.";
      return;
    }

    el.innerHTML = items.map(n => {
      const title = escapeHtml(n.title || "Untitled");
      const url = n.url || n.link || "";
      const source = escapeHtml(n.source || n.source_id || "");
      const pub = escapeHtml(n.published_at || n.pubDate || "");

      return `
        <div class="news-item">
          <div class="news-title">${title}</div>
          <div class="news-meta">${pub}${source ? " | " + source : ""}</div>
          ${url ? `<a href="${url}" target="_blank" rel="noopener noreferrer">Open article</a>` : ""}
        </div>
      `;
    }).join("");
  } catch (e) {
    console.error("Top news load error:", e);
    el.innerHTML = `
      <div>
        <div style="font-weight:600;">Top news data not found.</div>
        <div style="opacity:.7;font-size:12px;margin-top:4px;">
          Make sure <code>data/top_news.json</code> exists, then refresh.
        </div>
      </div>
    `;
  }
}

// tiny helper to prevent HTML injection in titles/sources
function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// ============================
// INIT
// ============================
createTabs();
loadTopNewsFromJson();

// Optional: auto-refresh Top News every 15 minutes
// setInterval(loadTopNewsFromJson, 15 * 60 * 1000);
createTabs();
