<script lang="ts">
  import { onMount } from "svelte";
  import * as d3 from "d3";
  import type { ReferenceVectorViewModel } from "$lib/adm/types";

  export let vectors: ReferenceVectorViewModel[] = [];
  export let selectedId: string | undefined;
  export let onSelect: (id: string) => void = () => {};

  let svgEl: SVGSVGElement;
  const width = 520;
  const height = 320;

  function draw() {
    if (!svgEl) return;

    const svg = d3.select(svgEl);
    svg.selectAll("*").remove();

    const margin = { top: 20, right: 20, bottom: 30, left: 40 };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const x = d3
      .scaleLinear()
      .domain(d3.extent(vectors, (d) => d.x) as [number, number])
      .nice()
      .range([0, innerW]);

    const y = d3
      .scaleLinear()
      .domain(d3.extent(vectors, (d) => d.y) as [number, number])
      .nice()
      .range([innerH, 0]);

    const maxAssigned = d3.max(vectors, (d) => d.assignedSolutions) ?? 1;

    const r = d3.scaleSqrt().domain([0, maxAssigned]).range([4, 14]);

    const color = d3
      .scaleSequential(d3.interpolateViridis)
      .domain([0, maxAssigned]);

    const g = svg
      .attr("viewBox", `0 0 ${width} ${height}`)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    g.append("g")
      .attr("transform", `translate(0,${innerH})`)
      .call(d3.axisBottom(x).ticks(5));

    g.append("g").call(d3.axisLeft(y).ticks(5));

    g.selectAll("circle")
      .data(vectors)
      .join("circle")
      .attr("cx", (d) => x(d.x))
      .attr("cy", (d) => y(d.y))
      .attr("r", (d) => r(d.assignedSolutions))
      .attr("fill", (d) => color(d.assignedSolutions))
      .attr("opacity", 0.85)
      .attr("stroke", (d) =>
        d.id === selectedId ? "#111827" : d.roi ? "#ef4444" : d.selected ? "#7c3aed" : "white"
      )
      .attr("stroke-width", (d) => (d.id === selectedId || d.roi || d.selected ? 3 : 1))
      .style("cursor", "pointer")
      .on("click", (_, d) => onSelect(d.id))
      .append("title")
      .text((d) => `${d.id}\nAssigned: ${d.assignedSolutions}`);
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