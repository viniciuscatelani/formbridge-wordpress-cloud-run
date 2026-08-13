<section class="dnd-registry" aria-labelledby="dnd-registry-title">
  <div class="dnd-registry__intro">
    <div class="dnd-registry__die" aria-hidden="true">20</div>
    <p class="dnd-registry__eyebrow">Adventurers' Guild · Est. 1492 DR</p>
    <h2 id="dnd-registry-title">Register your <span>next legend.</span></h2>
    <p>Enter your adventurer in the guild's local ledger.</p>
  </div>

  <form id="dnd-registry-form" class="dnd-registry__form">
    <label>
      Character name
      <input name="name" type="text" maxlength="80" required>
    </label>

    <label>
      Player name
      <input name="player_name" type="text" maxlength="80" placeholder="Who commands this hero?" required>
    </label>

    <div class="dnd-registry__row">
      <label>
        Class
        <select name="character_class" required>
          <option value="" selected disabled>Choose a class</option>
          <option>Barbarian</option><option>Bard</option><option>Cleric</option>
          <option>Druid</option><option>Fighter</option><option>Monk</option>
          <option>Paladin</option><option>Ranger</option><option>Rogue</option>
          <option>Sorcerer</option><option>Warlock</option><option>Wizard</option>
        </select>
      </label>
      <label>
        Level
        <input name="level" type="number" min="1" max="20" value="1" required>
      </label>
    </div>

    <label>
      Alignment
      <select name="alignment" required>
        <option value="" selected disabled>Choose an alignment</option>
        <option>Lawful Good</option><option>Neutral Good</option><option>Chaotic Good</option>
        <option>Lawful Neutral</option><option>True Neutral</option><option>Chaotic Neutral</option>
        <option>Lawful Evil</option><option>Neutral Evil</option><option>Chaotic Evil</option>
      </select>
    </label>

    <fieldset class="dnd-registry__abilities">
      <legend>Ability scores <small>1–20</small></legend>
      <div class="dnd-registry__ability-grid">
        <label>STR <input name="strength" type="number" min="1" max="20" value="10" required><output data-modifier="strength" aria-live="polite">Modifier +0</output></label>
        <label>DEX <input name="dexterity" type="number" min="1" max="20" value="10" required><output data-modifier="dexterity" aria-live="polite">Modifier +0</output></label>
        <label>CON <input name="constitution" type="number" min="1" max="20" value="10" required><output data-modifier="constitution" aria-live="polite">Modifier +0</output></label>
        <label>INT <input name="intelligence" type="number" min="1" max="20" value="10" required><output data-modifier="intelligence" aria-live="polite">Modifier +0</output></label>
        <label>WIS <input name="wisdom" type="number" min="1" max="20" value="10" required><output data-modifier="wisdom" aria-live="polite">Modifier +0</output></label>
        <label>CHA <input name="charisma" type="number" min="1" max="20" value="10" required><output data-modifier="charisma" aria-live="polite">Modifier +0</output></label>
      </div>
    </fieldset>

    <label>
      A note for the guild <small>Optional</small>
      <textarea name="notes" maxlength="500" rows="4"></textarea>
    </label>

    <button type="submit">Inscribe in the ledger <span aria-hidden="true">→</span></button>
    <p id="dnd-registry-status" role="status" aria-live="polite"></p>
  </form>
</section>
