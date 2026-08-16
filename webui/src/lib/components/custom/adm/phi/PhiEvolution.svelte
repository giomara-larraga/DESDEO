<script lang="ts">
  import { onMount } from "svelte";
  import * as d3 from "d3";

  import type { ADMLog } from "$lib/adm/types";

  export let log: ADMLog;
  export let selectedIteration: number;

  export let onSelect: (iteration: number) => void = () => {};

  export let width = 760;
  export let height = 240;

  type PhiPoint = {
    method: string;
    iteration: number;
    phase: "learning" | "decision";
    value: number;
  };

  let svgEl: SVGSVGElement;

  let tooltipVisible = false;
  let tooltipX = 0;
  let tooltipY = 0;

  let tooltipIteration = 1;
  let tooltipPhase = "";

  let tooltipValues: {
    method: string;
    value: number;
    color: string;
  }[] = [];

  function getPhiValue(
    iteration: (typeof log.iterations)[number],
    method: string
  ): number | null {
    const value =
      iteration.hypervolume?.[method]?.phi_iteration;

    if (
      value === undefined ||
      value === null ||
      !Number.isFinite(value)
    ) {
      return null;
    }

    return value;
  }

  function draw() {
    if (!svgEl) return;

    const svg = d3.select(svgEl);

    svg.selectAll("*").remove();

    const margin = {
      top: 18,
      right: 28,
      bottom: 38,
      left: 58
    };

    const innerWidth =
      width -
      margin.left -
      margin.right;

    const innerHeight =
      height -
      margin.top -
      margin.bottom;

    /*
     * ----------------------------------------------------
     * Build method series
     * ----------------------------------------------------
     */

    const series = log.methods.map((method) => ({
      method,

      values: log.iterations
        .map((iteration) => {
          const value =
            getPhiValue(
              iteration,
              method
            );

          if (value === null) {
            return null;
          }

          return {
            method,
            iteration:
              iteration.iteration,
            phase:
              iteration.phase,
            value
          } satisfies PhiPoint;
        })
        .filter(
          (d): d is PhiPoint =>
            d !== null
        )
    }));

    const allPoints =
      series.flatMap(
        (seriesItem) =>
          seriesItem.values
      );

    if (allPoints.length === 0) {
      svg
        .attr(
          "viewBox",
          `0 0 ${width} ${height}`
        )
        .append("text")
        .attr(
          "x",
          width / 2
        )
        .attr(
          "y",
          height / 2
        )
        .attr(
          "text-anchor",
          "middle"
        )
        .attr(
          "fill",
          "#8a91a3"
        )
        .attr(
          "font-size",
          12
        )
        .text(
          "No interaction-level Φ values available."
        );

      return;
    }

    /*
     * ----------------------------------------------------
     * Scales
     * ----------------------------------------------------
     */

    const x = d3
      .scaleLinear()
      .domain([
        1,
        log.iterations.length
      ])
      .range([
        0,
        innerWidth
      ]);

    let yMin =
      d3.min(
        allPoints,
        (d) => d.value
      ) ?? 0;

    let yMax =
      d3.max(
        allPoints,
        (d) => d.value
      ) ?? 1;

    /*
     * Φ is commonly displayed relative to zero,
     * so keep zero visible if all values are positive.
     */
    yMin =
      Math.min(
        0,
        yMin
      );

    if (yMin === yMax) {
      yMax =
        yMin + 1;
    }

    const padding =
      (yMax - yMin) *
      0.08;

    const y = d3
      .scaleLinear()
      .domain([
        Math.min(
          0,
          yMin - padding
        ),
        yMax + padding
      ])
      .nice()
      .range([
        innerHeight,
        0
      ]);

    const methodColors = [
      "#6546e8",
      "#ef4444",
      "#0284c7",
      "#f59e0b",
      "#16a34a"
    ];

    const color = d3
      .scaleOrdinal<
        string,
        string
      >()
      .domain(
        log.methods
      )
      .range(
        methodColors
      );

    /*
     * ----------------------------------------------------
     * Root
     * ----------------------------------------------------
     */

    const root = svg
      .attr(
        "viewBox",
        `0 0 ${width} ${height}`
      )
      .attr(
        "preserveAspectRatio",
        "xMidYMid meet"
      )
      .append("g")
      .attr(
        "transform",
        `translate(${margin.left},${margin.top})`
      );

    /*
     * ----------------------------------------------------
     * Phase backgrounds
     * ----------------------------------------------------
     */

    const learningCount =
      log.adm_configuration
        .learning_iterations;

    const decisionCount =
      log.adm_configuration
        .decision_iterations;

    const interactionSpacing =
      log.iterations.length > 1
        ? x(2) - x(1)
        : innerWidth;

    /*
     * Extend the phase backgrounds halfway around
     * the first / last interaction center.
     */

    const learningStart =
      Math.max(
        0,
        x(1) -
          interactionSpacing / 2
      );

    const learningEnd =
      Math.min(
        innerWidth,
        x(learningCount) +
          interactionSpacing / 2
      );

    root
      .append("rect")
      .attr(
        "x",
        learningStart
      )
      .attr(
        "y",
        0
      )
      .attr(
        "width",
        Math.max(
          0,
          learningEnd -
            learningStart
        )
      )
      .attr(
        "height",
        innerHeight
      )
      .attr(
        "fill",
        "#f4f0ff"
      )
      .attr(
        "opacity",
        0.55
      );

    if (decisionCount > 0) {
      const decisionStartIteration =
        learningCount + 1;

      const decisionStart =
        Math.max(
          0,
          x(
            decisionStartIteration
          ) -
            interactionSpacing / 2
        );

      root
        .append("rect")
        .attr(
          "x",
          decisionStart
        )
        .attr(
          "y",
          0
        )
        .attr(
          "width",
          innerWidth -
            decisionStart
        )
        .attr(
          "height",
          innerHeight
        )
        .attr(
          "fill",
          "#fff3ea"
        )
        .attr(
          "opacity",
          0.55
        );

      root
        .append("line")
        .attr(
          "x1",
          decisionStart
        )
        .attr(
          "x2",
          decisionStart
        )
        .attr(
          "y1",
          0
        )
        .attr(
          "y2",
          innerHeight
        )
        .attr(
          "stroke",
          "#d6dae3"
        )
        .attr(
          "stroke-dasharray",
          "4 4"
        );
    }

    /*
     * Phase labels
     */

    if (learningCount > 0) {
      root
        .append("text")
        .attr(
          "x",
          (
            learningStart +
            learningEnd
          ) / 2
        )
        .attr(
          "y",
          12
        )
        .attr(
          "text-anchor",
          "middle"
        )
        .attr(
          "fill",
          "#7c63d8"
        )
        .attr(
          "font-size",
          9
        )
        .attr(
          "font-weight",
          700
        )
        .text(
          "LEARNING"
        );
    }

    if (
      decisionCount > 0
    ) {
      const decisionStart =
        Math.max(
          0,
          x(
            learningCount + 1
          ) -
            interactionSpacing / 2
        );

      root
        .append("text")
        .attr(
          "x",
          (
            decisionStart +
            innerWidth
          ) / 2
        )
        .attr(
          "y",
          12
        )
        .attr(
          "text-anchor",
          "middle"
        )
        .attr(
          "fill",
          "#d47a37"
        )
        .attr(
          "font-size",
          9
        )
        .attr(
          "font-weight",
          700
        )
        .text(
          "DECISION"
        );
    }

    /*
     * ----------------------------------------------------
     * Grid
     * ----------------------------------------------------
     */

    root
      .append("g")
      .attr(
        "class",
        "grid"
      )
      .call(
        d3
          .axisLeft(y)
          .ticks(5)
          .tickSize(
            -innerWidth
          )
          .tickFormat(
            () => ""
          )
      )
      .call(
        (g) =>
          g
            .select(
              ".domain"
            )
            .remove()
      )
      .call(
        (g) =>
          g
            .selectAll(
              "line"
            )
            .attr(
              "stroke",
              "#e9ecf2"
            )
            .attr(
              "stroke-width",
              1
            )
      );

    /*
     * ----------------------------------------------------
     * Axes
     * ----------------------------------------------------
     */

    root
      .append("g")
      .attr(
        "class",
        "axis"
      )
      .attr(
        "transform",
        `translate(0,${innerHeight})`
      )
      .call(
        d3
          .axisBottom(x)
          .tickValues(
            log.iterations.map(
              (d) =>
                d.iteration
            )
          )
          .tickFormat(
            (d) =>
              String(
                Math.round(
                  Number(d)
                )
              )
          )
      )
      .call(
        (g) =>
          g
            .select(
              ".domain"
            )
            .attr(
              "stroke",
              "#cbd0da"
            )
      );

    root
      .append("g")
      .attr(
        "class",
        "axis"
      )
      .call(
        d3
          .axisLeft(y)
          .ticks(5)
          .tickFormat(
            (d) => {
              const value =
                Number(d);

              if (
                Math.abs(value) <
                  0.01 &&
                value !== 0
              ) {
                return d3.format(
                  ".1e"
                )(value);
              }

              return d3.format(
                ".3f"
              )(value);
            }
          )
      )
      .call(
        (g) =>
          g
            .select(
              ".domain"
            )
            .attr(
              "stroke",
              "#cbd0da"
            )
      );

    root
      .append("text")
      .attr(
        "x",
        innerWidth / 2
      )
      .attr(
        "y",
        innerHeight + 33
      )
      .attr(
        "text-anchor",
        "middle"
      )
      .attr(
        "fill",
        "#70788a"
      )
      .attr(
        "font-size",
        10
      )
      .text(
        "Interaction"
      );

    root
      .append("text")
      .attr(
        "transform",
        `translate(${-43},${innerHeight / 2}) rotate(-90)`
      )
      .attr(
        "text-anchor",
        "middle"
      )
      .attr(
        "fill",
        "#70788a"
      )
      .attr(
        "font-size",
        10
      )
      .text(
        "Φ"
      );

    /*
     * ----------------------------------------------------
     * Method lines
     * ----------------------------------------------------
     */

    const line = d3
      .line<PhiPoint>()
      .x(
        (d) =>
          x(d.iteration)
      )
      .y(
        (d) =>
          y(d.value)
      )
      .curve(
        d3.curveMonotoneX
      );

    for (
      const methodSeries
      of series
    ) {
      root
        .append("path")
        .datum(
          methodSeries.values
        )
        .attr(
          "d",
          line
        )
        .attr(
          "fill",
          "none"
        )
        .attr(
          "stroke",
          color(
            methodSeries.method
          )
        )
        .attr(
          "stroke-width",
          2.3
        )
        .attr(
          "stroke-linecap",
          "round"
        )
        .attr(
          "stroke-linejoin",
          "round"
        );

      root
        .append("g")
        .selectAll(
          "circle"
        )
        .data(
          methodSeries.values
        )
        .join(
          "circle"
        )
        .attr(
          "cx",
          (d) =>
            x(
              d.iteration
            )
        )
        .attr(
          "cy",
          (d) =>
            y(
              d.value
            )
        )
        .attr(
          "r",
          (d) =>
            d.iteration ===
            selectedIteration
              ? 5
              : 3.4
        )
        .attr(
          "fill",
          (d) =>
            d.iteration ===
            selectedIteration
              ? color(
                  methodSeries.method
                )
              : "white"
        )
        .attr(
          "stroke",
          color(
            methodSeries.method
          )
        )
        .attr(
          "stroke-width",
          2
        );
    }

    /*
     * ----------------------------------------------------
     * Selected interaction indicator
     * ----------------------------------------------------
     */

    const selectedX =
      x(selectedIteration);

    root
      .append("line")
      .attr(
        "x1",
        selectedX
      )
      .attr(
        "x2",
        selectedX
      )
      .attr(
        "y1",
        0
      )
      .attr(
        "y2",
        innerHeight
      )
      .attr(
        "stroke",
        "#6d4aff"
      )
      .attr(
        "stroke-width",
        1
      )
      .attr(
        "stroke-dasharray",
        "4 3"
      )
      .attr(
        "opacity",
        0.55
      );

    /*
     * ----------------------------------------------------
     * Interaction hit areas
     * ----------------------------------------------------
     */

    const interactionHitWidth =
      Math.max(
        26,
        interactionSpacing *
          0.8
      );

    root
      .append("g")
      .selectAll(
        "rect"
      )
      .data(
        log.iterations
      )
      .join(
        "rect"
      )
      .attr(
        "x",
        (d) =>
          x(
            d.iteration
          ) -
          interactionHitWidth /
            2
      )
      .attr(
        "y",
        0
      )
      .attr(
        "width",
        interactionHitWidth
      )
      .attr(
        "height",
        innerHeight
      )
      .attr(
        "fill",
        "transparent"
      )
      .style(
        "cursor",
        "pointer"
      )
      .on(
        "mousemove",
        function (
          event,
          iteration
        ) {
          tooltipIteration =
            iteration.iteration;

          tooltipPhase =
            iteration.phase;

          tooltipValues =
            log.methods
              .map(
                (
                  method
                ) => {
                  const value =
                    getPhiValue(
                      iteration,
                      method
                    );

                  return {
                    method,
                    value:
                      value ??
                      Number.NaN,
                    color:
                      color(
                        method
                      )
                  };
                }
              )
              .filter(
                (d) =>
                  Number.isFinite(
                    d.value
                  )
              );

          const bounds =
            svgEl.getBoundingClientRect();

          tooltipX =
            event.clientX -
            bounds.left +
            10;

          tooltipY =
            event.clientY -
            bounds.top +
            10;

          tooltipVisible =
            true;
        }
      )
      .on(
        "mouseleave",
        () => {
          tooltipVisible =
            false;
        }
      )
      .on(
        "click",
        (
          _event,
          iteration
        ) => {
          onSelect(
            iteration.iteration
          );
        }
      );
  }

  onMount(() => {
    draw();
  });

  $: if (
    svgEl &&
    selectedIteration
  ) {
    draw();
  }
