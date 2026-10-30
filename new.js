// Marks files added within the last 14 days with [NEW].
(function () {
  var DAYS = 14;
  document.querySelectorAll("a[data-added]").forEach(function (a) {
    var d = new Date(a.getAttribute("data-added") + "T00:00:00");
    if (isNaN(d) || (Date.now() - d) / 864e5 > DAYS) return;
    var s = document.createElement("span");
    s.className = "new";
    s.textContent = " [NEW]";
    a.after(s);
  });
})();
