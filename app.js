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

createTabs();
