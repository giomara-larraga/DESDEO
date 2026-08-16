<script lang="ts">
  import { onMount } from "svelte";
  import * as d3 from "d3";
  import type { ADMLog } from "$lib/adm/types";
  import { getIteration } from "$lib/adm/adapters";

  export let log: ADMLog;
  export let selectedIteration: number;
  export let width = 720;
  export let height = 280;

  let svgEl: SVGSVGElement;

  function draw() {
    const iteration = getIteration(log, selectedIteration);

    const data = log.methods.flatMap((method) =>
      iteration.hypervolume[method].phi_per_generation.map((phi, i) => ({
        method,
        generation: i + 1,
        phi
      }))
    );

    const svg = d3.select(svgEl);
    svg.selectAll("*").remove();

    const margin = { top: 20, right: 30, bottom: 40, left: 55 };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const x = d3
      .scaleLinear()
      .domain([1, log.adm_configuration.generations_per_iteration])
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

    g.append("g")
      .attr("transform", `translate(0,${innerH})`)
      .call(d3.axisBottom(x));

    g.append("g").call(d3.axisLeft(y));

    const line = d3
      .line<any>()
      .x((d) => x(d.generation))
      .y((d) => y(d.phi));

    for (const method of log.methods) {
      const values = data.filter((d) => d.method === method);

      g.append("path")
        .datum(values)
        .attr("fill", "none")
        .attr("stroke", color(method) as string)
        .attr("stroke-width", 2.5)
        .attr("d", line);
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