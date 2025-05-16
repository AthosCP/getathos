<script lang="ts">
  import { onMount, afterUpdate } from 'svelte';
  import { goto } from '$app/navigation';
  import AdminNavbar from '$lib/AdminNavbar.svelte';
  import { API_URL } from '$lib/config';
  import Chart from 'chart.js/auto';

  type Tenant = { 
    id: string; 
    name: string; 
    description: string; 
    users_count: number;
    created_at: string;
    status: string;
  };

  type DashboardStats = {
    total_clients: number;
    total_users: number;
    active_clients: number;
    active_users: number;
    recent_clients: Tenant[];
  };

  let stats: DashboardStats = {
    total_clients: 0,
    total_users: 0,
    active_clients: 0,
    active_users: 0,
    recent_clients: []
  };
  let loading = true;
  let error = '';
  let chartInstance: Chart | null = null;
  let chartCanvas: HTMLCanvasElement | null = null;

  async function loadDashboardData() {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        goto('/login');
        return;
      }

      const response = await fetch(`${API_URL}/api/admin/dashboard`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();
      if (data.success) {
        stats = data.data;
      } else {
        error = data.error || 'Error al cargar datos';
      }
    } catch (e) {
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }

  function getMonthlyClientEvolution() {
    // Agrupar clientes por mes de creación
    const months: Record<string, number> = {};
    stats.recent_clients.forEach(client => {
      const date = new Date(client.created_at);
      const key = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}`;
      months[key] = (months[key] || 0) + 1;
    });
    // Ordenar por fecha
    const sorted = Object.entries(months).sort(([a], [b]) => a.localeCompare(b));
    let total = 0;
    const labels = sorted.map(([k]) => k);
    const data = sorted.map(([_, v]) => (total += v)); // Acumulado
    return { labels, data };
  }

  function renderChart() {
    if (!chartCanvas) return;
    const { labels, data } = getMonthlyClientEvolution();
    if (chartInstance) {
      chartInstance.destroy();
    }
    chartInstance = new Chart(chartCanvas, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Clientes acumulados',
          data,
          borderColor: '#6366f1',
          backgroundColor: 'rgba(99,102,241,0.1)',
          tension: 0.3,
          fill: true,
          pointRadius: 4,
          pointBackgroundColor: '#6366f1',
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          title: { display: false }
        },
        scales: {
          x: { title: { display: true, text: 'Mes' } },
          y: { title: { display: true, text: 'Clientes' }, beginAtZero: true, ticks: { stepSize: 1 } }
        }
      }
    });
  }

  onMount(() => {
    const userRaw = localStorage.getItem('user');
    if (!userRaw) {
      goto('/login');
      return;
    }
    const user = JSON.parse(userRaw);
    if (user.role !== 'admin') {
      goto('/login');
      return;
    }
    loadDashboardData();
  });

  afterUpdate(() => {
    if (!loading && !error) {
      renderChart();
    }
  });
</script>

<AdminNavbar active="dashboard" />

<div class="min-h-screen bg-gray-100">
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
    {#if loading}
      <div class="text-center">Cargando...</div>
    {:else if error}
      <div class="text-red-500 text-center">{error}</div>
    {:else}
      <!-- Título de Bienvenida -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900">
          Bienvenido a Athos Cybersecurity Platform
        </h1>
        <p class="mt-2 text-sm text-gray-600">
          Panel de control para administrar tus clientes y monitorear el rendimiento
        </p>
      </div>

      <!-- Comisiones y Ganancias -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <!-- Comisiones del Mes -->
        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <dt class="text-sm font-medium text-gray-500 truncate">
              Comisiones de este mes
            </dt>
            <dd class="mt-1 text-3xl font-semibold text-green-600">
              $0.00
            </dd>
            <div class="mt-2 text-sm text-gray-500">
              <span class="text-green-500">↑ 12%</span> vs mes anterior
            </div>
          </div>
        </div>

        <!-- Ganancias Totales -->
        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <dt class="text-sm font-medium text-gray-500 truncate">
              Ganancias totales
            </dt>
            <dd class="mt-1 text-3xl font-semibold text-green-600">
              $0.00
            </dd>
            <div class="mt-2 text-sm text-gray-500">
              Acumulado desde el inicio
            </div>
          </div>
        </div>
      </div>

      <!-- Métricas principales -->
      <div class="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- Total Clientes -->
        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <dt class="text-sm font-medium text-gray-500 truncate">
              Total Clientes
            </dt>
            <dd class="mt-1 text-3xl font-semibold text-gray-900">
              {stats.total_clients}
            </dd>
          </div>
        </div>

        <!-- Total Usuarios -->
        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <dt class="text-sm font-medium text-gray-500 truncate">
              Total Usuarios
            </dt>
            <dd class="mt-1 text-3xl font-semibold text-gray-900">
              {stats.total_users}
            </dd>
          </div>
        </div>

        <!-- Clientes Activos -->
        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <dt class="text-sm font-medium text-gray-500 truncate">
              Clientes Activos
            </dt>
            <dd class="mt-1 text-3xl font-semibold text-gray-900">
              {stats.active_clients}
            </dd>
          </div>
        </div>

        <!-- Usuarios Activos -->
        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <dt class="text-sm font-medium text-gray-500 truncate">
              Usuarios Activos
            </dt>
            <dd class="mt-1 text-3xl font-semibold text-gray-900">
              {stats.active_users}
            </dd>
          </div>
        </div>
      </div>

      <!-- Gráfico de evolución de clientes -->
      <div class="mt-8 bg-white shadow rounded-lg p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-2">Evolución de clientes</h2>
        <canvas bind:this={chartCanvas} height="80"></canvas>
      </div>

      <!-- Clientes Recientes -->
      <div class="mt-8">
        <div class="bg-white shadow overflow-hidden sm:rounded-lg">
          <div class="px-4 py-5 sm:px-6">
            <h3 class="text-lg leading-6 font-medium text-gray-900">
              Clientes Recientes
            </h3>
            <p class="mt-1 max-w-2xl text-sm text-gray-500">
              Últimos clientes registrados en la plataforma
            </p>
          </div>
          <div class="border-t border-gray-200">
            <ul class="divide-y divide-gray-200">
              {#each stats.recent_clients as client}
                <li class="px-4 py-4">
                  <div class="flex items-center justify-between">
                    <div>
                      <p class="text-sm font-medium text-gray-900">{client.name}</p>
                      <p class="text-sm text-gray-500">{client.description}</p>
                    </div>
                    <div class="flex items-center space-x-4">
                      <div class="text-sm text-gray-500">
                        {client.users_count} usuarios
                      </div>
                      <div class="text-sm">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full {client.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}">
                          {client.status === 'active' ? 'Activo' : 'Pendiente'}
                        </span>
                      </div>
                    </div>
                  </div>
                </li>
              {/each}
            </ul>
          </div>
        </div>
      </div>
    {/if}
  </main>
</div> 