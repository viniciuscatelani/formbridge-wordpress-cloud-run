(() => {
  const form = document.querySelector("#dnd-registry-form");
  if (!form) return;

  const status = document.querySelector("#dnd-registry-status");
  const button = form.querySelector("button[type='submit']");
  let idempotencyKey = crypto.randomUUID();

  const modifier = (score) => Math.floor((Number(score) - 10) / 2);
  form.querySelectorAll("[data-modifier]").forEach((output) => {
    const input = form.elements[output.dataset.modifier];
    const update = () => {
      const value = modifier(input.value);
      output.textContent = `Modifier ${value >= 0 ? `+${value}` : value}`;
    };
    input.addEventListener("input", update);
    update();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const payload = {
      name: data.get("name"),
      player_name: data.get("player_name"),
      character_class: data.get("character_class"),
      level: Number(data.get("level")),
      alignment: data.get("alignment"),
      abilities: {
        strength: Number(data.get("strength")),
        dexterity: Number(data.get("dexterity")),
        constitution: Number(data.get("constitution")),
        intelligence: Number(data.get("intelligence")),
        wisdom: Number(data.get("wisdom")),
        charisma: Number(data.get("charisma")),
      },
      notes: data.get("notes"),
    };

    button.disabled = true;
    status.className = "";
    status.textContent = "Saving your adventurer…";

    try {
      const response = await fetch(dndRegistryConfig.endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Idempotency-Key": idempotencyKey,
        },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.message || "Submission failed.");

      status.className = "success";
      status.textContent = result.message;
      form.reset();
      form.querySelectorAll("[data-modifier]").forEach((output) => {
        output.textContent = "Modifier +0";
      });
      idempotencyKey = crypto.randomUUID();
    } catch (error) {
      status.className = "error";
      status.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
})();
