<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import Navbar from '$lib/Navbar.svelte';
  import { API_URL } from '$lib/config';
  import ChartLine from './ChartLine.svelte';
  import ChartPolar from './ChartPolar.svelte';
  import ChartBar from './ChartBar.svelte';
  import type { ChartData, ChartOptions } from 'chart.js';

  interface UserConfig {
    extension_enabled: boolean;
    blocked_domains: string[];
    allowed_domains: string[];
    user: {
      email: string;
      role: string;
    };
  }

  // Lista fija de categorías por defecto (nombres cortos para el radar)
  const DEFAULT_CATEGORIES = [
    "Azar",
    "Adultos",
    "Odio",
    "Drogas",
    "Estafas",
    "Ilegal",
    "Piratería",
    "Violencia"
  ];

  let userData: UserConfig | null = null;
  let loading = true;
  let error = '';

  // Estados para los datos reales
  let navStats: any = null;
  let alertStats: any = null;

  // Datos y opciones para la gráfica de tendencia de navegación
  let navTrendData: ChartData<'line'> = { labels: [], datasets: [] };
  let navTrendOptions: ChartOptions<'line'> = {
    responsive: true,
    plugins: {
      legend: { display: false },
      title: { display: false }
    },
    scales: {
      x: { title: { display: true, text: 'Fecha' } },
      y: { title: { display: true, text: 'Sitios visitados' }, beginAtZero: true }
    }
  };

  // Datos y opciones para la gráfica de tendencia de alertas
  let alertTrendData: ChartData<'line'> = { labels: [], datasets: [] };
  let alertTrendOptions: ChartOptions<'line'> = {
    responsive: true,
    plugins: {
      legend: { display: false },
      title: { display: false }
    },
    scales: {
      x: { title: { display: true, text: 'Fecha' } },
      y: { title: { display: true, text: 'Alertas' }, beginAtZero: true }
    }
  };

  // Datos y opciones para la gráfica de distribución por categoría
  let categoryData: ChartData<'radar'> = { labels: [], datasets: [] };
  let categoryOptions: ChartOptions<'radar'> = {
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
            size: 12,
            weight: 'bold'
          },
          color: '#4B5563'
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

  // Datos y opciones para la gráfica de distribución por hora
  let hourBarData: ChartData<'bar'> = { labels: [], datasets: [] };
  let hourBarOptions: ChartOptions<'bar'> = {
    responsive: true,
    plugins: {
      legend: { display: false },
      title: { display: false },
      tooltip: { enabled: true }
    },
    scales: {
      x: {
        title: { display: true, text: 'Hora' },
        grid: { display: false }
      },
      y: {
        title: { display: true, text: 'Visitas' },
        beginAtZero: true
      }
    }
  };

  // Lista de usuarios (id y correo)
  let users: { id: string; email: string }[] = [];

  async function loadUserData() {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        goto('/login');
        return;
      }

      const response = await fetch(`${API_URL}/api/config`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();
      if (data.success) {
        userData = data.data;
      } else {
        error = data.error || 'Error al cargar datos';
      }
    } catch (e) {
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }

  async function loadUsers() {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/users`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      const data = await res.json();
      if (data.success) {
        users = data.data.map((u: any) => ({ id: u.id, email: u.email }));
      }
    } catch {}
  }

  async function loadStats() {
    loading = true;
    error = '';
    const token = localStorage.getItem('token');
    if (!token) {
      goto('/login');
      return;
    }
    try {
      // Pedir ambos endpoints en paralelo
      const [navRes, alertRes] = await Promise.all([
        fetch(`${API_URL}/api/navigation_logs/stats`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_URL}/api/alerts/stats`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      ]);
      const navData = await navRes.json();
      const alertData = await alertRes.json();
      if (navData.success && alertData.success) {
        navStats = navData.data;
        alertStats = alertData.data;

        // Actualizar datos de la gráfica de tendencia de navegación
        if (navStats?.hourly_distribution) {
          navTrendData = {
            labels: navStats.hourly_distribution.map((h: any) => h.hour + ':00'),
            datasets: [
              {
                label: 'Sitios visitados',
                data: navStats.hourly_distribution.map((h: any) => h.count ?? 0),
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99,102,241,0.2)',
                tension: 0.3,
                fill: true
              }
            ]
          };
        }

        // Actualizar datos de la gráfica de tendencia de alertas
        if (alertStats?.alerts_trend) {
          alertTrendData = {
            labels: alertStats.alerts_trend.map((t: any) => t.date),
            datasets: [
              {
                label: 'Alertas',
                data: alertStats.alerts_trend.map((t: any) => t.count ?? 0),
                borderColor: '#f43f5e',
                backgroundColor: 'rgba(244,63,94,0.2)',
                tension: 0.3,
                fill: true
              }
            ]
          };
        }

        // --- RADAR: Cruzar categorías por defecto con navegación ---
        const navCatDict: Record<string, number> = {};
        (navStats.category_distribution || []).forEach((item: any) => {
          navCatDict[item.category] = item.count;
        });
        categoryData = {
          labels: DEFAULT_CATEGORIES,
          datasets: [{
            label: 'Visitas por Categoría',
            data: DEFAULT_CATEGORIES.map(cat => navCatDict[cat] || 0),
            backgroundColor: 'rgba(99,102,241,0.2)',
            borderColor: 'rgba(99,102,241,1)',
            borderWidth: 2,
            pointBackgroundColor: 'rgba(99,102,241,1)',
            pointBorderColor: '#fff',
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: 'rgba(99,102,241,1)',
            pointRadius: 4,
            pointHoverRadius: 6
          }]
        };

        // --- BARRAS: Distribución por hora ---
        const hours = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, '0'));
        const hourDict: Record<string, number> = {};
        (navStats.hourly_distribution || []).forEach((item: any) => {
          hourDict[item.hour] = item.count;
        });
        hourBarData = {
          labels: hours.map(h => h + ':00'),
          datasets: [{
            label: 'Visitas por hora',
            data: hours.map(h => hourDict[h] || 0),
            backgroundColor: 'rgba(99,102,241,0.7)',
            borderRadius: 4
          }]
        };
      } else {
        error = navData.error || alertData.error || 'Error al cargar estadísticas';
      }
    } catch (e) {
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }

  function handleLogout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    goto('/login');
  }

  onMount(async () => {
    // Importar Line solo en el cliente
    const userRaw = localStorage.getItem('user');
    if (!userRaw) {
      goto('/login');
      return;
    }
    loadUserData();
    loadUsers();
    loadStats();
  });
