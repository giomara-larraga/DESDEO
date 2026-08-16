<script lang="ts">
  import { onMount } from "svelte";
  import * as d3 from "d3";

  import type { ADMLog } from "$lib/adm/types";
  import { getIteration } from "$lib/adm/adapters";

  export let log: ADMLog;
  export let selectedIteration: number;

  // Bind this from Dashboard.svelte if you want the selected generation
  // to update other coordinated views.
  export let selectedGeneration: number | null = null;

  export let width = 760;
  export let height = 300;

  type MetricType = "phi" | "positive" | "negative";

  type GenerationPoint = {
    method: string;
    generation: number;
    value: number;
  };

  let metric: MetricType = "phi";
  let svgEl: SVGSVGElement;

  let tooltipVisible = false;
  let tooltipX = 0;
  let tooltipY = 0;
  let tooltipGeneration = 0;
  let tooltipValues: {
    method: string;
    value: number;
    color: string;
  }[] = [];

  $: iteration = getIteration(log, selectedIteration);

  $: metricLabel =
    metric === "phi"
      ? "Φ"
      : metric === "positive"
        ? "Positive Hypervolume"
        : "Negative Hypervolume";

  $: metricDescription =
    metric === "phi"
      ? "Performance evolution within the selected interaction"
      : metric === "positive"
        ? "Positive hypervolume evolution within the selected interaction"
        : "Negative hypervolume evolution within the selected interaction";

  function getMetricValues(method: string): number[] {
    const values = iteration.hypervolume[method];

    if (!values) {
      return [];
    }

    if (metric === "positive") {
      return values.positive_hypervolume_per_generation ?? [];
    }

    if (metric === "negative") {
      return values.negative_hypervolume_per_generation ?? [];
    }

    return values.phi_per_generation ?? [];
  }

  function getInteractionValue(method: string): number | null {
    if (metric !== "phi") {
      return null;
    }

    return iteration.hypervolume[method]?.phi_iteration ?? null;
  }

  function setMetric(nextMetric: MetricType) {
    metric = nextMetric;
    selectedGeneration = null;
  }

  function draw() {
    if (!svgEl) return;

    const svg = d3.select(svgEl);

    svg.selectAll("*").remove();

    const margin = {
      top: 18,
      right: 28,
      bottom: 42,
      left: 62
    };

    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const series = log.methods.map((method) => ({
      method,
      values: getMetricValues(method).map((value, index) => ({
        method,
        generation: index + 1,
        value
      }))
    }));

    const allPoints = series.flatMap((d) => d.values);

    if (allPoints.length === 0) {
      svg
        .attr("viewBox", `0 0 ${width} ${height}`)
        .append("text")
        .attr("x", width / 2)
        .attr("y", height / 2)
        .attr("text-anchor", "middle")
        .attr("fill", "#8a91a3")
        .attr("font-size", 13)
        .text("No generation data available.");

      return;
    }

    const generations = d3.max(
      allPoints,
      (d) => d.generation
    ) ?? log.adm_configuration.generations_per_iteration;

    const x = d3
      .scaleLinear()
      .domain([1, generations])
      .range([0, innerWidth]);

    let yMin = d3.min(allPoints, (d) => d.value) ?? 0;
    let yMax = d3.max(allPoints, (d) => d.value) ?? 1;

    if (metric === "phi") {
      yMin = Math.min(0, yMin);
    }

    if (yMin === yMax) {
      yMax = yMin + 1;
    }

    const padding = (yMax - yMin) * 0.06;

    const y = d3
      .scaleLinear()
      .domain([
        metric === "phi"
          ? Math.min(0, yMin - padding)
          : Math.max(0, yMin - padding),
        yMax + padding
      ])
      .nice()
      .range([innerHeight, 0]);

    /*
     * Keep method colors stable across all charts.
     * Add more colors here if you later compare more methods.
     */
    const methodColors = [
      "#6546e8",
      "#ef4444",
      "#0284c7",
      "#f59e0b",
      "#16a34a"
    ];

    const color = d3
      .scaleOrdinal<string, string>()
      .domain(log.methods)
      .range(methodColors);

    const root = svg
      .attr("viewBox", `0 0 ${width} ${height}`)
      .attr("preserveAspectRatio", "xMidYMid meet")
      .append("g")
      .attr(
        "transform",
        `translate(${margin.left},${margin.top})`
      );

    /*
     * Grid lines
     */
    root
      .append("g")
      .attr("class", "grid")
      .call(
        d3
          .axisLeft(y)
          .ticks(5)
          .tickSize(-innerWidth)
          .tickFormat(() => "")
      )
      .call((g) => g.select(".domain").remove())
      .call((g) =>
        g
          .selectAll("line")
          .attr("stroke", "#edf0f5")
          .attr("stroke-width", 1)
      );

    /*
     * X axis
     */
    root
      .append("g")
      .attr("class", "axis")
      .attr(
        "transform",
        `translate(0,${innerHeight})`
      )
      .call(
        d3
          .axisBottom(x)
          .ticks(
            Math.min(
              10,
              Math.max(5, Math.floor(generations / 10))
            )
          )
          .tickFormat((d) => String(Math.round(Number(d))))
      )
      .call((g) => g.select(".domain").attr("stroke", "#cdd2dc"));

    /*
     * Y axis
     */
    root
      .append("g")
      .attr("class", "axis")
      .call(
        d3
          .axisLeft(y)
          .ticks(5)
          .tickFormat((d) => {
            const value = Number(d);

            if (Math.abs(value) >= 1000) {
              return d3.format(".2s")(value);
            }

            if (Math.abs(value) < 0.01 && value !== 0) {
              return d3.format(".1e")(value);
            }

            return d3.format(".2f")(value);
          })
      )
      .call((g) => g.select(".domain").attr("stroke", "#cdd2dc"));

    /*
     * Axis labels
     */
    root
      .append("text")
      .attr("x", innerWidth / 2)
      .attr("y", innerHeight + 36)
      .attr("text-anchor", "middle")
      .attr("fill", "#6b7280")
      .attr("font-size", 11)
      .text("Generation");

    root
      .append("text")
      .attr(
        "transform",
        `translate(${-46},${innerHeight / 2}) rotate(-90)`
      )
      .attr("text-anchor", "middle")
      .attr("fill", "#6b7280")
      .attr("font-size", 11)
      .text(metricLabel);

    /*
     * Line generator
     */
    const line = d3
      .line<GenerationPoint>()
      .defined((d) => Number.isFinite(d.value))
      .x((d) => x(d.generation))
      .y((d) => y(d.value))
      .curve(d3.curveMonotoneX);

    /*
     * Draw a line for each method
     */
    for (const methodSeries of series) {
      root
        .append("path")
        .datum(methodSeries.values)
        .attr("fill", "none")
        .attr(
          "stroke",
          color(methodSeries.method)
        )
        .attr("stroke-width", 2.2)
        .attr("stroke-linejoin", "round")
        .attr("stroke-linecap", "round")
        .attr("d", line);

      /*
       * Small points are intentionally mostly invisible.
       * They become visible when hovering.
       */
      root
        .append("g")
        .selectAll("circle")
        .data(methodSeries.values)
        .join("circle")
        .attr(
          "cx",
          (d) => x(d.generation)
        )
        .attr(
          "cy",
          (d) => y(d.value)
        )
        .attr("r", 1.7)
        .attr(
          "fill",
          color(methodSeries.method)
        )
        .attr("opacity", 0.45);
    }

    /*
     * Show the aggregate interaction-level Φ as a dashed horizontal line.
     *
     * Note: because each method has its own phi_iteration, draw one
     * aggregate line for each method.
     */
    if (metric === "phi") {
      for (const method of log.methods) {
        const aggregate = getInteractionValue(method);

        if (
          aggregate === null ||
          !Number.isFinite(aggregate)
        ) {
          continue;
        }

        root
          .append("line")
          .attr("x1", 0)
          .attr("x2", innerWidth)
          .attr("y1", y(aggregate))
          .attr("y2", y(aggregate))
          .attr(
            "stroke",
            color(method)
          )
          .attr("stroke-width", 1)
          .attr("stroke-dasharray", "5 4")
          .attr("opacity", 0.45);
      }
    }

    /*
     * Selected-generation line.
     */
    const selectionGroup = root
      .append("g")
      .style("pointer-events", "none");

    const selectionLine = selectionGroup
      .append("line")
      .attr("y1", 0)
      .attr("y2", innerHeight)
      .attr("stroke", "#6d4aff")
      .attr("stroke-width", 1)
      .attr("stroke-dasharray", "4 3")
      .attr("opacity", 0);

    const selectionLabel = selectionGroup
      .append("g")
      .attr("opacity", 0);

    selectionLabel
      .append("rect")
      .attr("x", -15)
      .attr("y", -17)
      .attr("width", 30)
      .attr("height", 18)
      .attr("rx", 4)
      .attr("fill", "#6546e8");

    selectionLabel
      .append("text")
      .attr("x", 0)
      .attr("y", -5)
      .attr("text-anchor", "middle")
      .attr("fill", "white")
      .attr("font-size", 9)
      .attr("font-weight", 700);

    function showGeneration(
      generation: number,
      persist = false
    ) {
      const clamped = Math.max(
        1,
        Math.min(generations, generation)
      );

      selectionLine
        .attr("x1", x(clamped))
        .attr("x2", x(clamped))
        .attr("opacity", 1);

      selectionLabel
        .attr(
          "transform",
          `translate(${x(clamped)},0)`
        )
        .attr("opacity", 1);

      selectionLabel
        .select("text")
        .text(clamped);

      if (persist) {
        selectedGeneration = clamped;
      }
    }

    if (selectedGeneration !== null) {
      showGeneration(selectedGeneration);
    }

    /*
     * Hover layer
     */
    root
      .append("rect")
      .attr("width", innerWidth)
      .attr("height", innerHeight)
      .attr("fill", "transparent")
      .style("cursor", "crosshair")
      .on("mousemove", function (event) {
        const [mouseX] = d3.pointer(event, this);

        const generation = Math.max(
          1,
          Math.min(
            generations,
            Math.round(x.invert(mouseX))
          )
        );

        showGeneration(generation);

        tooltipGeneration = generation;

        tooltipValues = series
          .map((methodSeries) => {
            const point =
              methodSeries.values[generation - 1];

            return {
              method: methodSeries.method,
              value: point?.value ?? Number.NaN,
              color: color(methodSeries.method)
            };
          })
          .filter((d) => Number.isFinite(d.value));

        const bounds =
          svgEl.getBoundingClientRect();

        tooltipX =
          event.clientX - bounds.left + 12;

        tooltipY =
          event.clientY - bounds.top + 10;

        tooltipVisible = true;
      })
      .on("mouseleave", () => {
        tooltipVisible = false;

        if (selectedGeneration !== null) {
          showGeneration(selectedGeneration);
        } else {
          selectionLine.attr("opacity", 0);
          selectionLabel.attr("opacity", 0);
        }
      })
      .on("click", function (event) {
        const [mouseX] = d3.pointer(event, this);

        const generation = Math.max(
          1,
          Math.min(
            generations,
            Math.round(x.invert(mouseX))
          )
        );

        showGeneration(generation, true);
      });
  }

  onMount(() => {
    draw();
  });

  $: if (
    svgEl &&
    selectedIteration &&
    metric
  ) {
    draw();
  }
