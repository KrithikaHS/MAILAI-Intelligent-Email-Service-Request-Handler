chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "set-alarm") {
    chrome.alarms.create("mailAIAlarm", {
      delayInMinutes: request.minutes,
      periodInMinutes: request.minutes
    });
  }

  if (request.type === "clear-alarm") {
    chrome.alarms.clear("mailAIAlarm");
  }
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "mailAIAlarm") {
    fetch("http://127.0.0.1:5001/main", {
      method: "POST"
    })
    .then(res => console.log("MailAI auto-triggered"))
    .catch(err => console.error("Auto-trigger failed:", err));
  }
});
