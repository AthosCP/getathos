<script lang="ts">
  import { onMount } from 'svelte';
  import { Chart, CategoryScale, LinearScale, Tooltip } from 'chart.js';
  import { MatrixController, MatrixElement } from 'chartjs-chart-matrix';
  import type { ChartData, ChartOptions } from 'chart.js';

  // Registrar controladores ANTES de crear el gráfico
  Chart.register(CategoryScale, LinearScale, Tooltip, MatrixController, MatrixElement);

  export let data: any;
  export let options: any;

  let canvas: HTMLCanvasElement;
  let chart: Chart;

  onMount(() => {
    chart = new Chart(canvas, {
      type: 'matrix',
      data: data,
      options: options
    });
    return () => {
      chart.destroy();
    };
  });

  $: if (chart && data) {
    chart.data = data;
    chart.update();
  }
</script>

<style>
  .chart-center {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
    width: 100%;
  }
</style>

<div class="chart-center">
  <canvas bind:this={canvas} width="900" height="400"></canvas>
</div> 