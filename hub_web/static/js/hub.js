// Filtres de la page projets : type (Académique / Personnel) + une technologie.
(() => {
  const state = { type: "", stack: "" };

  const cards = [...document.querySelectorAll(".infobox")];
  const sections = [...document.querySelectorAll(".hub-section")];
  const empty = document.getElementById("hub-empty");

  function apply() {
    cards.forEach((card) => {
      const okType = !state.type || card.dataset.type === state.type;
      const okStack = !state.stack || card.dataset.stack.split("|").includes(state.stack);
      card.hidden = !(okType && okStack);
    });

    let visible = 0;
    sections.forEach((section) => {
      const n = section.querySelectorAll(".infobox:not([hidden])").length;
      section.hidden = n === 0;
      visible += n;
    });
    empty.hidden = visible > 0;
  }

  document.querySelectorAll(".filter-row").forEach((row) => {
    const key = row.dataset.filter;
    row.addEventListener("click", (e) => {
      const btn = e.target.closest(".chip");
      if (!btn) return;

      // Re-cliquer sur la technologie active la désactive.
      const value = key === "stack" && state.stack === btn.dataset.value ? "" : btn.dataset.value;
      state[key] = value;

      row.querySelectorAll(".chip").forEach((c) => {
        const on = c.dataset.value === value && !(key === "stack" && value === "");
        c.classList.toggle("is-active", key === "type" ? c.dataset.value === value : on);
        c.setAttribute("aria-pressed", String(c.classList.contains("is-active")));
      });
      apply();
    });
  });
})();
