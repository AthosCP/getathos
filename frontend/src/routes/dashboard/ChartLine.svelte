<script lang="ts">
  import { onDestroy, afterUpdate, onMount } from 'svelte';
  import Chart from 'chart.js/auto';
  export let data: any;
  export let options: any;
  let canvas: HTMLCanvasElement;
  let chart: Chart|null = null;

  function renderChart() {
    if (chart) {
      chart.destroy();
    }
    chart = new Chart(canvas, {
      type: 'line',
      data,
      options
    });
  }

  onMount(() => {
    renderChart();
  });

  afterUpdate(() => {
    renderChart();
  });

  onDestroy(() => {
    if (chart) chart.destroy();
  });
</script>

<canvas bind:this={canvas} class="w-full h-48"></canvas> 