function toggleSidebar(){
  document.getElementById("sidebar").classList.toggle("open");
}
setTimeout(()=>{
  document.querySelectorAll(".alert").forEach(a=>{
    if(!a.classList.contains("danger")) setTimeout(()=>a.remove(),4000);
  });
}, 500);
document.addEventListener("keydown", e=>{
  if(e.key === "Escape") document.getElementById("sidebar")?.classList.remove("open");
});
