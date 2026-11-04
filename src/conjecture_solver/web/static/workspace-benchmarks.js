"use strict";
window.WorkspaceBenchmarks = (() => {
  const $ = id => document.getElementById(id);
  const node = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined) SimjectureI18n.content(n, text);
    if (cls) n.className = cls;
    return n;
  };
  const money = n => (n === null ? SimjectureI18n.t("ui.unknown") : `$${n.toLocaleString(undefined, {maximumFractionDigits:5})}`);
  const seconds = n => (n === null ? SimjectureI18n.t("ui.unknown") : (n < 60 ? `${n.toFixed(1)} s` : `${(n / 60).toFixed(2)} min`));
  const percent = n => `${Math.round(n * 100)}%`;
  const title = row => `${row.agent} / ${row.model}${(row.settings.reasoning_effort ? ` · ${SimjectureI18n.label(row.settings.reasoning_effort, row.settings.reasoning_effort)}` : SimjectureI18n.t("ui.default-effort"))}`;
  let selected = "";
  let resultsSource = "", officialTask = "rz-diagnostics", rankMode = "time", costBasis = "cached";

  const effortOrder = ["low","medium","high","xhigh","max","ultra"];
  const titleWords = text => text.replace(/\b(sol|astra|luna|terra|flash|pro|opus|sonnet|build|fast|thinking)\b/g,w=>w[0].toUpperCase()+w.slice(1));
  const modelName = name => {
    if(name==="deepseek-flash")return "DeepSeek Flash";
    if(name==="deepseek-v4-pro")return "DeepSeek V4 Pro";
    if(name==="gpt-reserve")return SimjectureI18n.live(() => SimjectureI18n.t("ui.gpt-reserve-dynamic-router"));
    if(name==="gpt-oss-120b-medium")return "GPT-OSS 120B";
    if(name.startsWith("gpt-"))return titleWords(name.replace("gpt-","GPT-").replaceAll("-"," ").replace("GPT ","GPT-"));
    if(name.startsWith("gemini-"))return titleWords(name.replace("gemini-","Gemini ").replaceAll("-"," "));
    if(name.startsWith("mimo-"))return titleWords(name.replace("mimo-","MiMo ").replaceAll("-"," "));
    if(name.startsWith("grok-"))return titleWords(name.replace("grok-","Grok ").replaceAll("-"," "));
    if(name.startsWith("claude-"))return titleWords(name.replace("claude-","Claude ").replace("4-6","4.6").replaceAll("-"," "));
    return name;
  };
  const agentName = name => (({codex:"Codex",agy:"Antigravity",grok:"Grok CLI",builtin:SimjectureI18n.live(() => SimjectureI18n.t("ui.api-coding-agent")),"codex-glm":"Codex / GLM"})[name] || name);
  const modelColours = {"deepseek-flash":"#4da6ff","deepseek-v4-pro":"#aabfff","gpt-6-luna":"#00d9a6","gpt-6.1-sol":"#b091ff","gpt-6-astra":"#f280b5","gemini-3.8-flash":"#ff7722","gemini-3.7-flash":"#f29f66","gemini-3.6-flash":"#ffc857","gemini-3.1-pro":"#e4d975","gpt-5.5":"#e6e1d4","gpt-5.6-luna":"#46b8b4","gpt-5.6-sol":"#d4c5a9","gpt-5.6-terra":"#a7cb54","gpt-6-sol":"#54c95a","gpt-oss-120b-medium":"#a6cbd0","gpt-reserve":"#c5bbc9","grok-4.5":"#ec6c63","grok-4.6":"#db869e","grok-4.7":"#dc524c","grok-4.7-build-fast":"#cc9661","mimo-v2.6-flash":"#c1d971","mimo-v2.6-pro":"#94c474","claude-opus-4-6-thinking":"#ecafca","claude-sonnet-4-6":"#d6b8ff","glm-5.3":"#7996b5"};
  const familyColour = family => {
    const model=family.includes("/") ? family.split("/").slice(1).join("/") : family;
    if(modelColours[model])return modelColours[model];
    let hash=0;for(const c of model)hash=(hash*31+c.charCodeAt(0))>>>0;
    return `hsl(${hash%36000/100} 66% ${52+(hash>>>16)%16}%)`;
  };
  const unfinishedColour = "#dc524c";
  const officialCost = row => costBasis==="cached" ? row.cost_per_attempt : row.uncached_cost_per_attempt;
  const costLabel = row => {
    const value=officialCost(row);
    if(value===null)return (!row.trials ? SimjectureI18n.t("ui.no-inference") : (!row.tariff ? SimjectureI18n.t("ui.variable-tariff") : SimjectureI18n.t("ui.usage-missing")));
    return ((row.cost_coverage==="partial" ? "≥ " : (row.cost_coverage==="estimated" ? "≈ " : "")) + money(value));
  };
  const rankKey = () => rankMode==="time" ? "median_verified_seconds" : rankMode==="cost" ? (costBasis==="cached" ? "ranked_cost_per_attempt" : "ranked_uncached_cost_per_attempt") : "pass_rate";

  function rankBars(rows, kind) {
    const target=$(kind==="time" ? "benchmark-time-bars" : "benchmark-cost-bars");target.replaceChildren();
    const metric=r=>kind==="cost" ? officialCost(r) : r.passes ? r.median_verified_seconds : 0;
    const ranked=r=>r.passes>0 && metric(r)!==null && (kind==="time" || r.cost_coverage!=="partial");
    const category=r=>ranked(r) ? 0 : r.passes ? 1 : 2;
    const ordered=[...rows].sort((a,b)=>category(a)-category(b)||(category(a)===0 ? metric(a)-metric(b) : 0)||a.model.localeCompare(b.model)||effortOrder.indexOf(a.effort)-effortOrder.indexOf(b.effort));
    const maximum=Math.max(...ordered.map(metric).filter(n=>n!==null),1e-9);
    const axis=node("div",undefined,"benchmark-bar-axis");axis.append(node("span","0"),node("span",SimjectureI18n.live(() => kind==="time" ? seconds(maximum) : money(maximum))));target.append(axis);
    const list=node("ol",undefined,"benchmark-bar-list");SimjectureI18n.attribute(list, "aria-label", () => kind==="time" ? SimjectureI18n.t("ui.finish-time-ranked-from-fastest-unfinished-runs-are-red") : SimjectureI18n.t("ui.task-cost-ranked-from-cheapest-unfinished-runs-show-recorded-spendin"));
    let previous=null,place=0,position=0;
    for(const row of ordered){
      const value=metric(row),eligible=ranked(row);
      if(eligible){position++;if(value!==previous)place=position;previous=value;}
      const item=node("li",undefined,"benchmark-bar-row"+(!row.passes ? " unfinished" : ""));item.dataset.config=row.id;item.dataset.value=value===null ? "" : String(value);item.dataset.finished=String(row.passes>0);item.dataset.rank=eligible ? String(place) : "";
      item.append(node("span",eligible ? String(place) : "—","benchmark-bar-rank"));
      const label=node("div",undefined,"benchmark-bar-label");label.append(node("strong",SimjectureI18n.live(() => modelName(row.family_label))),node("small",SimjectureI18n.live(() => SimjectureI18n.label(row.effort || "default") + " · " + agentName(row.agent))));item.append(label);
      const track=node("div",undefined,"benchmark-bar-track"),bar=node("span",undefined,"benchmark-bar-fill");bar.style.width=value===null ? "0%" : (value/maximum*100)+"%";bar.style.backgroundColor=row.passes ? familyColour(row.family) : unfinishedColour;if(!row.passes&&kind==="time")bar.style.height="0";
      if(row.cost_coverage==="partial"&&kind==="cost")bar.classList.add("partial");
      track.append(bar);item.append(track);
      const text=SimjectureI18n.live(() => !row.passes ? (kind==="cost" ? (costLabel(row) + SimjectureI18n.t("ui.unfinished")) : SimjectureI18n.t("ui.unfinished-2")) : (value===null ? SimjectureI18n.t("ui.no-fixed-tariff") : (kind==="time" ? seconds(value) : costLabel(row))));
      item.append(node("span",text,"benchmark-bar-value"));
      item.tabIndex=0;item.setAttribute("role","button");SimjectureI18n.attribute(item, "aria-label", () => modelName(row.family_label)+" "+SimjectureI18n.label(row.effort||"default")+", "+text);
      SimjectureI18n.attribute(item, "title", () => row.passes + "/" + row.trials + SimjectureI18n.t("ui.verified-completions") + (row.cost_coverage==="partial"&&kind==="cost" ? SimjectureI18n.t("ui.recorded-cost-lower-bound-unranked") : ""));
      const choose=()=>{const entry=document.querySelector('#benchmark-leaderboard tr[data-config="'+row.id+'"]');if(entry){entry.classList.add("benchmark-highlight");entry.scrollIntoView({block:"nearest",behavior:"smooth"});}};
      item.onclick=choose;item.onkeydown=e=>{if(["Enter"," "].includes(e.key)){e.preventDefault();choose();}};list.append(item);
    }
    target.append(list);
  }

  function officialPlot(rows, task) {
    const target=$("benchmark-tradeoff"),legend=$("benchmark-series-legend");target.replaceChildren();legend.replaceChildren();
    const points=rows.filter(r=>r.passes>0 && r.median_verified_seconds!==null && officialCost(r)!==null && r.cost_coverage!=="partial");
    if(!points.length){target.append(empty(SimjectureI18n.message("ui.no-measurements-match-this-filter"),SimjectureI18n.message("ui.clear-the-model-or-effort-filter-to-see-the-published-results")));return;}
    const ns="http://www.w3.org/2000/svg";
    const s=(tag,attrs,text)=>{const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs||{}))["aria-label","title"].includes(k) ? SimjectureI18n.attribute(n,k,() => v) : n.setAttribute(k,String(v));if(text!==undefined)SimjectureI18n.content(n, text);return n;};
    const svg=s("svg",{viewBox:"0 0 1000 440",role:"img","aria-label":SimjectureI18n.message("ui.cost-time-pareto-plot-lower-cost-is-left-faster-completion-is-top-up")});
    const x0=90,x1=958,y0=365,y1=45,xmax=task.budget_seconds;
    const costs=points.map(officialCost).filter(n=>n>0);
    const logmin=Math.log10(Math.min(...costs)*.75);
    const logmax=Math.log10(Math.max(...costs)*1.4);
    const x=r=>x0+(x1-x0)*(Math.log10(officialCost(r))-logmin)/(logmax-logmin);
    const y=r=>y1+(y0-y1)*r.median_verified_seconds/xmax;
    for(let i=0;i<=5;i++){
      const py=y1+(y0-y1)*i/5;svg.append(s("line",{x1:x0,x2:x1,y1:py,y2:py,class:"benchmark-gridline"}));svg.append(s("text",{x:x0-15,y:py+4,"text-anchor":"end"},(xmax*i/5/60).toLocaleString(undefined,{maximumFractionDigits:1})));
    }
    const ticks=[];
    for(let power=Math.floor(logmin);power<=Math.ceil(logmax);power++)for(const multiple of [1,2,5]){const v=multiple*10**power;if(Math.log10(v)>=logmin && Math.log10(v)<=logmax)ticks.push(v);}
    for(const v of ticks){
      const px=x0+(x1-x0)*(Math.log10(v)-logmin)/(logmax-logmin);svg.append(s("line",{x1:px,x2:px,y1:y1,y2:y0,class:"benchmark-gridline"}));svg.append(s("text",{x:px,y:y0+28,"text-anchor":"middle"},SimjectureI18n.live(() => money(v))));
    }
    svg.append(s("text",{x:x0,y:22,class:"benchmark-axis-title"},SimjectureI18n.message("ui.verified-finish-time-minutes-faster-at-top")));
    svg.append(s("text",{x:(x0+x1)/2,y:427,"text-anchor":"middle",class:"benchmark-axis-title"},SimjectureI18n.message("ui.api-equivalent-cost-per-attempt-usd-log-scale-cheaper-to-the-left")));
    const frontier=points.filter(r=>!points.some(o=>o!==r && officialCost(o)<=officialCost(r) && o.median_verified_seconds<=r.median_verified_seconds && (officialCost(o)<officialCost(r)||o.median_verified_seconds<r.median_verified_seconds)));

    svg.append(s("text",{x:x0+8,y:y1+20,class:"benchmark-better-corner"},SimjectureI18n.message("ui.better-less-cost-less-time")));
    const families=new Map();for(const r of points){if(!families.has(r.family))families.set(r.family,[]);families.get(r.family).push(r);}
    for(const [family,variants] of families){
      variants.sort((a,b)=>effortOrder.indexOf(a.effort)-effortOrder.indexOf(b.effort));
      const comparable=variants.filter(r=>r.cost_coverage!=="partial");
      if(comparable.length>1){
        const path=s("polyline",{points:comparable.map(r=>x(r)+","+y(r)).join(" "),fill:"none",stroke:familyColour(family),"stroke-width":2,"stroke-dasharray":"7 5",opacity:.65,class:"benchmark-effort-line","data-family":family});
        path.append(s("title",{},SimjectureI18n.live(() => variants[0].family_label+" · "+comparable.map(r=>SimjectureI18n.label(r.effort)).join(" → "))));svg.append(path);
      }
      const button=node("button",undefined,"benchmark-series-button");button.type="button";
      const swatch=node("span",undefined,"benchmark-series-swatch"+(comparable.length>1 ? " effort" : ""));swatch.style.backgroundColor=familyColour(family);
      button.append(swatch,node("span",SimjectureI18n.live(() => modelName(variants[0].family_label))));
      button.onclick=()=>{const search=$("benchmark-search");search.value=search.value===variants[0].family_label ? "" : variants[0].family_label;search.dispatchEvent(new Event("input"));};legend.append(button);
    }

    const tooltip=node("div",undefined,"benchmark-plot-tooltip");tooltip.hidden=true;
    const placedLabels=[];
    for(const row of points){
      const colour=familyColour(row.family),partial=row.cost_coverage==="partial";
      const dot=s("circle",{cx:x(row),cy:y(row),r:frontier.includes(row) ? 9 : 7,fill:colour,stroke:frontier.includes(row) ? "var(--ink)" : colour,"stroke-width":frontier.includes(row) ? 3 : 2.5,tabindex:0,role:"button",class:"benchmark-official-dot"+(frontier.includes(row) ? " pareto" : ""),"data-model":row.model,"data-effort":row.effort||"default","data-cost":officialCost(row),"data-time":row.median_verified_seconds,"aria-label":SimjectureI18n.live(() => row.model + " " + SimjectureI18n.label(row.effort || "default") + ", " + costLabel(row) + ", " + seconds(row.median_verified_seconds))});
      const label=SimjectureI18n.live(() => SimjectureI18n.t("ui.effort-3", {p0:row.model,p1:SimjectureI18n.label(row.effort||"default")}));
      dot.append(s("title",{},SimjectureI18n.live(() => label + " · " + row.passes + "/" + row.trials + SimjectureI18n.t("ui.completed") + costLabel(row) + SimjectureI18n.t("ui.per-attempt") + seconds(row.median_verified_seconds) + (frontier.includes(row) ? SimjectureI18n.t("ui.observed-pareto-frontier") : ""))));
      const show=()=>{tooltip.replaceChildren(node("strong",label),node("span",SimjectureI18n.live(() => costLabel(row) + SimjectureI18n.t("ui.per-attempt") + seconds(row.median_verified_seconds))),node("small",SimjectureI18n.live(() => row.passes + "/" + row.trials + SimjectureI18n.t("ui.completed-2") + (row.cost_coverage==="estimated" ? SimjectureI18n.t("ui.agy-counter-estimate") : "") + (frontier.includes(row) ? SimjectureI18n.t("ui.pareto-frontier") : ""))));tooltip.hidden=false;};
      dot.onmouseenter=show;dot.onfocus=show;dot.onmouseleave=()=>tooltip.hidden=true;dot.onblur=()=>tooltip.hidden=true;
      const choose=()=>{document.querySelectorAll("#benchmark-leaderboard .benchmark-highlight").forEach(n=>n.classList.remove("benchmark-highlight"));const entry=document.querySelector('#benchmark-leaderboard tr[data-config="'+row.id+'"]');if(entry){entry.classList.add("benchmark-highlight");entry.scrollIntoView({block:"nearest",behavior:"smooth"});}};
      dot.onclick=choose;dot.onkeydown=e=>{if(["Enter"," "].includes(e.key)){e.preventDefault();choose();}};svg.append(dot);
      if(partial)svg.append(s("text",{x:x(row)+9,y:y(row)-8,fill:colour},"≥"));
      if(families.get(row.family).length>1&&!partial){
        const width=SimjectureI18n.label(row.effort||"").length * (SimjectureI18n.getLanguage() === "zh-CN" ? 12 : 6.5);
        const candidates=[[9,-10],[9,18],[-width-9,-10],[-width-9,18],[0,-25],[0,32]];
        const offset=candidates.find(([dx,dy])=>{
          const box={left:x(row)+dx,top:y(row)+dy-10,right:x(row)+dx+width,bottom:y(row)+dy+3};
          if(box.left<x0||box.right>x1||box.top<y1||box.bottom>y0)return false;
          if(placedLabels.some(b=>box.left<b.right+4&&box.right>b.left-4&&box.top<b.bottom+3&&box.bottom>b.top-3))return false;
          placedLabels.push(box);return true;
        });
        if(offset){const label=s("text",{x:x(row)+offset[0],y:y(row)+offset[1],class:"benchmark-effort-label"},SimjectureI18n.live(() => SimjectureI18n.label(row.effort)));label.style.fill=colour;svg.append(label);}
      }
    }
    target.append(svg,tooltip);
    SimjectureI18n.bindText($("benchmark-plot-title"), () => SimjectureI18n.t("ui.cost-time-pareto-plot"));
    SimjectureI18n.bindText($("benchmark-chart-note"), () => SimjectureI18n.t("ui.upper-left-is-better-cheaper-to-the-left-faster-at-the-top-outlined-"));
  }

  function officialBoard(publication, actions) {
    const task=publication.tasks.find(t=>t.id===officialTask)||publication.tasks[0];officialTask=task.id;
    const tabs=$("benchmark-task-tabs");tabs.replaceChildren();
    for(const t of publication.tasks){const b=node("button",SimjectureI18n.live(() => SimjectureI18n.known(`ui.benchmark-official.${t.id}.title`, t.title)),"benchmark-task-tab");b.type="button";b.setAttribute("aria-pressed",String(t.id===task.id));b.onclick=()=>{officialTask=t.id;officialBoard(publication,actions);};tabs.append(b);}
    const brief=$("benchmark-task-brief");brief.replaceChildren(node("p",SimjectureI18n.live(() => SimjectureI18n.known(`ui.benchmark-official.${task.id}.description`, task.description))),node("span",SimjectureI18n.live(() => SimjectureI18n.known(`ui.benchmark-official.${task.id}.inputs`, task.inputs))),node("span",SimjectureI18n.live(() => task.budget_seconds/60 + SimjectureI18n.t("ui.min-deadline") + task.repeats + SimjectureI18n.t("ui.scheduled") + (task.repeats===1 ? SimjectureI18n.t("ui.attempt") : SimjectureI18n.t("ui.attempts")) + SimjectureI18n.t("ui.per-configuration"))));
    const redraw=()=>{
      const search=$("benchmark-search").value.toLowerCase().replaceAll(/[^a-z0-9]/g,""),effort=$("benchmark-effort-filter").value;
      let rows=task.rows.filter(r=>r.trials>0&&(r.agent+" "+agentName(r.agent)+" "+r.model+" "+modelName(r.family_label)).toLowerCase().replaceAll(/[^a-z0-9]/g,"").includes(search)&&(effort==="all"||(r.effort||"default")===effort));
      const key=rankKey();rows.sort((a,b)=>(a.ranks[key]??Infinity)-(b.ranks[key]??Infinity)||a.model.localeCompare(b.model)||effortOrder.indexOf(a.effort)-effortOrder.indexOf(b.effort));
      const entries=rows.map(row=>{
        const identity=node("div",undefined,"benchmark-model-identity"),name=node("strong",SimjectureI18n.live(() => modelName(row.family_label))),detail=node("small",SimjectureI18n.live(() => agentName(row.agent)));identity.append(name,detail);SimjectureI18n.attribute(identity, "title", () => row.model + " · " + (row.agent_version || SimjectureI18n.t("ui.version-unavailable")));
        const receipts=node("details");receipts.append(node("summary",SimjectureI18n.live(() => SimjectureI18n.t("ui.view") + row.trials + " " + (row.trials===1 ? SimjectureI18n.t("ui.attempt") : SimjectureI18n.t("ui.attempts")))));
        const token=n=>n===null||n===undefined ? SimjectureI18n.t("ui.not-recorded") : n.toLocaleString();
        receipts.append(table([SimjectureI18n.message("ui.elapsed"),SimjectureI18n.message("ui.input-incl-cache"),SimjectureI18n.message("ui.cached-input"),SimjectureI18n.message("ui.output"),SimjectureI18n.message("ui.cost"),SimjectureI18n.message("ui.result")],row.receipts.map(r=>[SimjectureI18n.live(() => seconds(r.wall_seconds)),SimjectureI18n.live(() => token(r.usage.input_tokens)),SimjectureI18n.live(() => token(r.usage.cached_input_tokens)),SimjectureI18n.live(() => token(r.usage.output_tokens)),SimjectureI18n.live(() => (r.coverage==="partial" ? "≥ " : r.coverage==="agy-estimate" ? "≈ " : "")+money(costBasis==="cached" ? r.cost_usd : r.uncached_cost_usd)),SimjectureI18n.live(() => r.passed ? SimjectureI18n.t("ui.complete") : r.provider_interruption ? SimjectureI18n.t("ui.quota-interrupted-after-work") : r.numeric_passed&&!r.findings_present ? SimjectureI18n.t("ui.numbers-pass-findings-missing") : SimjectureI18n.t("ui.incomplete-contract"))])));
        if(row.unavailable_attempts)receipts.append(node("p",SimjectureI18n.live(() => row.unavailable_attempts+SimjectureI18n.t("ui.attempts-unavailable-before-inference-excluded-from-scores")),"field-help"));identity.append(receipts);
        const score=node("div");score.append(node("strong",SimjectureI18n.live(() => row.trials ? percent(row.pass_rate) : SimjectureI18n.t("ui.unavailable-2"))),node("small",SimjectureI18n.live(() => row.trials ? (row.passes + "/" + row.trials + SimjectureI18n.t("ui.complete-2")) : SimjectureI18n.t("ui.no-successful-inference"))));
        const numerical=node("div");numerical.append(node("strong",row.trials ? percent(row.numeric_passes/row.trials) : "—"),node("small",SimjectureI18n.live(() => row.trials ? (row.numeric_passes + "/" + row.trials + SimjectureI18n.t("ui.numerical-passes")) : "")));
        const cost=node("div");cost.append(node("strong",SimjectureI18n.live(() => costLabel(row))),node("small",SimjectureI18n.live(() => row.cost_coverage==="estimated" ? SimjectureI18n.t("ui.agy-estimate") : (row.cost_coverage==="partial" ? SimjectureI18n.t("ui.partial-receipt-unranked-by-cost") : (row.tariff?.reference ? SimjectureI18n.t("ui.groq-tariff-reference") : (row.trials ? SimjectureI18n.t("ui.api-equivalent") : ""))))));
        const rate=node("div");rate.append(node("span",SimjectureI18n.live(() => row.tariff ? (money(row.tariff.input) + " / " + money(row.tariff.output)) : SimjectureI18n.t("ui.variable-routing"))));
        if(row.tariff){const link=node("a",SimjectureI18n.live(() => row.tariff.reference ? SimjectureI18n.t("ui.reference-source") : SimjectureI18n.t("ui.vendor-tariff")));link.href=row.tariff.source;link.target="_blank";link.rel="noopener noreferrer";rate.append(link);SimjectureI18n.attribute(rate, "title", () => row.tariff.basis || SimjectureI18n.t("ui.input-output-usd-per-million-tokens-this-is-separate-from-task-cost"));}
        return [String(row.ranks[key]??"—"),identity,SimjectureI18n.live(() => SimjectureI18n.label(row.effort||"default")),score,numerical,row.median_verified_seconds===null ? row.trials ? SimjectureI18n.live(() => SimjectureI18n.t("ui.not-completed")) : "—" : seconds(row.median_verified_seconds),cost,rate];
      });
      const container=$("benchmark-leaderboard"),wrap=node("div",undefined,"benchmark-table-scroll");container.replaceChildren();
      const t=table([SimjectureI18n.message("ui.rank"),SimjectureI18n.message("ui.model-coding-agent"),SimjectureI18n.message("ui.effort"),SimjectureI18n.message("ui.completion"),SimjectureI18n.message("ui.numerical-checks"),SimjectureI18n.message("ui.completion-time"),SimjectureI18n.message("ui.cost-attempt-usd"),SimjectureI18n.message("ui.token-tariff-in-out-per-1m")],entries);wrap.append(t);container.append(wrap);
      Array.from(t.tBodies[0].rows).forEach((tr,i)=>{tr.dataset.config=rows[i].id;tr.classList.toggle("benchmark-unfinished",!rows[i].passes);});
      for(const [index,mode] of [[3,"score"],[5,"time"],[6,"cost"]]){
        const th=t.tHead.rows[0].cells[index],label={3:"ui.completion",5:"ui.completion-time",6:"ui.cost-attempt-usd"}[index],b=node("button",SimjectureI18n.live(() => SimjectureI18n.t(label)+(rankMode===mode ? " ↓" : "")),"benchmark-sort-heading");b.type="button";b.onclick=()=>{$("benchmark-sort").value=mode;rankMode=mode;redraw();};th.replaceChildren(b);th.setAttribute("aria-sort",rankMode===mode ? mode==="score" ? "descending" : "ascending" : "none");
      }
      rankBars(rows,"time");rankBars(rows,"cost");officialPlot(rows,task);
      SimjectureI18n.bindText($("benchmark-ranking-note"), () => SimjectureI18n.t("ui.time-rank-median-independently-verified-completion-cost-rank-mean-ap") + (task.repeats===1 ? SimjectureI18n.t("ui.rz-has-one-measured-attempt-per-configuration-ranks-describe-this-in") : SimjectureI18n.t("ui.csv-schedules-five-fresh-attempts-quota-blocked-attempts-are-exclude")) + SimjectureI18n.t("ui.api-tariffs-are-published-prices-task-cost-depends-on-tokens-used"));
    };
    $("benchmark-search").oninput=redraw;$("benchmark-effort-filter").onchange=redraw;
    $("benchmark-sort").value=rankMode;$("benchmark-sort").onchange=()=>{rankMode=$("benchmark-sort").value;redraw();};
    $("benchmark-cost-basis").value=costBasis;$("benchmark-cost-basis").onchange=()=>{costBasis=$("benchmark-cost-basis").value;redraw();};
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
    const points = rows.filter(r => r.api_tokens_usd_per_success !== null && r.seconds_per_success !== null);
    const target = $("benchmark-tradeoff");
    target.replaceChildren();
    if (!points.length) {
      target.append(empty(SimjectureI18n.message("ui.tradeoffs-need-measured-usage-and-timing"), SimjectureI18n.message("ui.missing-cost-stays-unknown-complete-timed-trial-metadata-will-place-")));
      return;
    }
    const ns = "http://www.w3.org/2000/svg";
    const svgNode = (tag, attrs, text) => {
      const n = document.createElementNS(ns, tag);
      for (const [k,v] of Object.entries(attrs || {})) ["aria-label","title"].includes(k) ? SimjectureI18n.attribute(n,k,() => v) : n.setAttribute(k, String(v));
      if (text !== undefined) SimjectureI18n.content(n, text);
      return n;
    };
    const svg = svgNode("svg", {viewBox:"0 0 760 290", role:"img", "aria-label":SimjectureI18n.message("ui.estimated-token-cost-and-elapsed-time-per-verified-success-includes-")});
    const xvalue = r => r.api_tokens_usd_per_success;
    const yvalue = r => r.seconds_per_success;
    const xmax = Math.max(...points.map(xvalue), 0.000001) * 1.15;
    const ymax = Math.max(...points.map(yvalue), 1) * 1.15;
    for (let i=0; i<=4; i++) {
      const x = 85 + i * 150, y = 40 + i * 50;
      svg.append(svgNode("line", {x1:x,x2:x,y1:40,y2:240,class:"benchmark-gridline"}));
      svg.append(svgNode("line", {x1:85,x2:685,y1:y,y2:y,class:"benchmark-gridline"}));
      svg.append(svgNode("text", {x,y:263,"text-anchor":"middle"}, SimjectureI18n.live(() => money(i*xmax/4))));
      svg.append(svgNode("text", {x:73,y:y+4,"text-anchor":"end"}, SimjectureI18n.live(() => seconds(i*ymax/4))));
    }
    svg.append(svgNode("text", {x:385,y:285,"text-anchor":"middle"}, SimjectureI18n.message("ui.token-estimate-verified-success")));
    svg.append(svgNode("text", {x:85,y:20}, SimjectureI18n.message("ui.elapsed-time-verified-success")));
    points.forEach(row => {
      const frontier = row.pareto;
      const dot = svgNode("circle", {
        cx:85+600*xvalue(row)/xmax,
        cy:40+200*yvalue(row)/ymax,
        r:frontier ? 8 : 6, fill:familyColour(`${row.agent}/${row.model}`),
        class:frontier ? "benchmark-dot frontier" : "benchmark-dot",
        tabindex:0, role:"button", "aria-label":SimjectureI18n.live(() => SimjectureI18n.t("ui.pass-rate-per-success", {p0: title(row), p1: percent(row.pass_rate), p2: money(row.api_tokens_usd_per_success), p3: seconds(row.seconds_per_success), p4: (row.provisional ? SimjectureI18n.t("ui.provisional") : "")})),
      });
      dot.append(svgNode("title", {}, SimjectureI18n.live(() => SimjectureI18n.t("ui.passed-per-trial-per-success", {p0: title(row), p1: row.passes, p2: row.trials, p3: seconds(row.mean_trial_seconds), p4: money(row.api_tokens_usd_per_success), p5: seconds(row.seconds_per_success), p6: row.provisional ? SimjectureI18n.t("ui.provisional-fewer-than-five-trials") : ""}))));
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
      SimjectureI18n.bindText($("benchmark-cohort-note"), () => SimjectureI18n.t("ui.each-comparison-holds-the-task-prompt-hardware-deadline-harness-and-"));
      container.append(empty(SimjectureI18n.message("ui.build-the-first-comparison"), SimjectureI18n.message("ui.prepare-a-task-below-or-import-final-host-grades-from-fresh-timed-tr")));
      scatter([]); return;
    }
    const scope = cohort.scope;
    SimjectureI18n.bindText($("benchmark-cohort-note"), () => SimjectureI18n.t("ui.pack-s-budget-harness-runner", {p0: scope.task, p1: scope.pack_version, p2: scope.hardware, p3: scope.budget_seconds, p4: (scope.execution_backend || SimjectureI18n.t("ui.execution-unknown")), p5: scope.harness_version, p6: scope.runner_version}));
    const entries = cohort.rows.map(row => {
      const identity = node("div"), quality = node("div");
      identity.append(node("strong", row.model), node("small", SimjectureI18n.live(() => SimjectureI18n.t("ui.effort-2", {p0: row.agent, p1: row.agent_version, p2: SimjectureI18n.label(row.settings.reasoning_effort || "default")}))));
      SimjectureI18n.attribute(identity, "title", () => JSON.stringify({model_version:row.model_version,settings:row.settings}));
      const receipts=node("details"),receiptLabel=node("summary",SimjectureI18n.message("ui.trial-measurements"));receipts.append(receiptLabel);
      const tokens=n=>n===null || n===undefined ? SimjectureI18n.t("ui.unknown") : n.toLocaleString();
      receipts.append(table([SimjectureI18n.message("ui.elapsed"),SimjectureI18n.message("ui.input-tokens"),SimjectureI18n.message("ui.cached-input"),SimjectureI18n.message("ui.output-tokens"),SimjectureI18n.message("ui.delivery")],row.receipts.map(r=>[
        SimjectureI18n.live(() => seconds(r.wall_seconds)),SimjectureI18n.live(() => tokens(r.usage.input_tokens)),SimjectureI18n.live(() => tokens(r.usage.cached_input_tokens)),SimjectureI18n.live(() => tokens(r.usage.output_tokens)),SimjectureI18n.live(() => r.passed ? SimjectureI18n.t("ui.verified-pass") : r.provider_interruption ? SimjectureI18n.t("ui.interrupted", {p0: r.provider_interruption}) : r.numeric_passed && r.findings_present===false ? SimjectureI18n.t("ui.numbers-pass-findings-missing-2") : r.deadline_missed ? SimjectureI18n.t("ui.verified-after-deadline") : SimjectureI18n.t("ui.incomplete-contract")),
      ])));identity.append(receipts);
      quality.append(node("strong", `${percent(row.pass_rate)} · ${row.passes}/${row.trials}`), node("small", SimjectureI18n.live(() => SimjectureI18n.t("ui.95-interval", {p0: row.pass_rate_95_interval.map(percent).join("–")}))));
      const status = node("span", SimjectureI18n.live(() => row.provisional ? SimjectureI18n.t("ui.provisional-2") : (!row.passes ? SimjectureI18n.t("ui.no-verified-success") : (row.pareto === true ? SimjectureI18n.t("ui.pareto-frontier-2") : (row.pareto === false ? SimjectureI18n.t("ui.tradeoff-dominated") : (row.pareto_quality_time ? SimjectureI18n.t("ui.time-frontier-cost-unknown") : SimjectureI18n.t("ui.cost-incomplete")))))), `benchmark-badge ${row.pareto ? "frontier" : ""}`);
      SimjectureI18n.attribute(status, "title", () => SimjectureI18n.t("ui.median-first-verified-completion-late-completions-trials-with-unknow", {p0: seconds(row.median_verified_seconds), p1: row.deadline_misses, p2: row.trials_without_price}));
      return [identity,String(row.trials),quality,seconds(row.mean_trial_seconds),seconds(row.seconds_per_success),money(row.api_tokens_usd_per_success),money(row.reported_usd_per_success),status];
    });
    const wrap = node("div",undefined,"benchmark-table-scroll");
    wrap.append(table([SimjectureI18n.message("ui.agent-configuration"),SimjectureI18n.message("ui.trials"),SimjectureI18n.message("ui.pass-rate"),SimjectureI18n.message("ui.mean-trial-time"),SimjectureI18n.message("ui.time-success"),SimjectureI18n.message("ui.token-estimate-success"),SimjectureI18n.message("ui.reported-success"),SimjectureI18n.message("ui.sample-status")],entries));
    container.append(wrap); scatter(cohort.rows);
  }

  function runDialog(pack, actions) {
    const dialog=node("dialog",undefined,"research-action-dialog benchmark-run-dialog"), form=node("form");
    SimjectureI18n.attribute(dialog, "aria-label", () => SimjectureI18n.t("ui.benchmark-your-model"));
    form.append(node("h2",SimjectureI18n.message("ui.benchmark-your-model")),node("p",SimjectureI18n.message("ui.run-fresh-timed-trials-with-your-installed-coding-agent-or-the-api-c"),"field-help"));
    const field=(label,input)=>{const row=node("label",label);SimjectureI18n.attribute(input, "aria-label", () => label);row.append(input);form.append(row);return input;};
    const backend=field(SimjectureI18n.message("ui.coding-agent"),node("select"));
    for(const [id,label] of [["codex","Codex"],["codex-glm","Codex / GLM"],["grok","Grok"],["agy","AGY"],["builtin",SimjectureI18n.live(() => SimjectureI18n.t("ui.api-coding-agent"))]]) {const option=node("option",label);option.value=id;backend.append(option);}
    const model=field(SimjectureI18n.message("ui.model-id-suggestions-or-your-own"),node("input"));model.required=true;model.maxLength=160;model.autocomplete="off";
    const suggestions=node("datalist");suggestions.id=`benchmark-model-${crypto.randomUUID()}`;model.setAttribute("list",suggestions.id);form.append(suggestions);
    const effort=field(SimjectureI18n.message("ui.reasoning-effort"),node("select"));
    for(const value of ["","low","medium","high","xhigh","max","ultra"]) {const option=node("option",SimjectureI18n.live(() => value || SimjectureI18n.t("ui.provider-default")));if(value)SimjectureI18n.bindText(option,()=>SimjectureI18n.label(value,value));option.value=value;effort.append(option);}
    const taskList=node("fieldset");taskList.append(node("legend",SimjectureI18n.message("ui.tasks")));const checks=[];
    for(const task of pack.tasks) {const row=node("label"),check=node("input");check.type="checkbox";check.checked=true;checks.push([check,task.id]);row.append(check,node("span",SimjectureI18n.live(() => SimjectureI18n.t("ui.p0-p1-min-per-trial", {p0:SimjectureI18n.known(`ui.benchmark-task.${task.id}.title`, task.title),p1:task.seconds/60}))));taskList.append(row);}form.append(taskList);
    const repeats=field(SimjectureI18n.message("ui.fresh-trials-per-task"),node("input"));repeats.type="number";repeats.min="1";repeats.max="20";repeats.value="5";repeats.required=true;
    const advanced=node("details");advanced.append(node("summary",SimjectureI18n.message("ui.advanced-settings")));const workerLabel=node("label",SimjectureI18n.message("ui.parallel-trials")),workers=node("input");workers.type="number";workers.min="1";workers.max="8";workers.value="1";workerLabel.append(workers);advanced.append(workerLabel,node("p",SimjectureI18n.message("ui.task-definitions-and-deadlines-stay-fixed-hardware-and-runner-settin"),"field-help"));form.append(advanced);
    form.append(node("p",SimjectureI18n.message("ui.uses-your-configured-subscription-or-api-credits-api-cost-estimates-"),"field-help"));
    const error=node("p","","form-error");error.setAttribute("role","alert");form.append(error);
    const controls=node("div",undefined,"study-controls"),cancel=node("button",SimjectureI18n.message("ui.cancel"),"secondary"),submit=node("button",SimjectureI18n.message("ui.start-timed-trials"));cancel.type="button";cancel.onclick=()=>dialog.close();submit.type="submit";controls.append(cancel,submit);form.append(controls);
    let request=0;
    backend.onchange=async()=>{
      const current=++request;effort.disabled=backend.value==="agy";if(effort.disabled)effort.value="";
      try {const catalogue=await actions.api("models",{backend:backend.value});if(current!==request)return;suggestions.replaceChildren();for(const entry of catalogue.models || []) {const option=node("option");option.value=entry.id;suggestions.append(option);}if(!model.value)model.value=catalogue.default || "";}catch(e){if(current===request)SimjectureI18n.content(error, e.message);}
    };
    form.onsubmit=async event=>{
      event.preventDefault();if(submit.disabled)return;submit.disabled=true;SimjectureI18n.content(error, "");
      try {const result=await actions.api("start-benchmark-campaign",{backend:backend.value,model:model.value.trim(),reasoning_effort:effort.value,repeats:Number(repeats.value),workers:Number(workers.value),tasks:checks.filter(([check])=>check.checked).map(([,id])=>id)});dialog.close();await actions.refresh();actions.toast(SimjectureI18n.live(() => SimjectureI18n.known("ui.timed-trials-started", result.message)));}catch(e){SimjectureI18n.content(error, e.message);submit.disabled=false;}
    };
    dialog.append(form);document.body.append(dialog);dialog.addEventListener("close",()=>dialog.remove());dialog.showModal();backend.onchange();model.focus();
  }

  function render(pack, actions) {
    SimjectureI18n.bindText($("benchmark-published-note"), () => SimjectureI18n.t("ui.simjecture-owned-grades-shipped-community-grades-local-runs-appear-a", {p0: (pack.published_trials || 0), p1: (pack.community_trials || 0)}));
    $("benchmark-download-grades").onclick=()=>{
      const url=URL.createObjectURL(new Blob([JSON.stringify({reports:pack.grade_reports || []},null,2)+"\n"],{type:"application/json"}));
      const a=node("a");a.href=url;a.download="simjecture-benchmark-grades.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    };
    $("benchmark-run").disabled=actions.readonly;
    SimjectureI18n.attribute($("benchmark-run"), "title", () => actions.hosted ? SimjectureI18n.t("ui.run-your-own-benchmarks-in-a-self-hosted-simjecture-workspace") : "");
    $("benchmark-run").onclick=()=>runDialog(pack,actions);
    const campaigns=$("benchmark-campaigns");campaigns.replaceChildren();
    for(const run of pack.campaigns || []) {
      const card=node("article",undefined,"benchmark-campaign");
      card.append(node("strong",run.name),node("span",SimjectureI18n.live(() => SimjectureI18n.t("ui.finished-passed", {p0: run.finished, p1: run.total, p2: run.passed, p3: run.active ? SimjectureI18n.t("ui.running") : (run.stopped_reason || SimjectureI18n.t("ui.finished-3"))}))));
      const progress=node("progress");progress.max=run.total || 1;progress.value=run.finished;SimjectureI18n.attribute(progress, "aria-label", () => SimjectureI18n.t("ui.progress", {p0: run.name}));card.append(progress);
      if(run.running.length)card.append(node("p",SimjectureI18n.live(() => SimjectureI18n.t("ui.working", {p0: run.running.join(", ")})),"field-help"));
      if(run.blocked.length)card.append(node("p",SimjectureI18n.live(() => SimjectureI18n.t("ui.unavailable-or-quota-limited", {p0: [...new Set(run.blocked)].join(", ")})),"field-help"));
      if(run.runner_errors)card.append(node("p",SimjectureI18n.live(() => SimjectureI18n.t("ui.runner-errors-need-attention", {p0: run.runner_errors})),"form-error"));
      campaigns.append(card);
    }
    const data = pack.local_leaderboard || pack.leaderboard, allRows = data.cohorts.flatMap(c => c.rows);
    $("benchmark-overview").replaceChildren();
    const values = [
      [allRows.reduce((n,r)=>n+r.trials,0),SimjectureI18n.live(() => SimjectureI18n.t("ui.graded-trials"))],
      [data.cohorts.length,SimjectureI18n.live(() => SimjectureI18n.t("ui.comparison-groups"))],
      [allRows.filter(r=>!r.provisional).length,SimjectureI18n.live(() => SimjectureI18n.t("ui.repeated-configurations"))],
      [allRows.reduce((n,r)=>n+r.passes,0),SimjectureI18n.live(() => SimjectureI18n.t("ui.completed-trials"))],
    ];
    for (const [count,label] of values) {
      const card = node("div",undefined,"benchmark-stat"); card.append(node("strong",String(count)),node("span",label)); $("benchmark-overview").append(card);
    }
    const picker = $("benchmark-cohort");
    picker.replaceChildren();
    const ordered=[...data.cohorts].sort((a,b)=>b.scope.pack_version.localeCompare(a.scope.pack_version,{numeric:true}) || b.rows.reduce((n,r)=>n+r.trials,0)-a.rows.reduce((n,r)=>n+r.trials,0));
    ordered.forEach((c,i) => {
      const option = node("option",SimjectureI18n.live(() => SimjectureI18n.t("ui.pack-s", {p0: (c.scope.protocol==="community-controlled" ? SimjectureI18n.t("ui.community") : SimjectureI18n.t("ui.local")), p1: c.scope.task, p2: c.scope.pack_version, p3: c.scope.budget_seconds, p4: c.id.slice(0,6)}))); option.value=c.id; picker.append(option);
      if (!selected && i===0) selected=c.id;
    });
    if (!data.cohorts.length) picker.append(node("option",SimjectureI18n.message("ui.no-controlled-trials-yet")));
    if (!data.cohorts.some(c=>c.id===selected)) selected=data.cohorts[0]?.id || "";
    picker.value=selected; picker.disabled=!data.cohorts.length;
    picker.onchange=()=>{selected=picker.value; board(data.cohorts.find(c=>c.id===selected));};
    board(data.cohorts.find(c=>c.id===selected));
    SimjectureI18n.content($("benchmark-price-date"), `· ${data.pricing.checked_date}`);
    SimjectureI18n.bindText($("benchmark-price-note"), () => SimjectureI18n.t("ui.usd-per-million-tokens", {p0: SimjectureI18n.known("ui.benchmark-pricing-note", data.cost_note)}));
    const prices = Object.entries(data.pricing.per_million_tokens).map(([model,rate]) => {
      const link = node("a",SimjectureI18n.message("ui.official-source")); link.href=rate.source; link.target="_blank"; link.rel="noopener noreferrer";
      if(rate.basis)SimjectureI18n.attribute(link, "title", () => rate.basis);
      return [model,money(rate.input),money(rate.cached),money(rate.output),link];
    });
    $("benchmark-price-table").replaceChildren(table([SimjectureI18n.message("ui.model"),SimjectureI18n.message("ui.input"),SimjectureI18n.message("ui.cached-input"),SimjectureI18n.message("ui.output"),SimjectureI18n.message("ui.reference")],prices));
    $("benchmark-export").onclick=()=>{
      const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)+"\n"],{type:"application/json"}));
      const a=node("a");a.href=url;a.download="simjecture-leaderboard.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    };
    const files=$("benchmark-import-files");
    $("benchmark-import").disabled=actions.readonly;
    SimjectureI18n.attribute($("benchmark-import"), "title", () => actions.hosted ? SimjectureI18n.t("ui.import-custom-results-in-a-self-hosted-simjecture-workspace") : "");
    SimjectureI18n.bindText($("benchmark-your-work").querySelector(".field-help"), () => actions.hosted ? SimjectureI18n.t("ui.browse-and-download-the-official-results-here-testing-models-and-imp") : SimjectureI18n.t("workspace.benchmarkCommunityHelp"));
    $("benchmark-import").onclick=()=>files.click();
    files.onchange=async()=>{
      try {
        const selectedFiles=Array.from(files.files || []);
        if (!selectedFiles.length) return;
        if (selectedFiles.length>100 || selectedFiles.some(f=>f.size>4000000)) throw Error(SimjectureI18n.t("ui.choose-at-most-100-grade-files-up-to-4-mb-each"));
        $("benchmark-import").disabled=true;
        const parsed=await Promise.all(selectedFiles.map(async f=>JSON.parse(await f.text())));
        const reports=parsed.flatMap(value=>Array.isArray(value) ? value : Array.isArray(value.reports) ? value.reports : [value]);
        if(reports.length>1000)throw Error(SimjectureI18n.t("ui.import-at-most-1000-grades-at-a-time"));
        const knownLocal=new Set((pack.grade_reports || []).filter(r=>r.trial?.comparison?.protocol==="controlled").map(r=>r.trial.trial_id));
        for(const report of reports)if(report.trial?.comparison?.protocol==="controlled" && !knownLocal.has(report.trial.trial_id))report.trial.comparison.protocol="community-controlled";
        const result=await actions.api("import-benchmark-reports",{reports});
        await actions.refresh(); actions.toast(SimjectureI18n.live(() => SimjectureI18n.t("ui.grades-imported-repeated-imports-do-not-add-trials", {p0: result.imported})));
      } catch(error) {actions.toast(error.message,true);}
      finally {files.value="";$("benchmark-import").disabled=actions.readonly;}
    };
    if(!resultsSource)resultsSource=pack.official ? "official" : "local";
    if(!pack.official)resultsSource="local";
    const source=$("benchmark-source");source.value=resultsSource;
    source.querySelector('option[value="official"]').disabled=!pack.official;
    source.querySelector('option[value="local"]').disabled=!!actions.hosted;
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
      SimjectureI18n.bindText($("benchmark-published-note"), () => SimjectureI18n.t("ui.official-simjecture-measurements") + publication.date + SimjectureI18n.t("ui.maintained-result-edition-pack") + publication.pack_version);
      $("benchmark-overview").replaceChildren();
      for(const [count,label] of [[new Set(publication.tasks.flatMap(t=>t.rows.filter(r=>r.trials>0).map(r=>r.id))).size,SimjectureI18n.live(() => SimjectureI18n.t("ui.configurations-tested"))],[publication.tasks.reduce((n,t)=>n+t.rows.reduce((m,r)=>m+r.trials,0),0),SimjectureI18n.live(() => SimjectureI18n.t("ui.graded-attempts"))],[publication.tasks.length,SimjectureI18n.live(() => SimjectureI18n.t("ui.scientific-coding-tasks"))],[publication.tasks.reduce((n,t)=>n+t.rows.reduce((m,r)=>m+r.passes,0),0),SimjectureI18n.live(() => SimjectureI18n.t("ui.completed-attempts"))]]){
        const card=node("div",undefined,"benchmark-stat");card.append(node("strong",String(count)),node("span",label));$("benchmark-overview").append(card);
      }
      $("benchmark-export").onclick=()=>{
        const url=URL.createObjectURL(new Blob([JSON.stringify(publication,null,2)+"\n"],{type:"application/json"}));
        const a=node("a");a.href=url;a.download="simjecture-official-results-"+publication.date+".json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
      };
      officialBoard(publication,actions);
    }else{
      $("benchmark-series-legend").replaceChildren();
      $("benchmark-task-brief").replaceChildren(node("p",SimjectureI18n.message("ui.current-pack-community-and-locally-declared-trials-each-comparison-p")));
      SimjectureI18n.bindText($("benchmark-ranking-note"), () => SimjectureI18n.t("ui.these-submissions-are-separate-from-the-official-publication-importe"));
      SimjectureI18n.bindText($("benchmark-chart-note"), () => SimjectureI18n.t("ui.community-and-local-measurements-use-their-declared-comparison-proto"));
    }
  }
  return {render};
})();
