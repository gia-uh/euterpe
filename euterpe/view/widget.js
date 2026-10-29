(function () {
  if (!window.euterpeWidget) {
    var NAMES = ["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"];
    var N = 96;
    window.euterpeWidget = function (fig) {
      if (fig.dataset.on) return;
      fig.dataset.on = "1";
      var au = fig.querySelector("audio"), dur = +fig.dataset.dur;
      var env = fig.querySelector("svg.eu-env"), spec = fig.querySelector("svg.eu-spec");
      var timed = fig.querySelectorAll("svg[data-x1]"), marks = fig.querySelectorAll("[data-t]");
      var live = spec.querySelector(".eu-live"), avg = spec.querySelector(".eu-avg"), pk = spec.querySelector(".eu-pk");
      var played = env.querySelector(".eu-played rect"), clock = env.querySelector(".eu-t");
      var ctx = null, an = null, bins = null;
      function place() {
        var now = au.currentTime || 0, t = Math.min(1, now / dur);
        timed.forEach(function (s) {
          var x0 = +s.dataset.x0, x = x0 + t * (+s.dataset.x1 - x0);
          s.querySelectorAll(".eu-ph").forEach(function (p) { p.setAttribute("transform", "translate(" + x.toFixed(1) + ",0)"); });
          if (s === env) played.setAttribute("width", (x - x0).toFixed(1));
        });
        clock.textContent = now > 0 || !au.paused ? now.toFixed(2) + " s" : "";
        marks.forEach(function (m) {
          var on = !au.paused && now >= +m.dataset.t && now < +m.dataset.t + 0.15;
          if (!m.dataset.f) m.dataset.f = m.getAttribute("fill");
          m.setAttribute("fill", on ? "#b0361f" : m.dataset.f);
        });
      }
      function spectrum() {
        an.getFloatFrequencyData(bins);
        var hz = ctx.sampleRate / an.fftSize, d = "", best = 1e9, bx = 0, bf = 0;
        for (var i = 0; i < N; i++) {
          var f = 20 * Math.pow(1000, i / (N - 1)), k = f / hz, m = -200;
          for (var j = Math.max(1, Math.round(k / 1.03)); j <= Math.min(bins.length - 1, Math.round(k * 1.03)); j++) if (bins[j] > m) m = bins[j];
          var x = 4 + 192 * i / (N - 1), y = 4 + 58 * (1 - Math.min(1, Math.max(0, (m + 100) / 90)));
          d += (i ? "L" : "M") + x.toFixed(1) + "," + y.toFixed(1);
          if (y < best) { best = y; bx = x; bf = f; }
        }
        live.setAttribute("d", d);
        var n = Math.round(69 + 12 * Math.log2(bf / 440));
        pk.style.display = best < 60 ? "" : "none";
        pk.querySelector("circle").setAttribute("cx", bx.toFixed(1));
        pk.querySelector("circle").setAttribute("cy", best.toFixed(1));
        var label = pk.querySelector("text");
        label.setAttribute("x", Math.min(bx + 4, 140).toFixed(1));
        label.setAttribute("y", Math.max(10, best - 3).toFixed(1));
        label.textContent = Math.round(bf) + " Hz · " + NAMES[((n % 12) + 12) % 12] + (Math.floor(n / 12) - 1);
      }
      function frame() {
        place();
        if (an) spectrum();
        if (!au.paused) requestAnimationFrame(frame);
      }
      function still() {
        place();
        live.style.display = pk.style.display = "none";
        avg.style.display = "";
      }
      au.addEventListener("play", function () {
        document.querySelectorAll("figure.euterpe-widget audio").forEach(function (o) { if (o !== au) o.pause(); });
        if (!ctx) {
          try {
            ctx = new (window.AudioContext || window.webkitAudioContext)();
            an = ctx.createAnalyser();
            an.fftSize = 4096;
            an.smoothingTimeConstant = 0.75;
            bins = new Float32Array(an.frequencyBinCount);
            ctx.createMediaElementSource(au).connect(an).connect(ctx.destination);
          } catch (e) { an = null; }
        }
        if (ctx && ctx.state === "suspended") ctx.resume();
        if (an) { live.style.display = ""; avg.style.display = "none"; }
        frame();
      });
      au.addEventListener("pause", still);
      au.addEventListener("ended", still);
      au.addEventListener("seeked", place);
      var drag = false;
      function seek(e) {
        var r = env.getBoundingClientRect(), x0 = +env.dataset.x0, x1 = +env.dataset.x1;
        var x = (e.clientX - r.left) / r.width * env.viewBox.baseVal.width;
        au.currentTime = Math.min(1, Math.max(0, (x - x0) / (x1 - x0))) * dur;
        place();
      }
      env.addEventListener("pointerdown", function (e) { drag = true; env.setPointerCapture(e.pointerId); seek(e); });
      env.addEventListener("pointermove", function (e) { if (drag) seek(e); });
      env.addEventListener("pointerup", function () { drag = false; });
      still();
    };
  }
  document.querySelectorAll("figure.euterpe-widget").forEach(window.euterpeWidget);
})();
