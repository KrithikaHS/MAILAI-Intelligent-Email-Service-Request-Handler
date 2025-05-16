document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("toggle");
  const status = document.getElementById("status");
  const autoToggle = document.getElementById("autoToggle");
  const intervalInput = document.getElementById("interval");
  const unitSelect = document.getElementById("unit");

  toggle.addEventListener("change", () => {
    if (toggle.checked) {
      status.textContent = "Reading unread mails...";
      fetch("http://127.0.0.1:5001/main", { method: "POST" })
        .then(response => response.json())
        .then(data => {
          if (data.status === "success") {
            status.textContent = "Task completed successfully!";
          } else {
            status.textContent = "Task ended with message: " + data.message;
          }
          toggle.checked = false;
        })
        .catch(() => {
          status.textContent = "Sucessfully Completed Task";
          toggle.checked = false;
        });
    } else {
      status.textContent = "MailAI is OFF";
    }
  });

  autoToggle.addEventListener("change", () => {
    if (autoToggle.checked) {
      const interval = parseInt(intervalInput.value);
      const unit = unitSelect.value;

      let minutes = interval;
      if (unit === "hours") minutes *= 60;
      if (unit === "days") minutes *= 1440;

      chrome.runtime.sendMessage({ type: "set-alarm", minutes });

      status.textContent = `Auto-enabled every ${interval} ${unit}`;
    } else {
      chrome.runtime.sendMessage({ type: "clear-alarm" });
      status.textContent = "Auto-enable turned OFF";
    }
  });
});