</script>

<div class="phi-evolution">

  <div class="chart-wrapper">

    <svg bind:this={svgEl}></svg>

    {#if tooltipVisible}

      <div
        class="tooltip"
        style:left={`${tooltipX}px`}
        style:top={`${tooltipY}px`}
      >

        <div class="tooltip-header">

          <strong>
            Interaction
            {tooltipIteration}
          </strong>

          <span
            class:learning={
              tooltipPhase ===
              "learning"
            }
            class:decision={
              tooltipPhase ===
              "decision"
            }
            class="phase"
          >
            {tooltipPhase}
          </span>

        </div>

        {#each tooltipValues as item}

          <div class="tooltip-row">

            <span
              class="method-dot"
              style:background={
                item.color
              }
            ></span>

            <span>
              {item.method}
            </span>

            <b>
              {
                item.value.toFixed(
                  4
                )
              }
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

          <span>
            {method}
          </span>

        </div>

      {/each}

    </div>

    <div class="phase-legend">

      <span>
        <i class="learning-box"></i>
        Learning
      </span>

      <span>
        <i class="decision-box"></i>
        Decision
      </span>

    </div>

  </div>

</div>


<style>
  .phi-evolution {
    width: 100%;
    min-width: 0;
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
    fill: #788093;
    font-size: 9px;
  }

  :global(.axis line) {
    stroke: #cbd0da;
  }

  /*
   * Tooltip
   */

  .tooltip {
    position: absolute;
    z-index: 20;

    min-width: 150px;

    padding:
      0.55rem
      0.65rem;

    pointer-events: none;

    border:
      1px solid
      #e1e4ec;

    border-radius:
      7px;

    background:
      rgba(
        255,
        255,
        255,
        0.98
      );

    box-shadow:
      0 8px 25px
      rgb(15 23 42 / 0.12);
  }

  .tooltip-header {
    display: flex;
    align-items: center;
    justify-content: space-between;

    gap: 0.5rem;

    margin-bottom: 0.4rem;
  }

  .tooltip-header strong {
    color: #303646;
    font-size: 0.67rem;
  }

  .phase {
    padding:
      0.15rem
      0.34rem;

    border-radius:
      4px;

    font-size: 0.52rem;
    font-weight: 700;

    text-transform:
      capitalize;
  }

  .phase.learning {
    color: #6244d4;
    background: #f0ebff;
  }

  .phase.decision {
    color: #d46e29;
    background: #fff1e7;
  }

  .tooltip-row {
    display: grid;

    grid-template-columns:
      8px
      1fr
      auto;

    gap: 0.38rem;

    align-items: center;

    margin-top: 0.25rem;

    color: #6d7587;

    font-size: 0.62rem;
  }

  .tooltip-row b {
    color: #262c3a;

    font-size: 0.62rem;
    font-variant-numeric:
      tabular-nums;
  }

  .method-dot {
    width: 7px;
    height: 7px;

    border-radius:
      50%;
  }

  /*
   * Footer legends
   */

  .footer {
    display: flex;
    align-items: center;
    justify-content: space-between;

    gap: 1rem;

    margin-top:
      0.25rem;
  }

  .legend,
  .phase-legend {
    display: flex;
    flex-wrap: wrap;

    gap: 0.75rem;
  }

  .legend-item,
  .phase-legend span {
    display: flex;
    align-items: center;

    gap: 0.3rem;

    color: #747c8e;

    font-size: 0.61rem;
  }

  .legend-line {
    width: 16px;
    height: 2px;

    border-radius: 2px;
  }

  .phase-legend i {
    display: inline-block;

    width: 9px;
    height: 9px;

    border-radius: 2px;
  }

  .learning-box {
    background: #eee8ff;
    border: 1px solid #d9ceff;
  }

  .decision-box {
    background: #fff0e4;
    border: 1px solid #f5d4bd;
  }

  @media (
    max-width: 650px
  ) {
    .footer {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>