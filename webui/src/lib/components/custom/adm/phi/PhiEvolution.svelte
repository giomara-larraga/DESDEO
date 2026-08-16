<script lang="ts">
  import { onMount } from "svelte";
  import * as d3 from "d3";
  import type { ADMLog } from "$lib/adm/types";

  export let log: ADMLog;
  export let width = 720;
  export let height = 300;

  let svgEl: SVGSVGElement;

  function draw() {
    const svg = d3.select(svgEl);
    svg.selectAll("*").remove();

    const margin = { top: 20, right: 30, bottom: 40, left: 55 };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const data = log.methods.flatMap((method) =>
      log.iterations.map((it) => ({
        method,
        iteration: it.iteration,
        phi: it.hypervolume[method].phi_iteration,
        phase: it.phase
      }))
    );

    const x = d3
      .scaleLinear()
      .domain(d3.extent(log.iterations, (d) => d.iteration) as [number, number])
      .range([0, innerW]);

    const y = d3
      .scaleLinear()
      .domain(d3.extent(data, (d) => d.phi) as [number, number])
      .nice()
      .range([innerH, 0]);

    const color = d3.scaleOrdinal(d3.schemeTableau10).domain(log.methods);

    const g = svg
      .attr("viewBox", `0 0 ${width} ${height}`)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    g.append("rect")
      .attr("x", x(1))
      .attr("width", x(log.adm_configuration.learning_iterations) - x(1))
      .attr("y", 0)
      .attr("height", innerH)
      .attr("fill", "#dbeafe")
      .attr("opacity", 0.4);

    g.append("rect")
      .attr("x", x(log.adm_configuration.learning_iterations))
      .attr("width", innerW - x(log.adm_configuration.learning_iterations))
      .attr("y", 0)
      .attr("height", innerH)
      .attr("fill", "#ffedd5")
      .attr("opacity", 0.4);

    g.append("g")
      .attr("transform", `translate(0,${innerH})`)
      .call(d3.axisBottom(x).ticks(log.iterations.length));

    g.append("g").call(d3.axisLeft(y));

    const line = d3
      .line<any>()
      .x((d) => x(d.iteration))
      .y((d) => y(d.phi));

    for (const method of log.methods) {
      const values = data.filter((d) => d.method === method);

      g.append("path")
        .datum(values)
        .attr("fill", "none")
        .attr("stroke", color(method) as string)
        .attr("stroke-width", 2.5)
        .attr("d", line);

      g.selectAll(`circle-${method}`)
        .data(values)
        .join("circle")
        .attr("cx", (d) => x(d.iteration))
        .attr("cy", (d) => y(d.phi))
        .attr("r", 4)
        .attr("fill", color(method) as string);
    }
  }

  onMount(draw);
  $: if (svgEl) draw();
</script>

<svg bind:this={svgEl}></svg>

<style>
  svg {
    width: 100%;
    height: auto;
  }
</style>