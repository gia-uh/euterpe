(function () {
  if (!window.euterpeWidget) {
    var NAMES = ["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"];
    var N = 96;
    // The score part of a figure with a panel and a map: from the audio's time, which notes sound and where the cursor is.
    function scorePart(fig, au) {
      var panel = fig.querySelector(".eu-score"), json = fig.querySelector(".eu-map");
      if (!panel || !json) return null;
      var map = JSON.parse(json.textContent), svg = panel.querySelector("svg"), w = svg.viewBox.baseVal.width;
      var els = null, i = -1, lit = {}, line = null, places = [], row = null;
      function el(id) {
        if (!els) {
          els = {};
          svg.querySelectorAll("[id]").forEach(function (e) { els[e.id] = e; });
        }
        return els[id];
      }
      function light(id, on) {
        var e = el(id), up = e.parentNode, stem = up.classList.contains("chord") && up.querySelector(":scope>.stem");
        e.classList.toggle("eu-on", on);
        if (stem) stem.classList.toggle("eu-on", on);
        if (on) lit[id] = 1; else delete lit[id];
      }
      function box(e) {
        var s = svg.getBoundingClientRect(), r = e.getBoundingClientRect(), k = w / s.width;
        return { x: (r.left - s.left) * k, y0: (r.top - s.top) * k, y1: (r.bottom - s.top) * k };
      }
      // Where event k puts the cursor: the leftmost note it starts, in that note's system. An event that starts none keeps the last.
      function place(k) {
        if (places[k] === undefined) {
          var ids = map[k][1];
          if (ids.length) {
            var sys = el(ids[0]).closest("g.system");
            sys.euBox = sys.euBox || box(sys);
            places[k] = { x: Math.min.apply(null, ids.map(function (id) { return box(el(id)).x; })), sys: sys, t: map[k][0] };
          } else places[k] = k ? place(k - 1) : null;
        }
        return places[k];
      }
      function follow(x, sys) {
        var s = svg.getBoundingClientRect(), p = panel.getBoundingClientRect(), k = s.width / w, top = sys.euBox.y0 * k + s.top - p.top;
        if (sys !== row) {
          row = sys;
          if (top < 0 || sys.euBox.y1 * k + s.top - p.top > panel.clientHeight) panel.scrollTo({ top: panel.scrollTop + top - panel.clientHeight / 4, behavior: "smooth" });
        }
        var cx = x * k + s.left - p.left;
        if (cx < 0 || cx > panel.clientWidth * 0.9) panel.scrollLeft += cx - panel.clientWidth / 4;
      }
      panel.addEventListener("click", function (e) {
        for (var t = e.target; t && t !== panel; t = t.parentNode) {
          var best = null;
          map.forEach(function (ev) {
            if (ev[1].indexOf(t.id) >= 0 && (best === null || Math.abs(ev[0] - au.currentTime) < Math.abs(best - au.currentTime))) best = ev[0];
          });
          if (best !== null) { au.currentTime = best; return; }
        }
      });
      return function () {
        var now = au.currentTime, a = null, idle = au.ended || (au.paused && !now);
        if (idle || (i >= 0 && now < map[i][0])) {
          Object.keys(lit).forEach(function (id) { light(id, false); });
          i = -1;
        }
        if (!idle) {
          while (i + 1 < map.length && map[i + 1][0] <= now) {
            i++;
            map[i][2].forEach(function (id) { light(id, false); });
            map[i][1].forEach(function (id) { light(id, true); });
          }
          if (i >= 0) a = place(i);
        }
        if (line) line.style.display = a ? "" : "none";
        if (!a) return;
        var x = a.x, j = i + 1;
        while (j < map.length && !map[j][1].length) j++;
        if (j < map.length) {
          var b = place(j);
          if (b.sys === a.sys && b.x > a.x) x += (b.x - a.x) * Math.min(1, (now - a.t) / (b.t - a.t));
        }
        if (!line) {
          line = document.createElementNS("http://www.w3.org/2000/svg", "line");
          line.setAttribute("class", "eu-cursor");
          svg.appendChild(line);
        }
        var c = { x1: x, x2: x, y1: Math.max(0, a.sys.euBox.y0), y2: a.sys.euBox.y1 };
        Object.keys(c).forEach(function (k) { line.setAttribute(k, c[k].toFixed(1)); });
        follow(x, a.sys);
      };
    }
    window.euterpeWidget = function (fig) {
      if (fig.dataset.on) return;
      fig.dataset.on = "1";
      var au = fig.querySelector("audio"), dur = +fig.dataset.dur;
      var env = fig.querySelector("svg.eu-env"), spec = fig.querySelector("svg.eu-spec");
      var timed = fig.querySelectorAll("svg[data-x1]"), marks = fig.querySelectorAll(".eu-sp [data-t]");
      var live = spec.querySelector(".eu-live"), avg = spec.querySelector(".eu-avg"), pk = spec.querySelector(".eu-pk");
      var played = env.querySelector(".eu-played rect"), clock = env.querySelector(".eu-t");
      var ctx = null, an = null, bins = null, score = scorePart(fig, au);
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
        if (score) score();
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