</script>

<Navbar active="dashboard" />

<div class="min-h-screen bg-gray-100">
  <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
    {#if loading}
      <div class="text-center text-gray-500 py-12">Cargando datos...</div>
    {:else if error}
      <div class="text-center text-red-500 py-12">{error}</div>
    {:else}
      <!-- Tarjetas resumen -->
      <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
        <div class="rounded-xl px-6 py-6 bg-blue-50 flex flex-col items-center">
          <span class="text-3xl font-extrabold text-indigo-600">{navStats?.total_sites ?? '-'}</span>
          <span class="text-base text-gray-700 mt-1">Sitios visitados</span>
        </div>
        <div class="rounded-xl px-6 py-6 bg-red-50 flex flex-col items-center">
          <span class="text-3xl font-extrabold text-red-600">{alertStats?.total_alerts ?? '-'}</span>
          <span class="text-base text-gray-700 mt-1">Total de alertas</span>
        </div>
        <div class="rounded-xl px-6 py-6 bg-yellow-50 flex flex-col items-center">
          <span class="text-3xl font-extrabold text-yellow-600">{navStats?.active_users ?? '-'}</span>
          <span class="text-base text-gray-700 mt-1">Usuarios activos hoy</span>
        </div>
        <div class="rounded-xl px-6 py-6 bg-pink-50 flex flex-col items-center">
          <span class="text-3xl font-extrabold text-pink-600">{alertStats?.alerts_by_severity?.high ?? '-'}</span>
          <span class="text-base text-gray-700 mt-1">Alertas de alto riesgo</span>
        </div>
        <div class="rounded-xl px-6 py-6 bg-green-50 flex flex-col items-center">
          <span class="text-3xl font-extrabold text-green-600">{navStats?.avg_session_time ?? '-'}</span>
          <span class="text-base text-gray-700 mt-1">Tiempo promedio sesión</span>
        </div>
        <div class="rounded-xl px-6 py-6 bg-purple-50 flex flex-col items-center">
          <span class="text-3xl font-extrabold text-purple-600">{navStats?.most_frequent_category ?? '-'}</span>
          <span class="text-base text-gray-700 mt-1">Categoría más frecuente</span>
        </div>
      </div>

      <!-- Gráficas y tendencias -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-2">Tendencia de Navegación</h3>
          {#if navTrendData.labels && navTrendData.labels.length > 0}
            <ChartLine data={navTrendData} options={navTrendOptions} />
          {:else}
            <div class="h-32 flex items-center justify-center text-gray-400">Sin datos</div>
          {/if}
        </div>
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-2">Tendencia de Alertas</h3>
          {#if alertTrendData.labels && alertTrendData.labels.length > 0}
            <ChartLine data={alertTrendData} options={alertTrendOptions} />
          {:else}
            <div class="h-32 flex items-center justify-center text-gray-400">Sin datos</div>
          {/if}
        </div>
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-2">Distribución por Categoría</h3>
          {#if categoryData.labels && categoryData.labels.length > 0}
            <div class="h-96">
              <ChartPolar data={categoryData} options={categoryOptions} />
            </div>
          {:else}
            <div class="h-32 flex items-center justify-center text-gray-400">Sin datos</div>
          {/if}
        </div>
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-2">Distribución por Hora</h3>
          {#if hourBarData.labels && hourBarData.labels.length > 0}
            <div class="h-80">
              <ChartBar data={hourBarData} options={hourBarOptions} />
            </div>
          {:else}
            <div class="h-32 flex items-center justify-center text-gray-400">Sin datos</div>
          {/if}
        </div>
      </div>

      <!-- Insights rápidos -->
      <div class="bg-white rounded-lg shadow p-6 mb-8">
        <h3 class="text-lg font-semibold mb-2">Insights rápidos</h3>
        <ul class="list-disc pl-6 text-gray-700 space-y-1">
          <li>Hoy hubo <span class="font-bold text-pink-600">{alertStats?.alerts_by_severity?.high ?? '-'}</span> alertas de alto riesgo.</li>
          <li>El usuario más activo fue: <span class="font-bold">{
            (() => {
              const userId = Object.keys(alertStats?.alerts_by_user ?? {})[0] ?? '-';
              const user = users.find(u => u.id === userId);
              return user ? user.email : userId;
            })()
          }</span></li>
          <li>La categoría más visitada fue: <span class="font-bold text-purple-600">{navStats?.most_frequent_category ?? '-'}</span></li>
          <li>La categoría más bloqueada fue: <span class="font-bold text-red-600">{Object.keys(alertStats?.alerts_by_category ?? {})[0] ?? '-'}</span></li>
        </ul>
      </div>
    {/if}
  </main>
</div> 