</script>

<div class="generation-performance">

  <div class="header">
    <div>
      <h3>
        Performance per Generation
        <span>
          (Interaction {selectedIteration})
        </span>
      </h3>

      <p>{metricDescription}</p>
    </div>

    <div
      class="tabs"
      role="group"
      aria-label="Generation metric"
    >
      <button
        type="button"
        class:active={metric === "phi"}
        on:click={() => setMetric("phi")}
      >
        Φ
      </button>

      <button
        type="button"
        class:active={metric === "positive"}
        on:click={() => setMetric("positive")}
      >
        Positive HV
      </button>

      <button
        type="button"
        class:active={metric === "negative"}
        on:click={() => setMetric("negative")}
      >
        Negative HV
      </button>
    </div>
  </div>

  <div class="chart-wrapper">
    <svg bind:this={svgEl}></svg>

    {#if tooltipVisible}
      <div
        class="tooltip"
        style:left={`${tooltipX}px`}
        style:top={`${tooltipY}px`}
      >
        <strong>
          Generation {tooltipGeneration}
        </strong>

        {#each tooltipValues as item}
          <div class="tooltip-row">
            <span
              class="method-dot"
              style:background={item.color}
            ></span>

            <span>{item.method}</span>

            <b>
              {metric === "phi"
                ? item.value.toFixed(4)
                : item.value.toPrecision(5)}
            </b>
          </div>
        {/each}
      </div>
    {/if}
  </div>

  <div class="footer">
    <div class="legend">
      {#each log.methods as method, index}
        <div class="legend-item">
          <span
            class="legend-line"
            style:background={
              [
                "#6546e8",
                "#ef4444",
                "#0284c7",
                "#f59e0b",
                "#16a34a"
              ][index % 5]
            }
          ></span>

          <span>{method}</span>
        </div>
      {/each}

      {#if metric === "phi"}
        <div class="legend-item aggregate">
          <span class="legend-line dashed"></span>
          <span>Interaction-level Φ</span>
        </div>
      {/if}
    </div>

    {#if selectedGeneration !== null}
      <button
        type="button"
        class="clear-button"
        on:click={() => {
          selectedGeneration = null;
          draw();
        }}
      >
        Clear generation selection
      </button>
    {/if}
  </div>

</div>

<style>
  .generation-performance {
    width: 100%;
    min-width: 0;
  }

  .header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.65rem;
  }

  h3 {
    margin: 0;
    color: #171b27;
    font-size: 0.9rem;
    font-weight: 700;
  }

  h3 span {
    color: #72798b;
    font-size: 0.76rem;
    font-weight: 500;
  }

  p {
    margin: 0.2rem 0 0;
    color: #8b92a3;
    font-size: 0.69rem;
  }

  .tabs {
    display: flex;
    align-items: center;
    padding: 0.18rem;
    border: 1px solid #e5e7ee;
    border-radius: 7px;
    background: #f7f8fb;
  }

  .tabs button {
    border: 0;
    border-radius: 5px;
    padding: 0.38rem 0.68rem;

    background: transparent;
    color: #687084;

    font: inherit;
    font-size: 0.67rem;
    font-weight: 600;

    cursor: pointer;

    transition:
      background 0.15s ease,
      color 0.15s ease,
      box-shadow 0.15s ease;
  }

  .tabs button:hover {
    color: #4f36d7;
  }

  .tabs button.active {
    background: white;
    color: #5b3ee4;

    box-shadow:
      0 1px 2px rgb(15 23 42 / 0.05),
      0 0 0 1px rgb(101 70 232 / 0.08);
  }

  .chart-wrapper {
    position: relative;
    width: 100%;
  }

  svg {
    display: block;
    width: 100%;
    height: auto;
    overflow: visible;
  }

  :global(.axis text) {
    fill: #7b8294;
    font-size: 9px;
  }

  :global(.axis line) {
    stroke: #cfd4de;
  }

  .tooltip {
    position: absolute;
    z-index: 10;

    min-width: 155px;
    padding: 0.55rem 0.65rem;

    pointer-events: none;

    border: 1px solid #e2e5ed;
    border-radius: 7px;

    background: rgba(255, 255, 255, 0.97);

    box-shadow:
      0 8px 24px rgb(15 23 42 / 0.12);
  }

  .tooltip strong {
    display: block;
    margin-bottom: 0.42rem;

    color: #333949;
    font-size: 0.69rem;
  }

  .tooltip-row {
    display: grid;
    grid-template-columns: 8px 1fr auto;
    align-items: center;
    gap: 0.4rem;

    margin-top: 0.28rem;

    color: #687084;
    font-size: 0.65rem;
  }

  .tooltip-row b {
    color: #242a38;
    font-size: 0.65rem;
    font-variant-numeric: tabular-nums;
  }

  .method-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
  }

  .footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;

    margin-top: 0.3rem;
  }

  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.8rem;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 0.32rem;

    color: #71788a;
    font-size: 0.65rem;
  }

  .legend-line {
    display: block;
    width: 16px;
    height: 2px;
    border-radius: 2px;
  }

  .legend-line.dashed {
    height: 0;
    border-top: 1px dashed #8b92a3;
    background: none;
  }

  .aggregate {
    color: #9097a7;
  }

  .clear-button {
    padding: 0;
    border: 0;
    background: transparent;

    color: #6546e8;
    font-size: 0.64rem;

    cursor: pointer;
  }

  .clear-button:hover {
    text-decoration: underline;
  }

  @media (max-width: 680px) {
    .header {
      flex-direction: column;
    }

    .tabs {
      width: 100%;
    }

    .tabs button {
      flex: 1;
    }

    .footer {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>