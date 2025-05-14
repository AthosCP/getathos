<script lang="ts">
  import { onMount } from 'svelte';
  import { Chart, RadialLinearScale, PointElement, LineElement, Filler } from 'chart.js';
  import type { ChartData, ChartOptions } from 'chart.js';

  Chart.register(RadialLinearScale, PointElement, LineElement, Filler);

  export let data: ChartData<'radar'>;
  export let options: ChartOptions<'radar'> = {
    responsive: true,
    plugins: {
      legend: {
        display: false
      },
      title: {
        display: false
      }
    },
    scales: {
      r: {
        beginAtZero: true,
        ticks: {
          display: false
        },
        pointLabels: {
          font: {
            size: 10,
            weight: 'bold'
          },
          color: '#374151',
          callback: function(label: string) {
            // Cortar cada 7 caracteres para evitar cortes feos
            const maxLen = 7;
            let result = [];
            for (let i = 0; i < label.length; i += maxLen) {
              result.push(label.slice(i, i + maxLen));
            }
            return result;
          }
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.1)'
        },
        angleLines: {
          color: 'rgba(0, 0, 0, 0.1)'
        }
      }
    }
  };

  let canvas: HTMLCanvasElement;
  let chart: Chart;

  onMount(() => {
    chart = new Chart(canvas, {
      type: 'radar',
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
  <canvas bind:this={canvas} width="600" height="600"></canvas>
</div> 