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
  let chartMode = "cost-time";
  let resultsSource = "", officialTask = "rz-diagnostics", rankMode = "time", costBasis = "cached";

  const effortOrder = ["low","medium","high","xhigh","max","ultra"];
  const titleWords = text => text.replace(/\b(sol|astra|luna|terra|flash|pro|opus|sonnet|build|fast|thinking)\b/g,w=>w[0].toUpperCase()+w.slice(1));
  const modelName = name => {
    if(name==="deepseek-flash")return "DeepSeek Flash";
    if(name==="deepseek-v4-pro")return "DeepSeek V4 Pro";
    if(name==="gpt-reserve")return "GPT Reserve · dynamic router";
    if(name==="gpt-oss-120b-medium")return "GPT-OSS 120B";
    if(name.startsWith("gpt-"))return titleWords(name.replace("gpt-","GPT-").replaceAll("-"," ").replace("GPT ","GPT-"));
    if(name.startsWith("gemini-"))return titleWords(name.replace("gemini-","Gemini ").replaceAll("-"," "));
    if(name.startsWith("mimo-"))return titleWords(name.replace("mimo-","MiMo ").replaceAll("-"," "));
    if(name.startsWith("grok-"))return titleWords(name.replace("grok-","Grok ").replaceAll("-"," "));
    if(name.startsWith("claude-"))return titleWords(name.replace("claude-","Claude ").replace("4-6","4.6").replaceAll("-"," "));
    return name;
  };
  const agentName = name => ({codex:"Codex",agy:"Antigravity",grok:"Grok CLI",builtin:"API coding agent","codex-glm":"Codex / GLM"})[name]||name;
  const familyColour = family => {
    const palette=["#4879d9","#11958b","#bc6698","#8b6ed1","#d48a36","#679743","#b85c50","#639eb2"];
    let hash=0;for(const c of family)hash=(hash*31+c.charCodeAt(0))>>>0;
    return palette[hash%palette.length];
  };
  const officialCost = row => costBasis==="cached" ? row.cost_per_attempt : row.uncached_cost_per_attempt;
  const costLabel = row => {
    const value=officialCost(row);
    if(value===null)return !row.trials ? "No inference" : !row.tariff ? "Variable tariff" : "Usage missing";
    return (row.cost_coverage==="partial" ? "≥ " : row.cost_coverage==="estimated" ? "≈ " : "")+money(value);
  };
  const rankKey = () => rankMode==="time" ? "median_verified_seconds" : rankMode==="cost" ? (costBasis==="cached" ? "ranked_cost_per_attempt" : "ranked_uncached_cost_per_attempt") : "pass_rate";

  function rankBars(rows, kind) {
    const target=$(kind==="time" ? "benchmark-time-bars" : "benchmark-cost-bars");target.replaceChildren();
    const metric=r=>!r.passes ? 0 : kind==="time" ? r.median_verified_seconds : officialCost(r);
    const ranked=r=>r.passes>0 && metric(r)!==null && (kind==="time" || r.cost_coverage!=="partial");
    const category=r=>ranked(r) ? 0 : r.passes ? 1 : 2;
    const ordered=[...rows].sort((a,b)=>category(a)-category(b)||(category(a)===0 ? metric(a)-metric(b) : 0)||a.model.localeCompare(b.model)||effortOrder.indexOf(a.effort)-effortOrder.indexOf(b.effort));
    const maximum=Math.max(...ordered.map(metric).filter(n=>n!==null),1e-9);
    const axis=node("div",undefined,"benchmark-bar-axis");axis.append(node("span","0"),node("span",kind==="time" ? seconds(maximum) : money(maximum)));target.append(axis);
    const list=node("ol",undefined,"benchmark-bar-list");list.setAttribute("aria-label",kind==="time" ? "Finish time ranked from fastest; unfinished has value zero" : "Task cost ranked from cheapest; unfinished has value zero");
    let previous=null,place=0,position=0;
    for(const row of ordered){
      const value=metric(row),eligible=ranked(row);
      if(eligible){position++;if(value!==previous)place=position;previous=value;}
      const item=node("li",undefined,"benchmark-bar-row"+(!row.passes ? " unfinished" : ""));item.dataset.config=row.id;item.dataset.value=value===null ? "" : String(value);item.dataset.finished=String(row.passes>0);item.dataset.rank=eligible ? String(place) : "";
      item.append(node("span",eligible ? String(place) : "—","benchmark-bar-rank"));
      const label=node("div",undefined,"benchmark-bar-label");label.append(node("strong",modelName(row.family_label)),node("small",(row.effort||"default")+" · "+agentName(row.agent)));item.append(label);
      const track=node("div",undefined,"benchmark-bar-track"),bar=node("span",undefined,"benchmark-bar-fill");bar.style.width=value===null ? "0%" : (value/maximum*100)+"%";bar.style.backgroundColor=familyColour(row.family);if(!row.passes)bar.style.height="0";
      if(row.cost_coverage==="partial"&&kind==="cost")bar.classList.add("partial");
      track.append(bar);item.append(track);
      const text=!row.passes ? "0 · "+(row.trials ? "Unfinished" : "Unavailable") : value===null ? "No fixed tariff" : kind==="time" ? seconds(value) : costLabel(row);
      item.append(node("span",text,"benchmark-bar-value"));
      item.tabIndex=0;item.setAttribute("role","button");item.setAttribute("aria-label",modelName(row.family_label)+" "+(row.effort||"default")+", "+text);
      item.title=row.passes+"/"+row.trials+" verified completions"+(row.cost_coverage==="partial"&&kind==="cost" ? " · recorded cost lower bound, unranked" : "");
      const choose=()=>{const entry=document.querySelector('#benchmark-leaderboard tr[data-config="'+row.id+'"]');if(entry){entry.classList.add("benchmark-highlight");entry.scrollIntoView({block:"nearest",behavior:"smooth"});}};
      item.onclick=choose;item.onkeydown=e=>{if(["Enter"," "].includes(e.key)){e.preventDefault();choose();}};list.append(item);
    }
    target.append(list);
  }

  function officialPlot(rows, task) {
    const target=$("benchmark-tradeoff"),legend=$("benchmark-series-legend");target.replaceChildren();legend.replaceChildren();
    const quality=chartMode==="quality-time", points=rows.filter(r=>r.passes>0 && r.median_verified_seconds!==null && (quality || officialCost(r)!==null && r.cost_coverage!=="partial"));
    if(!points.length){target.append(empty("No measurements match this filter","Clear the model or effort filter to see the published results."));return;}
    const ns="http://www.w3.org/2000/svg";
    const s=(tag,attrs,text)=>{const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,String(v));if(text!==undefined)n.textContent=text;return n;};
    const svg=s("svg",{viewBox:"0 0 1000 440",role:"img","aria-label":quality ? "Completion and time" : "Cost-time Pareto plot. Lower cost is left; faster completion is top. Upper left is better."});
    const x0=90,x1=958,y0=365,y1=45,xmax=task.budget_seconds;
    const costs=points.map(officialCost).filter(n=>n>0);
    const logmin=quality ? 0 : Math.log10(Math.min(...costs)*.75);
    const logmax=quality ? 1 : Math.log10(Math.max(...costs)*1.4);
    const x=r=>quality ? x0+(x1-x0)*r.median_verified_seconds/xmax : x0+(x1-x0)*(Math.log10(officialCost(r))-logmin)/(logmax-logmin);
    const y=r=>quality ? y0-(y0-y1)*r.pass_rate : y1+(y0-y1)*r.median_verified_seconds/xmax;
    for(let i=0;i<=5;i++){
      const px=x0+(x1-x0)*i/5;
      if(quality){svg.append(s("line",{x1:px,x2:px,y1:y1,y2:y0,class:"benchmark-gridline"}));svg.append(s("text",{x:px,y:y0+28,"text-anchor":"middle"},(xmax*i/5/60).toLocaleString(undefined,{maximumFractionDigits:1})));}
      else{const py=y1+(y0-y1)*i/5;svg.append(s("line",{x1:x0,x2:x1,y1:py,y2:py,class:"benchmark-gridline"}));svg.append(s("text",{x:x0-15,y:py+4,"text-anchor":"end"},(xmax*i/5/60).toLocaleString(undefined,{maximumFractionDigits:1})));}
    }
    const ticks=[];
    if(quality){for(let i=0;i<=4;i++)ticks.push(i/4);}
    else{for(let power=Math.floor(logmin);power<=Math.ceil(logmax);power++)for(const multiple of [1,2,5]){const v=multiple*10**power;if(Math.log10(v)>=logmin && Math.log10(v)<=logmax)ticks.push(v);}}
    for(const v of ticks){
      if(quality){const py=y0-(y0-y1)*v;svg.append(s("line",{x1:x0,x2:x1,y1:py,y2:py,class:"benchmark-gridline"}));svg.append(s("text",{x:x0-15,y:py+4,"text-anchor":"end"},percent(v)));}
      else{const px=x0+(x1-x0)*(Math.log10(v)-logmin)/(logmax-logmin);svg.append(s("line",{x1:px,x2:px,y1:y1,y2:y0,class:"benchmark-gridline"}));svg.append(s("text",{x:px,y:y0+28,"text-anchor":"middle"},money(v)));}
    }
    svg.append(s("text",{x:x0,y:22,class:"benchmark-axis-title"},quality ? "Verified completion rate" : "Verified finish time · minutes · faster at top"));
    svg.append(s("text",{x:(x0+x1)/2,y:427,"text-anchor":"middle",class:"benchmark-axis-title"},quality ? "Verified finish time · minutes" : "API-equivalent cost per attempt · USD · log scale · cheaper to the left"));
    const frontier=quality ? [] : points.filter(r=>!points.some(o=>o!==r && officialCost(o)<=officialCost(r) && o.median_verified_seconds<=r.median_verified_seconds && (officialCost(o)<officialCost(r)||o.median_verified_seconds<r.median_verified_seconds)));
    if(frontier.length>1){const edge=s("polyline",{points:[...frontier].sort((a,b)=>officialCost(a)-officialCost(b)).map(r=>x(r)+","+y(r)).join(" "),fill:"none",stroke:"var(--accent)","stroke-width":2.5,opacity:.6,class:"benchmark-pareto-front"});edge.append(s("title",{},"Observed cost–finish-time Pareto frontier"));svg.append(edge);}
    svg.append(s("text",{x:x0+8,y:y1+20,class:"benchmark-better-corner"},quality ? "" : "↖ BETTER · LESS COST + LESS TIME"));
    const families=new Map();for(const r of points){if(!families.has(r.family))families.set(r.family,[]);families.get(r.family).push(r);}
    for(const [family,variants] of families){
      variants.sort((a,b)=>effortOrder.indexOf(a.effort)-effortOrder.indexOf(b.effort));
      const comparable=variants.filter(r=>r.cost_coverage!=="partial" || quality);
      if(comparable.length>1){
        const path=s("polyline",{points:comparable.map(r=>x(r)+","+y(r)).join(" "),fill:"none",stroke:familyColour(family),"stroke-width":2,"stroke-dasharray":"7 5",opacity:.65,class:"benchmark-effort-line","data-family":family});
        path.append(s("title",{},variants[0].family_label+" · "+comparable.map(r=>r.effort).join(" → ")));svg.append(path);
        const button=node("button",undefined,"benchmark-series-button");button.type="button";
        const swatch=node("span",undefined,"benchmark-series-swatch");swatch.style.borderColor=familyColour(family);
        button.append(swatch,document.createTextNode(modelName(variants[0].family_label)));
        button.onclick=()=>{const search=$("benchmark-search");search.value=search.value===variants[0].family_label ? "" : variants[0].family_label;search.dispatchEvent(new Event("input"));};legend.append(button);
      }
    }
    const tooltip=node("div",undefined,"benchmark-plot-tooltip");tooltip.hidden=true;
    const placedLabels=[];
    for(const row of points){
      const colour=familyColour(row.family),partial=row.cost_coverage==="partial";
      const dot=s("circle",{cx:x(row),cy:y(row),r:frontier.includes(row) ? 9 : 7,fill:colour,stroke:frontier.includes(row) ? "var(--ink)" : colour,"stroke-width":frontier.includes(row) ? 3 : 2.5,tabindex:0,role:"button",class:"benchmark-official-dot"+(frontier.includes(row) ? " pareto" : ""),"data-model":row.model,"data-effort":row.effort||"default","data-cost":officialCost(row),"data-time":row.median_verified_seconds,"aria-label":row.model+" "+(row.effort||"default")+", "+costLabel(row)+", "+seconds(row.median_verified_seconds)});
      const label=row.model+" · "+(row.effort||"default")+" effort";
      dot.append(s("title",{},label+" · "+row.passes+"/"+row.trials+" completed · "+costLabel(row)+" per attempt · "+seconds(row.median_verified_seconds)+(frontier.includes(row) ? " · observed Pareto frontier" : "")));
      const show=()=>{tooltip.replaceChildren(node("strong",label),node("span",costLabel(row)+" per attempt · "+seconds(row.median_verified_seconds)),node("small",row.passes+"/"+row.trials+" completed"+(row.cost_coverage==="estimated" ? " · AGY counter estimate" : "")+(frontier.includes(row) ? " · Pareto frontier" : "")));tooltip.hidden=false;};
      dot.onmouseenter=show;dot.onfocus=show;dot.onmouseleave=()=>tooltip.hidden=true;dot.onblur=()=>tooltip.hidden=true;
      const choose=()=>{document.querySelectorAll("#benchmark-leaderboard .benchmark-highlight").forEach(n=>n.classList.remove("benchmark-highlight"));const entry=document.querySelector('#benchmark-leaderboard tr[data-config="'+row.id+'"]');if(entry){entry.classList.add("benchmark-highlight");entry.scrollIntoView({block:"nearest",behavior:"smooth"});}};
      dot.onclick=choose;dot.onkeydown=e=>{if(["Enter"," "].includes(e.key)){e.preventDefault();choose();}};svg.append(dot);
      if(partial&&!quality)svg.append(s("text",{x:x(row)+9,y:y(row)-8,fill:colour},"≥"));
      if(families.get(row.family).length>1&&!partial){
        const width=(row.effort||"").length*6.5;
        const candidates=[[9,-10],[9,18],[-width-9,-10],[-width-9,18],[0,-25],[0,32]];
        const offset=candidates.find(([dx,dy])=>{
          const box={left:x(row)+dx,top:y(row)+dy-10,right:x(row)+dx+width,bottom:y(row)+dy+3};
          if(box.left<x0||box.right>x1||box.top<y1||box.bottom>y0)return false;
          if(placedLabels.some(b=>box.left<b.right+4&&box.right>b.left-4&&box.top<b.bottom+3&&box.bottom>b.top-3))return false;
          placedLabels.push(box);return true;
        });
        if(offset){const label=s("text",{x:x(row)+offset[0],y:y(row)+offset[1],class:"benchmark-effort-label"},row.effort);label.style.fill=colour;svg.append(label);}
      }
    }
    target.append(svg,tooltip);
    $("benchmark-plot-title").textContent=quality ? "Completion versus finish time" : "Cost–time Pareto plot";
    $("benchmark-chart-note").textContent=quality ? "Upper left is better: faster to the left, higher completion at the top. Dashed lines connect reasoning efforts." : "Upper left is better: cheaper to the left, faster at the top. Outlined points and the solid line mark the observed Pareto frontier. Dashed lines connect reasoning efforts for the same model. Unfinished and partial cost receipts are excluded.";
  }

  function officialBoard(publication, actions) {
    const task=publication.tasks.find(t=>t.id===officialTask)||publication.tasks[0];officialTask=task.id;
    const tabs=$("benchmark-task-tabs");tabs.replaceChildren();
    for(const t of publication.tasks){const b=node("button",t.title,"benchmark-task-tab");b.type="button";b.setAttribute("aria-pressed",String(t.id===task.id));b.onclick=()=>{officialTask=t.id;officialBoard(publication,actions);};tabs.append(b);}
    const brief=$("benchmark-task-brief");brief.replaceChildren(node("p",task.description),node("span",task.inputs),node("span",task.budget_seconds/60+" min deadline · "+task.repeats+" scheduled "+(task.repeats===1 ? "attempt" : "attempts")+" per configuration"));
    const redraw=()=>{
      const search=$("benchmark-search").value.toLowerCase().replaceAll(/[^a-z0-9]/g,""),effort=$("benchmark-effort-filter").value;
      let rows=task.rows.filter(r=>(r.agent+" "+agentName(r.agent)+" "+r.model+" "+modelName(r.family_label)).toLowerCase().replaceAll(/[^a-z0-9]/g,"").includes(search)&&(effort==="all"||(r.effort||"default")===effort));
      const key=rankKey();rows.sort((a,b)=>(a.ranks[key]??Infinity)-(b.ranks[key]??Infinity)||a.model.localeCompare(b.model)||effortOrder.indexOf(a.effort)-effortOrder.indexOf(b.effort));
      const entries=rows.map(row=>{
        const identity=node("div",undefined,"benchmark-model-identity"),name=node("strong",modelName(row.family_label)),detail=node("small",agentName(row.agent));identity.append(name,detail);identity.title=row.model+" · "+(row.agent_version||"Version unavailable");
        const receipts=node("details");receipts.append(node("summary","View "+row.trials+" "+(row.trials===1 ? "attempt" : "attempts")));
        const token=n=>n===null||n===undefined ? "Not recorded" : n.toLocaleString();
        receipts.append(table(["Elapsed","Input incl. cache","Cached input","Output","Cost","Result"],row.receipts.map(r=>[seconds(r.wall_seconds),token(r.usage.input_tokens),token(r.usage.cached_input_tokens),token(r.usage.output_tokens),(r.coverage==="partial" ? "≥ " : r.coverage==="agy-estimate" ? "≈ " : "")+money(costBasis==="cached" ? r.cost_usd : r.uncached_cost_usd),r.passed ? "Complete" : r.provider_interruption ? "Quota interrupted after work" : r.numeric_passed&&!r.findings_present ? "Numbers pass; findings missing" : "Incomplete contract"])));
        if(row.unavailable_attempts)receipts.append(node("p",row.unavailable_attempts+" attempts unavailable before inference; excluded from scores.","field-help"));identity.append(receipts);
        const score=node("div");score.append(node("strong",row.trials ? percent(row.pass_rate) : "Unavailable"),node("small",row.trials ? row.passes+"/"+row.trials+" complete" : "No successful inference"));
        const numerical=node("div");numerical.append(node("strong",row.trials ? percent(row.numeric_passes/row.trials) : "—"),node("small",row.trials ? row.numeric_passes+"/"+row.trials+" numerical passes" : ""));
        const cost=node("div");cost.append(node("strong",costLabel(row)),node("small",row.cost_coverage==="estimated" ? "AGY estimate" : row.cost_coverage==="partial" ? "Partial receipt · unranked by cost" : row.tariff?.reference ? "Groq tariff reference" : row.trials ? "API equivalent" : ""));
        const rate=node("div");rate.append(node("span",row.tariff ? money(row.tariff.input)+" / "+money(row.tariff.output) : "Variable routing"));
        if(row.tariff){const link=node("a",row.tariff.reference ? "Reference source" : "Vendor tariff");link.href=row.tariff.source;link.target="_blank";link.rel="noopener noreferrer";rate.append(link);rate.title=row.tariff.basis||"Input / output USD per million tokens; this is separate from task cost.";}
        return [String(row.ranks[key]??"—"),identity,row.effort||"default",score,numerical,row.median_verified_seconds===null ? row.trials ? "Not completed" : "—" : seconds(row.median_verified_seconds),cost,rate];
      });
      const container=$("benchmark-leaderboard"),wrap=node("div",undefined,"benchmark-table-scroll");container.replaceChildren();
      const t=table(["Rank","Model / coding agent","Effort","Completion","Numerical checks","Completion time","Cost / attempt · USD","Token tariff · in / out per 1M"],entries);wrap.append(t);container.append(wrap);
      Array.from(t.tBodies[0].rows).forEach((tr,i)=>tr.dataset.config=rows[i].id);
      for(const [index,mode] of [[3,"score"],[5,"time"],[6,"cost"]]){
        const th=t.tHead.rows[0].cells[index],label=th.textContent,b=node("button",label+(rankMode===mode ? " ↓" : ""),"benchmark-sort-heading");b.type="button";b.onclick=()=>{$("benchmark-sort").value=mode;rankMode=mode;redraw();};th.replaceChildren(b);th.setAttribute("aria-sort",rankMode===mode ? mode==="score" ? "descending" : "ascending" : "none");
      }
      rankBars(rows,"time");rankBars(rows,"cost");officialPlot(rows,task);
      $("benchmark-ranking-note").textContent="Time rank = median independently verified completion. Cost rank = mean API-equivalent cost per attempt, including failures. Partial usage has a lower bound and no cost rank. "+(task.repeats===1 ? "RZ has one measured attempt per configuration; ranks describe this initial sweep." : "CSV schedules five fresh attempts; quota-blocked attempts are excluded.")+" API tariffs are published prices; task cost depends on tokens used.";
    };
    $("benchmark-search").oninput=redraw;$("benchmark-effort-filter").onchange=redraw;
    $("benchmark-sort").value=rankMode;$("benchmark-sort").onchange=()=>{rankMode=$("benchmark-sort").value;redraw();};
    $("benchmark-cost-basis").value=costBasis;$("benchmark-cost-basis").onchange=()=>{costBasis=$("benchmark-cost-basis").value;redraw();};
    $("benchmark-chart").value=chartMode;$("benchmark-chart").onchange=()=>{chartMode=$("benchmark-chart").value;redraw();};
    const methodology=$("benchmark-methodology-text");methodology.replaceChildren();
    for(const text of ["Official results are this fixed 2026-10-01 edition, pack "+publication.pack_version+". Earlier packs and local/community protocols are archived separately.",
      "Completion requires numerical results, an independently reexecuted reducer, unchanged inputs and nonempty findings. Numerical checks are shown separately so correct arithmetic with missing delivery is visible.",
      "API-equivalent costs use published standard short-context rates and recorded token usage. They are not subscription invoices. Cache storage, hosted tools and unreported cache-write charges are excluded. Switching cost basis applies full input rates to all recorded input.",
      "AGY estimates treat its reported input and cache-read counters as disjoint; output already includes its thinking subset. This interpretation is explicit because native counter semantics are not a verified billing receipt.",
      "Interrupted requests may lack final usage. ≥ shows the recorded cost lower bound; it is excluded from cost ranking and effort connections. Grok Build Fast uses its published CLI tariff. GPT-OSS uses a labelled Groq reference tariff; GPT Reserve routes dynamically and has no fixed model tariff.",
      "These are recorded-diagnostic coding tasks with fresh numerical holdouts. Passing does not establish a physical hypothesis. Trials retain each coding agent's native prompts and tools."]){methodology.append(node("p",text,"field-help"));}
    const report=node("a","Full results and protocol");report.href=publication.report_url;report.target="_blank";report.rel="noopener noreferrer";methodology.append(report);
    redraw();
  }

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
    const svg = svgNode("svg", {viewBox:"0 0 760 290", role:"img", "aria-label":quality ? "Verified pass rate and mean elapsed time per trial. Includes failed attempts; upper left is more reliable and faster." : "Estimated token cost and elapsed time per verified success. Includes failed attempts; lower left is cheaper and faster. Pass rate is a third Pareto objective."});
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
    svg.append(svgNode("text", {x:385,y:285,"text-anchor":"middle"}, quality ? "Mean trial time (includes failures)" : "Token $ estimate / verified success"));
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
        const entries = $("benchmark-leaderboard").querySelectorAll(":scope > .benchmark-table-scroll > table > tbody > tr");
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
      const receipts=node("details"),receiptLabel=node("summary","Trial measurements");receipts.append(receiptLabel);
      const tokens=n=>n===null || n===undefined ? "Unknown" : n.toLocaleString();
      receipts.append(table(["Elapsed","Input tokens","Cached input","Output tokens","Delivery"],row.receipts.map(r=>[
        seconds(r.wall_seconds),tokens(r.usage.input_tokens),tokens(r.usage.cached_input_tokens),tokens(r.usage.output_tokens),r.passed ? "Verified pass" : r.provider_interruption ? `Interrupted · ${r.provider_interruption}` : r.numeric_passed && r.findings_present===false ? "Numbers pass · findings missing" : r.deadline_missed ? "Verified after deadline" : "Incomplete contract",
      ])));identity.append(receipts);
      quality.append(node("strong", `${percent(row.pass_rate)} · ${row.passes}/${row.trials}`), node("small", `95% interval ${row.pass_rate_95_interval.map(percent).join("–")}`));
      const status = node("span", row.provisional ? "Provisional" : !row.passes ? "No verified success" : row.pareto === true ? "Pareto frontier" : row.pareto === false ? "Tradeoff dominated" : row.pareto_quality_time ? "Time frontier · cost unknown" : "Cost incomplete", `benchmark-badge ${row.pareto ? "frontier" : ""}`);
      status.title = `Median first verified completion: ${seconds(row.median_verified_seconds)}. ${row.deadline_misses} late completions. ${row.trials_without_price} trials with unknown token cost.`;
      return [identity,String(row.trials),quality,seconds(row.mean_trial_seconds),seconds(row.seconds_per_success),money(row.api_tokens_usd_per_success),money(row.reported_usd_per_success),status];
    });
    const wrap = node("div",undefined,"benchmark-table-scroll");
    wrap.append(table(["Agent configuration","Trials","Pass rate","Mean trial time","Time / success","Token $ estimate / success","Reported $ / success","Sample status"],entries));
    container.append(wrap); scatter(cohort.rows);
  }

  function runDialog(pack, actions) {
    const dialog=node("dialog",undefined,"research-action-dialog benchmark-run-dialog"), form=node("form");
    form.append(node("h2","Benchmark your model"),node("p","Run fresh timed trials with your installed coding agent or the API connection saved in Connections. Your agent keeps its native tools. Grades are added here automatically.","field-help"));
    const field=(label,input)=>{const row=node("label",label);input.setAttribute("aria-label",label);row.append(input);form.append(row);return input;};
    const backend=field("Coding agent",node("select"));
    for(const [id,label] of [["codex","Codex"],["codex-glm","Codex / GLM"],["grok","Grok"],["agy","AGY"],["builtin","API coding agent"]]) {const option=node("option",label);option.value=id;backend.append(option);}
    const model=field("Model ID · suggestions or your own",node("input"));model.required=true;model.maxLength=160;model.autocomplete="off";
    const suggestions=node("datalist");suggestions.id=`benchmark-model-${crypto.randomUUID()}`;model.setAttribute("list",suggestions.id);form.append(suggestions);
    const effort=field("Reasoning effort",node("select"));
    for(const value of ["","low","medium","high","xhigh","max","ultra"]) {const option=node("option",value || "Provider default");option.value=value;effort.append(option);}
    const taskList=node("fieldset");taskList.append(node("legend","Tasks"));const checks=[];
    for(const task of pack.tasks) {const row=node("label"),check=node("input");check.type="checkbox";check.checked=true;checks.push([check,task.id]);row.append(check,document.createTextNode(`${task.title} · ${task.seconds / 60} min per trial`));taskList.append(row);}form.append(taskList);
    const repeats=field("Fresh trials per task",node("input"));repeats.type="number";repeats.min="1";repeats.max="20";repeats.value="5";repeats.required=true;
    const advanced=node("details");advanced.append(node("summary","Advanced settings"));const workerLabel=node("label","Parallel trials"),workers=node("input");workers.type="number";workers.min="1";workers.max="8";workers.value="1";workerLabel.append(workers);advanced.append(workerLabel,node("p","Task definitions and deadlines stay fixed. Hardware and runner settings create separate comparison groups. One trial is provisional; five are required for Pareto eligibility.","field-help"));form.append(advanced);
    form.append(node("p","Uses your configured subscription or API credits. API cost estimates and provider-reported spending remain separate.","field-help"));
    const error=node("p","","form-error");error.setAttribute("role","alert");form.append(error);
    const controls=node("div",undefined,"study-controls"),cancel=node("button","Cancel","secondary"),submit=node("button","Start timed trials");cancel.type="button";cancel.onclick=()=>dialog.close();submit.type="submit";controls.append(cancel,submit);form.append(controls);
    let request=0;
    backend.onchange=async()=>{
      const current=++request;effort.disabled=backend.value==="agy";if(effort.disabled)effort.value="";
      try {const catalogue=await actions.api("models",{backend:backend.value});if(current!==request)return;suggestions.replaceChildren();for(const entry of catalogue.models || []) {const option=node("option");option.value=entry.id;suggestions.append(option);}if(!model.value)model.value=catalogue.default || "";}catch(e){if(current===request)error.textContent=e.message;}
    };
    form.onsubmit=async event=>{
      event.preventDefault();submit.disabled=true;error.textContent="";
      try {const result=await actions.api("start-benchmark-campaign",{backend:backend.value,model:model.value.trim(),reasoning_effort:effort.value,repeats:Number(repeats.value),workers:Number(workers.value),tasks:checks.filter(([check])=>check.checked).map(([,id])=>id)});dialog.close();await actions.refresh();actions.toast(result.message);}catch(e){error.textContent=e.message;submit.disabled=false;}
    };
    dialog.append(form);document.body.append(dialog);dialog.addEventListener("close",()=>dialog.remove());dialog.showModal();backend.onchange();model.focus();
  }

  function render(pack, actions) {
    $("benchmark-published-note").textContent=`${pack.published_trials || 0} Simjecture-owned grades · ${pack.community_trials || 0} shipped community grades. Local runs appear as they finish. Community declarations keep separate comparison groups.`;
    $("benchmark-download-grades").onclick=()=>{
      const url=URL.createObjectURL(new Blob([JSON.stringify({reports:pack.grade_reports || []},null,2)+"\n"],{type:"application/json"}));
      const a=node("a");a.href=url;a.download="simjecture-benchmark-grades.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    };
    $("benchmark-run").disabled=actions.readonly;
    $("benchmark-run").onclick=()=>runDialog(pack,actions);
    const campaigns=$("benchmark-campaigns");campaigns.replaceChildren();
    for(const run of pack.campaigns || []) {
      const card=node("article",undefined,"benchmark-campaign");
      card.append(node("strong",run.name),node("span",`${run.finished}/${run.total} finished · ${run.passed} passed · ${run.active ? "Running" : run.stopped_reason || "Finished"}`));
      const progress=node("progress");progress.max=run.total || 1;progress.value=run.finished;progress.setAttribute("aria-label",`${run.name} progress`);card.append(progress);
      if(run.running.length)card.append(node("p",`Working: ${run.running.join(", ")}`,"field-help"));
      if(run.blocked.length)card.append(node("p",`Unavailable or quota limited: ${[...new Set(run.blocked)].join(", ")}`,"field-help"));
      if(run.runner_errors)card.append(node("p",`${run.runner_errors} runner errors need attention`,"form-error"));
      campaigns.append(card);
    }
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
    const ordered=[...data.cohorts].sort((a,b)=>b.scope.pack_version.localeCompare(a.scope.pack_version,{numeric:true}) || b.rows.reduce((n,r)=>n+r.trials,0)-a.rows.reduce((n,r)=>n+r.trials,0));
    ordered.forEach((c,i) => {
      const option = node("option",`${c.scope.protocol==="community-controlled" ? "Community · " : "Archive / local · "}${c.scope.task} · pack ${c.scope.pack_version} · ${c.scope.budget_seconds}s · ${c.id.slice(0,6)}`); option.value=c.id; picker.append(option);
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
    $("benchmark-unranked-table").replaceChildren(table(["Model / agent","Host result","Reason unranked"],data.unranked.slice(0,100).map(r=>[
      `${r.model || "Unknown model"} / ${r.agent || "Unknown agent"}`,r.availability_only ? "Unavailable · no inference" : r.passed ? "Passed" : "Failed / incomplete",r.issues.join(" · "),
    ])));
    $("benchmark-price-date").textContent=`· ${data.pricing.checked_date}`;
    $("benchmark-price-note").textContent=`USD per million tokens. ${data.cost_note}`;
    const prices = Object.entries(data.pricing.per_million_tokens).map(([model,rate]) => {
      const link = node("a","Official source"); link.href=rate.source; link.target="_blank"; link.rel="noopener noreferrer";
      if(rate.basis)link.title=rate.basis;
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
        const parsed=await Promise.all(selectedFiles.map(async f=>JSON.parse(await f.text())));
        const reports=parsed.flatMap(value=>Array.isArray(value) ? value : Array.isArray(value.reports) ? value.reports : [value]);
        if(reports.length>1000)throw Error("Import at most 1000 grades at a time.");
        const knownLocal=new Set((pack.grade_reports || []).filter(r=>r.trial?.comparison?.protocol==="controlled").map(r=>r.trial.trial_id));
        for(const report of reports)if(report.trial?.comparison?.protocol==="controlled" && !knownLocal.has(report.trial.trial_id))report.trial.comparison.protocol="community-controlled";
        const result=await actions.api("import-benchmark-reports",{reports});
        await actions.refresh(); actions.toast(`${result.imported} grades imported. Repeated imports do not add trials.`);
      } catch(error) {actions.toast(error.message,true);}
      finally {files.value="";$("benchmark-import").disabled=actions.readonly;}
    };
    if(!resultsSource)resultsSource=pack.official ? "official" : "local";
    if(!pack.official)resultsSource="local";
    const source=$("benchmark-source");source.value=resultsSource;
    source.querySelector('option[value="official"]').disabled=!pack.official;
    source.onchange=()=>{resultsSource=source.value;render(pack,actions);};
    const official=resultsSource==="official";
    $("benchmark-task-tabs").hidden=!official;
    $("benchmark-official-controls").hidden=!official;
    $("benchmark-ranked-charts").hidden=!official;
    $("benchmark-bar-note").hidden=!official;
    $("benchmark-local-group").hidden=official;
    $("benchmark-cohort-note").hidden=official;
    if(official){
      const publication=pack.official;
      $("benchmark-published-note").textContent="Official Simjecture measurements · "+publication.date+" · maintained result edition · pack "+publication.pack_version;
      $("benchmark-overview").replaceChildren();
      for(const [count,label] of [[publication.configurations,"Configurations tested"],[publication.attempts,"Scheduled attempts recorded"],[publication.tasks.length,"Scientific coding tasks"],[publication.unavailable_attempts,"Unavailable before inference"]]){
        const card=node("div",undefined,"benchmark-stat");card.append(node("strong",String(count)),node("span",label));$("benchmark-overview").append(card);
      }
      $("benchmark-export").onclick=()=>{
        const url=URL.createObjectURL(new Blob([JSON.stringify(publication,null,2)+"\n"],{type:"application/json"}));
        const a=node("a");a.href=url;a.download="simjecture-official-results-"+publication.date+".json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
      };
      officialBoard(publication,actions);
    }else{
      $("benchmark-series-legend").replaceChildren();
      $("benchmark-task-brief").replaceChildren(node("p","Archived qualifications and locally declared trials. Each comparison preserves its task version and runner conditions."));
      $("benchmark-ranking-note").textContent="This archive is separate from the official publication. Imported and community execution/billing declarations are not independently certified.";
      $("benchmark-chart-note").textContent="Archive measurements use their original comparison protocol.";
      $("benchmark-methodology-text").replaceChildren(node("p","Choose Official Simjecture results for the maintained two-task publication. Community and local records remain in their declared comparison groups.","field-help"));
    }
  }
  return {render};
})();
