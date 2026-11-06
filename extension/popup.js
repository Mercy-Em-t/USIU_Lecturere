document.getElementById("openHubBtn").addEventListener("click", () => {
  chrome.tabs.create({ url: "http://127.0.0.1:8085/" });
});

document.getElementById("openBbBtn").addEventListener("click", () => {
  chrome.tabs.create({ url: "https://blackboard.usiu.ac.ke/" });
});
