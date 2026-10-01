"use strict";
window.WorkspaceBenchmarks = (() => {
  const $ = id => document.getElementById(id);
  const node = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };
  const money = n => n === null ? "Unknown" : `$${n.toLocaleString(undefined, {maximumFractionDigits:5})}`;
  const seconds = n => n === null ? "Unknown" : n < 60 ? `${n.toFixed(1)} s` : `${(n / 60).toFixed(2)} min`;
  const percent = n => `${Math.round(n * 100)}%`;
  const title = row => `${row.agent} / ${row.model}${row.settings.reasoning_effort ? ` · ${row.settings.reasoning_effort}` : " · default effort"}`;
  let selected = "";
  let chartMode = "quality-time";

  function table(headers, entries) {
    const t = node("table", undefined, "benchmark-table"), h = node("thead"), r = node("tr"), body = node("tbody");
    for (const text of headers) r.append(node("th", text));
    h.append(r); t.append(h, body);
    for (const cells of entries) {
      const row = node("tr");
      for (const value of cells) {
        const cell = node("td");
        cell.append(value instanceof Node ? value : node("span", value));
        row.append(cell);
      }
      body.append(row);
    }
    return t;
  }

  function empty(titleText, detail) {
    const n = node("div", undefined, "benchmark-empty");
    n.append(node("span", "↗", "benchmark-empty-icon"), node("h3", titleText), node("p", detail));
    return n;
  }

  function scatter(rows) {
    const quality = chartMode === "quality-time";
    const points = rows.filter(r => quality ? r.mean_trial_seconds !== null : r.api_tokens_usd_per_success !== null && r.seconds_per_success !== null);
    const target = $("benchmark-tradeoff");
    target.replaceChildren();
    if (!points.length) {
      target.append(empty(quality ? "Compare verified quality and elapsed time" : "Tradeoffs need measured usage and timing", quality ? "Import fresh timed grades to compare configurations, including unsuccessful attempts." : "Missing cost stays unknown. Complete timed trial metadata will place configurations here."));
      return;
    }
    const ns = "http://www.w3.org/2000/svg";
    const svgNode = (tag, attrs, text) => {
      const n = document.createElementNS(ns, tag);
      for (const [k,v] of Object.entries(attrs || {})) n.setAttribute(k, String(v));
      if (text !== undefined) n.textContent = text;
      return n;
    };
    const svg = svgNode("svg", {viewBox:"0 0 760 290", role:"img", "aria-label":quality ? "Verified pass rate and mean elapsed time per trial. Includes failed attempts; upper left is more reliable and faster." : "API token cost and elapsed time per verified success. Includes failed attempts; lower left is cheaper and faster. Pass rate is a third Pareto objective."});
    const xvalue = r => quality ? r.mean_trial_seconds : r.api_tokens_usd_per_success;
    const yvalue = r => quality ? r.pass_rate : r.seconds_per_success;
    const xmax = Math.max(...points.map(xvalue), 0.000001) * 1.15;
    const ymax = quality ? 1 : Math.max(...points.map(yvalue), 1) * 1.15;
    for (let i=0; i<=4; i++) {
      const x = 85 + i * 150, y = 240 - i * 50;
      svg.append(svgNode("line", {x1:x,x2:x,y1:40,y2:240,class:"benchmark-gridline"}));
      svg.append(svgNode("line", {x1:85,x2:685,y1:y,y2:y,class:"benchmark-gridline"}));
      svg.append(svgNode("text", {x,y:263,"text-anchor":"middle"}, quality ? seconds(i*xmax/4) : money(i*xmax/4)));
      svg.append(svgNode("text", {x:73,y:y+4,"text-anchor":"end"}, quality ? percent(i*ymax/4) : seconds(i*ymax/4)));
    }
    svg.append(svgNode("text", {x:385,y:285,"text-anchor":"middle"}, quality ? "Mean trial time (includes failures)" : "API token $ / verified success"));
    svg.append(svgNode("text", {x:85,y:20}, quality ? "Verified pass rate" : "Elapsed time / verified success"));
    points.forEach(row => {
      const frontier = quality ? row.pareto_quality_time : row.pareto;
      const dot = svgNode("circle", {
        cx:85+600*xvalue(row)/xmax,
        cy:240-200*yvalue(row)/ymax,
        r:frontier ? 8 : 6, fill:`hsl(${175 + 55*row.pass_rate} 65% ${row.provisional ? 65 : 48}%)`,
        class:frontier ? "benchmark-dot frontier" : "benchmark-dot",
        tabindex:0, role:"button", "aria-label":`${title(row)}: ${percent(row.pass_rate)} pass rate, ${money(row.api_tokens_usd_per_success)}, ${seconds(row.seconds_per_success)} per success${row.provisional ? ", provisional" : ""}`,
      });
      dot.append(svgNode("title", {}, `${title(row)}\n${row.passes}/${row.trials} passed\n${seconds(row.mean_trial_seconds)} per trial\n${money(row.api_tokens_usd_per_success)} · ${seconds(row.seconds_per_success)} per success${row.provisional ? "\nProvisional: fewer than five trials" : ""}`));
      const focus = () => {
        const entries = $("benchmark-leaderboard").querySelectorAll("tbody tr");
        entries.forEach(n => n.classList.remove("benchmark-highlight"));
        const index = rows.indexOf(row), entry = entries[index];
        if (entry) {entry.classList.add("benchmark-highlight"); entry.tabIndex=-1; entry.focus(); entry.scrollIntoView({block:"nearest",behavior:"smooth"});}
      };
      dot.onclick = focus;
      dot.onkeydown = e => {if (["Enter"," "].includes(e.key)) {e.preventDefault(); focus();}};
      svg.append(dot);
    });
    target.append(svg);
  }

  function board(cohort) {
    const container = $("benchmark-leaderboard"); container.replaceChildren();
    if (!cohort) {
      $("benchmark-cohort-note").textContent = "Each comparison holds the task, prompt, hardware, deadline, harness and continuation policy fixed.";
      container.append(empty("Build the first comparison", "Prepare a task below, or import final host grades from fresh timed trials. Exploratory results remain visible separately."));
      scatter([]); return;
    }
    const scope = cohort.scope;
    $("benchmark-cohort-note").textContent = `${scope.task} · pack ${scope.pack_version} · ${scope.hardware} · ${scope.budget_seconds}s budget · ${scope.execution_backend || "execution unknown"} · harness ${scope.harness_version} · runner ${scope.runner_version}`;
    const entries = cohort.rows.map(row => {
      const identity = node("div"), quality = node("div");
      identity.append(node("strong", row.model), node("small", `${row.agent} ${row.agent_version} · ${row.settings.reasoning_effort || "default"} effort`));
      identity.title = JSON.stringify({model_version:row.model_version,settings:row.settings});
      quality.append(node("strong", `${percent(row.pass_rate)} · ${row.passes}/${row.trials}`), node("small", `95% interval ${row.pass_rate_95_interval.map(percent).join("–")}`));
      const status = node("span", row.provisional ? "Provisional" : !row.passes ? "No verified success" : row.pareto === true ? "Pareto frontier" : row.pareto === false ? "Tradeoff dominated" : row.pareto_quality_time ? "Time frontier · cost unknown" : "Cost incomplete", `benchmark-badge ${row.pareto ? "frontier" : ""}`);
      status.title = `Median first verified completion: ${seconds(row.median_verified_seconds)}. ${row.deadline_misses} late completions. ${row.trials_without_price} trials with unknown token cost.`;
      return [identity,String(row.trials),quality,seconds(row.seconds_per_success),money(row.api_tokens_usd_per_success),money(row.reported_usd_per_success),status];
    });
    const wrap = node("div",undefined,"benchmark-table-scroll");
    wrap.append(table(["Agent configuration","Trials","Pass rate","Time / success","API token $ estimate / success","Reported $ / success","Sample status"],entries));
    container.append(wrap); scatter(cohort.rows);
  }

  function render(pack, actions) {
    const data = pack.leaderboard, allRows = data.cohorts.flatMap(c => c.rows);
    $("benchmark-overview").replaceChildren();
    const values = [
      [allRows.reduce((n,r)=>n+r.trials,0)+data.unranked.length,"Graded trials"],
      [data.cohorts.length,"Comparison groups"],
      [allRows.filter(r=>!r.provisional).length,"Repeated configurations"],
      [data.unranked.length,"Unranked records"],
    ];
    for (const [count,label] of values) {
      const card = node("div",undefined,"benchmark-stat"); card.append(node("strong",String(count)),node("span",label)); $("benchmark-overview").append(card);
    }
    const picker = $("benchmark-cohort");
    picker.replaceChildren();
    data.cohorts.forEach((c,i) => {
      const option = node("option",`${c.scope.task} · ${c.scope.budget_seconds}s · ${c.scope.hardware} · ${c.id.slice(0,6)}`); option.value=c.id; picker.append(option);
      if (!selected && i===0) selected=c.id;
    });
    if (!data.cohorts.length) picker.append(node("option","No controlled trials yet"));
    if (!data.cohorts.some(c=>c.id===selected)) selected=data.cohorts[0]?.id || "";
    picker.value=selected; picker.disabled=!data.cohorts.length;
    picker.onchange=()=>{selected=picker.value; board(data.cohorts.find(c=>c.id===selected));};
    $("benchmark-chart").value = chartMode;
    $("benchmark-chart").onchange = () => {chartMode=$("benchmark-chart").value;board(data.cohorts.find(c=>c.id===selected));};
    board(data.cohorts.find(c=>c.id===selected));
    $("benchmark-unranked-count").textContent=`(${data.unranked.length})`;
    $("benchmark-unranked-table").replaceChildren(table(["Model / agent","Numerical contract","Measurements needed"],data.unranked.slice(0,100).map(r=>[
      `${r.model || "Unknown model"} / ${r.agent || "Unknown agent"}`,r.passed ? "Passed" : "Failed / incomplete",r.issues.join(" · "),
    ])));
    $("benchmark-price-date").textContent=`· ${data.pricing.checked_date}`;
    $("benchmark-price-note").textContent=`USD per million tokens. ${data.cost_note}`;
    const prices = Object.entries(data.pricing.per_million_tokens).map(([model,rate]) => {
      const link = node("a","Official source"); link.href=rate.source; link.target="_blank"; link.rel="noopener noreferrer";
      return [model,money(rate.input),money(rate.cached),money(rate.output),link];
    });
    $("benchmark-price-table").replaceChildren(table(["Model","Input","Cached input","Output","Reference"],prices));
    $("benchmark-history").hidden = !data.historical_pilot;
    if (data.historical_pilot) {
      $("benchmark-history-note").textContent = data.historical_pilot.note;
      $("benchmark-history-source").href = data.historical_pilot.source;
      $("benchmark-history-table").replaceChildren(table(["Earlier task","Model","Delivery","First host verification","Reported input","Output incl. reasoning"],data.historical_pilot.observations.map(r => [
        r.task,r.model,r.delivered ? "Passed contract" : "Not delivered",r.verified_seconds === null ? "Not reached" : seconds(r.verified_seconds),r.input_tokens.toLocaleString(),r.output_tokens.toLocaleString(),
      ])));
    }
    $("benchmark-export").onclick=()=>{
      const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)+"\n"],{type:"application/json"}));
      const a=node("a");a.href=url;a.download="simjecture-leaderboard.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    };
    const files=$("benchmark-import-files");
    $("benchmark-import").disabled=actions.readonly;
    $("benchmark-import").onclick=()=>files.click();
    files.onchange=async()=>{
      try {
        const selectedFiles=Array.from(files.files || []);
        if (!selectedFiles.length) return;
        if (selectedFiles.length>100 || selectedFiles.some(f=>f.size>4000000)) throw Error("Choose at most 100 grade files, up to 4 MB each.");
        $("benchmark-import").disabled=true;
        const reports=await Promise.all(selectedFiles.map(async f=>JSON.parse(await f.text())));
        const result=await actions.api("import-benchmark-reports",{reports});
        await actions.refresh(); actions.toast(`${result.imported} grades imported. Repeated imports do not add trials.`);
      } catch(error) {actions.toast(error.message,true);}
      finally {files.value="";$("benchmark-import").disabled=actions.readonly;}
    };
  }
  return {render};
})();
