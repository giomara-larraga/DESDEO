<script lang="ts">
  import { onMount } from "svelte";
  import * as d3 from "d3";
  import type { ReferenceVectorViewModel } from "$lib/adm/types";

  export let vectors: ReferenceVectorViewModel[] = [];
  export let objectives: string[] = [];
  export let selectedId: string | undefined;
  export let onSelect: (id: string) => void = () => {};

  let svgEl: SVGSVGElement;
  const width = 560;
  const rowHeight = 24;

  function draw() {
    const height = vectors.length * rowHeight + 70;
    const svg = d3.select(svgEl);
    svg.selectAll("*").remove();

    const margin = { top: 40, right: 70, bottom: 20, left: 60 };
    const innerW = width - margin.left - margin.right;

    const x = d3
      .scaleBand()
      .domain(objectives)
      .range([0, innerW])
      .padding(0.05);

    const y = d3
      .scaleBand()
      .domain(vectors.map((d) => d.id))
      .range([0, vectors.length * rowHeight])
      .padding(0.05);

    const color = d3.scaleSequential(d3.interpolateBlues).domain([0, 1]);

    const g = svg
      .attr("viewBox", `0 0 ${width} ${height}`)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    g.append("g").call(d3.axisTop(x));

    g.append("g")
      .call(d3.axisLeft(y).tickSize(0))
      .select(".domain")
      .remove();

    const cells = vectors.flatMap((vector) =>
      vector.weights.map((value, i) => ({
        vector,
        objective: objectives[i],
        value
      }))
    );

    g.selectAll("rect.cell")
      .data(cells)
      .join("rect")
      .attr("class", "cell")
      .attr("x", (d) => x(d.objective) ?? 0)
      .attr("y", (d) => y(d.vector.id) ?? 0)
      .attr("width", x.bandwidth())
      .attr("height", y.bandwidth())
      .attr("fill", (d) => color(d.value))
      .attr("stroke", (d) => (d.vector.id === selectedId ? "#111827" : "white"))
      .attr("stroke-width", (d) => (d.vector.id === selectedId ? 2 : 0.5))
      .style("cursor", "pointer")
      .on("click", (_, d) => onSelect(d.vector.id));

    const maxAssigned = d3.max(vectors, (d) => d.assignedSolutions) ?? 1;
    const bar = d3.scaleLinear().domain([0, maxAssigned]).range([0, 55]);

    g.selectAll("rect.assigned")
      .data(vectors)
      .join("rect")
      .attr("class", "assigned")
      .attr("x", innerW + 12)
      .attr("y", (d) => y(d.id) ?? 0)
      .attr("width", (d) => bar(d.assignedSolutions))
      .attr("height", y.bandwidth())
      .attr("fill", "#7c3aed");
  }

  onMount(draw);
  $: if (svgEl) draw();
</script>

<div class="scroll">
  <svg bind:this={svgEl}></svg>
</div>

<style>
  .scroll {
    max-height: 360px;
    overflow-y: auto;
  }

  svg {
    width: 100%;
    height: auto;
  }
</style>