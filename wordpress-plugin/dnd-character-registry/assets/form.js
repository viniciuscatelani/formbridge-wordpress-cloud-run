(() => {
  const form = document.querySelector("#dnd-registry-form");
  if (!form) return;

  const status = document.querySelector("#dnd-registry-status");
  const button = form.querySelector("button[type='submit']");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const payload = {
      name: data.get("name"),
      character_class: data.get("character_class"),
      level: Number(data.get("level")),
      alignment: data.get("alignment"),
      notes: data.get("notes"),
    };

    button.disabled = true;
    status.className = "";
    status.textContent = "Saving your adventurer…";

    try {
      const response = await fetch(dndRegistryConfig.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.message || "Submission failed.");

      status.className = "success";
      status.textContent = result.message;
      form.reset();
    } catch (error) {
      status.className = "error";
      status.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
})();

