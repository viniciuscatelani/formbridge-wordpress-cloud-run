const form = document.querySelector("#character-form");
const statusMessage = document.querySelector("#form-status");
const submitButton = form.querySelector("button[type='submit']");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusMessage.className = "";
  statusMessage.textContent = "Saving your adventurer…";
  submitButton.disabled = true;

  const data = new FormData(form);
  const payload = {
    name: data.get("name"),
    character_class: data.get("character_class"),
    level: Number(data.get("level")),
    alignment: data.get("alignment"),
    notes: data.get("notes"),
  };

  try {
    const response = await fetch("/api/characters", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Something went wrong.");

    statusMessage.className = "success";
    statusMessage.textContent = result.message;
    form.reset();
  } catch (error) {
    statusMessage.textContent = error.message;
  } finally {
    submitButton.disabled = false;
  }
});

