<script lang="ts">
  import { onMount } from "svelte";
  import * as d3 from "d3";

  import type { ADMLog } from "$lib/adm/types";

  import {
    getIteration,
    getObjectives
  } from "$lib/adm/adapters";

  export let log: ADMLog;
  export let selectedIteration: number;
  export let selectedVector: string | null = null;

  export let width = 760;
  export let height = 330;

  let svgEl: SVGSVGElement;

  $: iteration =
    getIteration(log, selectedIteration);

  $: objectives =
    getObjectives(log);

  function draw() {
    if (!svgEl) return;

    const svg = d3.select(svgEl);

    svg.selectAll("*").remove();

    const margin = {
      top: 28,
      right: 24,
      bottom: 20,
      left: 24
    };

    const innerW =
      width - margin.left - margin.right;

    const innerH =
      height - margin.top - margin.bottom;

    const solutions =
      iteration.composite_front;

    const x =
      d3.scalePoint<number>()
        .domain(
          d3.range(objectives.length)
        )
        .range([0, innerW]);

    const extents =
      objectives.map((_, index) =>
        d3.extent(
          solutions,
          d => d.objectives[index]
        ) as [number, number]
      );

    const yScales =
      extents.map(extent =>
        d3.scaleLinear()
          .domain(extent)
          .nice()
          .range([innerH, 0])
      );

    const methodColor =
      d3.scaleOrdinal<string>()
        .domain(log.methods)
        .range([
          "#6446ef",
          "#ef5350",
          "#2f80ed",
          "#f59e0b"
        ]);

    const line =
      d3.line<number>()
        .x((_, index) =>
          x(index) ?? 0
        )
        .y((value, index) =>
          yScales[index](value)
        )
        .curve(d3.curveLinear);

    const g =
      svg
        .attr(
          "viewBox",
          `0 0 ${width} ${height}`
        )
        .append("g")
        .attr(
          "transform",
          `translate(${margin.left},${margin.top})`
        );

    // solution lines
    g.append("g")
      .selectAll("path")
      .data(solutions)
      .join("path")
      .attr(
        "d",
        d => line(d.objectives)
      )
      .attr("fill", "none")
      .attr(
        "stroke",
        d => methodColor(d.method)
      )
      .attr("stroke-width", 1)
      .attr("stroke-opacity", 0.16)
      .on("mouseenter", function () {
        d3.select(this)
          .attr("stroke-opacity", 0.95)
          .attr("stroke-width", 2.2);
      })
      .on("mouseleave", function () {
        d3.select(this)
          .attr("stroke-opacity", 0.16)
          .attr("stroke-width", 1);
      });

    // reference point
    const reference =
      iteration.preference_information
        .reference_point;

    g.append("path")
      .datum(reference)
      .attr(
        "d",
        line(reference)
      )
      .attr("fill", "none")
      .attr("stroke", "#111827")
      .attr("stroke-width", 2)
      .attr("stroke-dasharray", "5 4");

    // axes
    const axes =
      g.selectAll(".axis")
        .data(
          objectives.map(
            (objective, index) => ({
              objective,
              index
            })
          )
        )
        .join("g")
        .attr("class", "axis")
        .attr(
          "transform",
          d =>
            `translate(${x(d.index)},0)`
        );

    axes.each(function(d) {
      d3.select(this)
        .call(
          d3.axisLeft(
            yScales[d.index]
          )
          .ticks(4)
          .tickSize(3)
        );
    });

    axes
      .append("text")
      .attr("y", -12)
      .attr("text-anchor", "middle")
      .attr("fill", "#222")
      .attr("font-size", 12)
      .attr("font-weight", 700)
      .text(d => d.objective);

    // reference-point markers
    g.append("g")
      .selectAll("circle")
      .data(reference)
      .join("circle")
      .attr(
        "cx",
        (_, i) => x(i) ?? 0
      )
      .attr(
        "cy",
        (d, i) => yScales[i](d)
      )
      .attr("r", 4)
      .attr("fill", "#111827");
  }

  onMount(draw);

  $: if (
    svgEl &&
    selectedIteration
  ) {
    draw();
  }
</script>

<svg bind:this={svgEl}></svg>

<div class="legend">
  {#each log.methods as method, i}
    <span>
      <i
        style={`background:${
          [
            "#6446ef",
            "#ef5350",
            "#2f80ed",
            "#f59e0b"
          ][i]
        }`}
      ></i>
      {method}
    </span>
  {/each}

  <span>
    <i class="reference"></i>
    ADM reference point
  </span>
</div>

<style>
  svg {
    width: 100%;
    display: block;
  }

  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin-top: 0.45rem;
    color: #72798b;
    font-size: 0.68rem;
  }

  .legend span {
    display: flex;
    align-items: center;
    gap: 0.35rem;
  }

  .legend i {
    display: inline-block;
    width: 14px;
    height: 2px;
  }

  .legend .reference {
    background: #111827;
  }

  :global(.axis path),
  :global(.axis line) {
    stroke: #adb3c0;
  }

  :global(.axis text) {
    fill: #7d8494;
    font-size: 9px;
  }
</style>