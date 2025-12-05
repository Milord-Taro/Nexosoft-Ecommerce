// ============================================================
// 1. PRODUCTOS EN LA TIENDA (BASE DE DATOS PROVISORIA)
// ============================================================
const productos = [
  {
    id: 1,
    titulo: "Taladro inalámbrico profesional",
    categoria: "Herramientas Eléctricas",
    vendedor: "ToolPro La Tusa",
    rating: 4.7,
    ventas: 825,
    precio: 300.000,
    imagen: "../taladro.png",

    descripcion:
      "Taladro potente con batería de litio, 2 velocidades y luz LED integrada. Incluye maletín y cargador rápido.",
    caracteristicas: [
      "Garantía de 1 año",
      "Envío gratis en pedidos superiores a $100",
      "Incluye 2 baterías recargables",
      "Velocidad variable con control preciso",
      "Ideal para uso doméstico y profesional"
    ],
    stock: "En stock"
  },
  {
    id: 2,
    titulo: "Sierra circular 7 1/4\" 1400W",
    categoria: "Herramientas Eléctricas",
    vendedor: "Ferretería El Ingeniero",
    rating: 4.5,
    ventas: 410,
    precio: 754.099,
    imagen: "../sierra.png",
    descripcion:
      "Sierra circular de alto rendimiento para cortes rectos en madera y tableros. Incluye guía paralela.",
    caracteristicas: [
      "Motor de 1400W",
      "Protección de seguridad en el disco",
      "Ajuste de profundidad y ángulo",
      "Cable reforzado de 2.5m"
    ],
    stock: "En stock"
  },

  // -------------------------
  // HERRAMIENTAS MANUALES
  // -------------------------
  {
    id: 3,
    titulo: "Juego de martillos carpintero (3 pzs)",
    categoria: "Herramientas Manuales",
    vendedor: "Ferretería El Ingeniero",
    rating: 4.6,
    ventas: 523,
    precio: 150.000,
    imagen: "../martillos.png",
    descripcion:
      "Set de 3 martillos con cabezas forjadas y mangos ergonómicos antideslizantes.",
    caracteristicas: [
      "Acero de alta resistencia",
      "Mangos antideslizantes",
      "Ideal para carpintería",
      "Peso balanceado"
    ],
    stock: "En stock"
  },
  {
    id: 4,
    titulo: "Martillo de uña clásico",
    categoria: "Herramientas Manuales",
    vendedor: "Efraín Herramientas",
    rating: 4.8,
    ventas: 412,
    precio: 24.500,
    imagen: "../otromartillo.png",
    descripcion:
      "Martillo tradicional con mango de fibra de vidrio y cabeza forjada.",
    caracteristicas: [
      "Mango anti-vibración",
      "Cabeza forjada",
      "Acabado resistente",
      "Equilibrio perfecto"
    ],
    stock: "En stock"
  },

  // -------------------------
  // PINTURA
  // -------------------------
  {
    id: 5,
    titulo: "Kit de rodillo y bandeja para pintura",
    categoria: "Pintura",
    vendedor: "Pinturas El Color",
    rating: 4.3,
    ventas: 310,
    precio: 75.40000,
    imagen: "../rodillo.png",
    descripcion:
      "Kit básico de pintura con rodillo de microfibra y bandeja resistente.",
    caracteristicas: ["Rodillo lavable", "Bandeja reforzada", "Ligero"],
    stock: "En stock"
  },
  {
    id: 6,
    titulo: "Juego de brochas profesionales (5 pzs)",
    categoria: "Pintura",
    vendedor: "Pinceles Premium",
    rating: 4.9,
    ventas: 189,
    precio: 54.700,
    imagen: "../pinceles.png",
    descripcion:
      "Conjunto de brochas de alta calidad con cerdas suaves.",
    caracteristicas: [
      "Cerdas premium",
      "Mango barnizado",
      "Para esmaltes y látex"
    ],
    stock: "En stock"
  },

  // -------------------------
  // ESCALERAS
  // -------------------------
  {
    id: 7,
    titulo: "Escalera de aluminio 6 peldaños",
    categoria: "Escaleras",
    vendedor: "Altura Segura",
    rating: 4.6,
    ventas: 142,
    precio: 500.000,
    imagen: "../escalera.png",
    descripcion:
      "Escalera liviana y resistente, perfecta para uso doméstico y profesional.",
    caracteristicas: [
      "Capacidad 120 kg",
      "Peldaños antideslizantes",
      "Certificación europea"
    ],
    stock: "En stock"
  },

  // -------------------------
  // MEDICIÓN
  // -------------------------
  {
    id: 8,
    titulo: "Cinta métrica 8 m con freno",
    categoria: "Medición",
    vendedor: "Meditec",
    rating: 4.5,
    ventas: 390,
    precio: 30.200,
    imagen: "../metro.png",
    descripcion:
      "Cinta métrica reforzada con sistema de freno y clip metálico.",
    caracteristicas: [
      "8 metros",
      "Recubrimiento anti-desgaste",
      "Carcasa resistente"
    ],
    stock: "En stock"
  },
  {
    id: 9,
    titulo: "Nivel láser de línea cruzada",
    categoria: "Medición",
    vendedor: "ProNivel",
    rating: 4.7,
    ventas: 95,
    precio: 250.000,
    imagen: "../laser.png",
    descripcion:
      "Nivel láser con proyección horizontal y vertical para alta precisión.",
    caracteristicas: [
      "Alcance 15 m",
      "Base magnética",
      "Bolsa acolchada"
    ],
    stock: "En stock"
  }
];

