var hamBurger = document.querySelector(".toggle-btn");
var sidebar = document.querySelector("#sidebar");
var mainContent = document.querySelector("#contenido_principal");

hamBurger.addEventListener("click", function () {
  sidebar.classList.toggle("expand");
});

mainContent.addEventListener("click", function () {
  if (sidebar.classList.contains("expand")) {
    sidebar.classList.remove("expand");
  }
});
