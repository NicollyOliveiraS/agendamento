(function () {
  "use strict";

  const form = document.getElementById("booking-form");
  if (!form) return;

  const dateInput = document.getElementById("date");
  const slotsContainer = document.getElementById("slots-container");
  const timeInput = document.getElementById("time");
  const serviceId = form.dataset.serviceId;
  const availabilityUrl = form.dataset.availabilityUrl;

  function markSelected(button) {
    document.querySelectorAll(".slot-btn").forEach((b) => b.classList.remove("selected"));
    button.classList.add("selected");
    timeInput.value = button.dataset.time;
  }

  function attachSlotHandlers() {
    document.querySelectorAll(".slot-btn").forEach((btn) => {
      btn.addEventListener("click", () => markSelected(btn));
      if (btn.dataset.time === timeInput.value) {
        markSelected(btn);
      }
    });
  }

  async function loadSlots(date) {
    if (!date) return;

    slotsContainer.innerHTML = '<p class="slots-empty">Carregando horários...</p>';
    timeInput.value = "";

    try {
      const response = await fetch(`${availabilityUrl}?service_id=${encodeURIComponent(serviceId)}&date=${encodeURIComponent(date)}`);
      const data = await response.json();

      if (!response.ok || !data.slots) {
        slotsContainer.innerHTML = `<p class="slots-empty">${data.error || "Não foi possível carregar os horários."}</p>`;
        return;
      }

      if (data.slots.length === 0) {
        slotsContainer.innerHTML = '<p class="slots-empty">Nenhum horário disponível nessa data. Escolha outra data.</p>';
        return;
      }

      const grid = document.createElement("div");
      grid.className = "slots-grid";
      grid.id = "slots-grid";

      data.slots.forEach((time) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "slot-btn";
        btn.dataset.time = time;
        btn.textContent = time;
        grid.appendChild(btn);
      });

      slotsContainer.innerHTML = "";
      slotsContainer.appendChild(grid);
      attachSlotHandlers();
    } catch (err) {
      slotsContainer.innerHTML = '<p class="slots-empty">Erro de conexão. Tente novamente.</p>';
    }
  }

  dateInput.addEventListener("change", () => loadSlots(dateInput.value));

  // Se a página já veio com slots renderizados (ex.: reenvio após erro), liga os handlers
  attachSlotHandlers();

  form.addEventListener("submit", (event) => {
    if (!timeInput.value) {
      event.preventDefault();
      alert("Selecione um horário disponível antes de continuar.");
    }
  });
})();