// ============================================================
// 2. CARRITO (CONTADOR BÁSICO)
// ============================================================
let cartCount = 0;

function addToCart() {
  cartCount++;
  const cartCountEl = document.getElementById("cartCount");
  if (cartCountEl) cartCountEl.textContent = cartCount;
}

// ============================================================
// 3. RENDERIZAR PRODUCTOS EN LA TIENDA
// ============================================================
const productsGrid = document.getElementById("productsGrid");

function renderProducts(categoria = "Todos") {
  if (!productsGrid) return;

  productsGrid.innerHTML = "";

  productos
    .filter((p) => categoria === "Todos" || p.categoria === categoria)
    .forEach((prod) => {
      const card = document.createElement("article");
      card.className = "product-card";

      card.innerHTML = `
        <div class="product-image-wrapper">
          <img src="${prod.imagen}" alt="${prod.titulo}">
        </div>

        <div class="product-body">
          <div class="product-header">
            <h3 class="product-title">${prod.titulo}</h3>
            <span class="product-tag">${prod.categoria}</span>
          </div>

          <div class="product-meta">${prod.vendedor} • ★ ${prod.rating}</div>

          <p class="product-desc">
            ${prod.descripcion.slice(0, 90)}${prod.descripcion.length > 90 ? "..." : ""}
          </p>

          <div class="product-price">$${prod.precio.toFixed(2)}</div>

          <button class="product-details-btn" data-id="${prod.id}">
            Ver detalles
          </button>
        </div>

        <button class="product-btn" data-add="${prod.id}">
          Agregar al carrito
        </button>
      `;

      productsGrid.appendChild(card);
    });
}

renderProducts();

// ============================================================
// 4. FILTRO DE CATEGORÍAS
// ============================================================
const categoryBar = document.getElementById("categoryBar");

if (categoryBar) {
  categoryBar.addEventListener("click", (e) => {
    const btn = e.target.closest(".category-pill");
    if (!btn) return;

    document
      .querySelectorAll(".category-pill")
      .forEach((p) => p.classList.remove("active"));

    btn.classList.add("active");

    renderProducts(btn.dataset.category);
  });
}

// ============================================================
// 5. MODAL DE PRODUCTOS
// ============================================================
const modal = document.getElementById("productModal");
const modalImg = document.getElementById("modalImage");
const modalTag = document.getElementById("modalCategory");
const modalTitle = document.getElementById("modalTitle");
const modalMeta = document.getElementById("modalMeta");
const modalPrice = document.getElementById("modalPrice");
const modalDesc = document.getElementById("modalDescription");
const modalFeatures = document.getElementById("modalFeatures");
const modalStock = document.getElementById("modalStockText");
const modalCloseBtn = document.getElementById("modalCloseBtn");

function openModal(id) {
  const p = productos.find((x) => x.id == id);
  if (!p) return;

  modalImg.src = p.imagen;
  modalTag.textContent = p.categoria;
  modalTitle.textContent = p.titulo;
  modalMeta.textContent = `${p.vendedor} • ★ ${p.rating} • ${p.ventas} ventas`;
  modalPrice.textContent = `$${p.precio.toFixed(2)}`;
  modalDesc.textContent = p.descripcion;
  modalStock.textContent = p.stock;

  modalFeatures.innerHTML = "";
  p.caracteristicas.forEach((c) => {
    const li = document.createElement("li");
    li.textContent = c;
    modalFeatures.appendChild(li);
  });

  modal.classList.remove("modal-hidden");
}

function closeModal() {
  modal.classList.add("modal-hidden");
}

modalCloseBtn.addEventListener("click", closeModal);

modal.addEventListener("click", (e) => {
  if (e.target === modal) closeModal();
});

// ============================================================
// 6. EVENTOS EN TARJETAS (delegación)
// ============================================================
productsGrid.addEventListener("click", (e) => {
  const btnDetails = e.target.closest(".product-details-btn");
  const btnAdd = e.target.closest(".product-btn");

  if (btnDetails) {
    const id = btnDetails.dataset.id;
    openModal(id);
  }

  if (btnAdd) {
    addToCart();
  }
});
