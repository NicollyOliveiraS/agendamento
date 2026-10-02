(function () {
  "use strict";

  // Menu de navegação em telas pequenas
  const toggle = document.getElementById("nav-toggle");
  const nav = document.getElementById("admin-nav");

  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const isOpen = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });
  }

  // Alterna a linha de edição inline na tabela de serviços
  document.querySelectorAll(".js-edit-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.dataset.target;
      const row = document.getElementById(targetId);
      if (!row) return;
      row.style.display = row.style.display === "none" ? "table-row" : "none";
    });
  });
})();
