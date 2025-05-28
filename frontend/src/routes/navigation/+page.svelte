<script lang="ts">
  import Navbar from '$lib/Navbar.svelte';
  import { onMount } from 'svelte';
  import { API_URL } from '$lib/config';
  import { writable } from 'svelte/store';
  import ChartBar from '../dashboard/ChartBar.svelte';
  type User = { id: string; email: string };
  type Log = {
    id: string;
    user_id: string;
    tenant_id: string;
    domain: string;
    url: string;
    timestamp: string;
    action: string;
  };
  let users: User[] = [];
  let userId = '';
  let domain = '';
  let url = '';
  let dateFrom = '';
  let dateTo = '';
  let action = 'all';
  let logs: Log[] = [];
  let loading = false;
  let error = '';
  let page = 1;
  let pageSize = 10;
  let total = 0;
  let domainSuggestions: string[] = [];
  let urlSuggestions: string[] = [];
  let showDomainSuggestions = false;
  let showUrlSuggestions = false;
  let blocking = false;
  let blockError = '';
  let blockSuccess = '';
  let activeTab = (typeof localStorage !== 'undefined' && localStorage.getItem('navigation_active_tab')) || 'general';

  // Estadísticas generales
  interface Stats {
    total_sites: number;
    most_frequent_category: string;
    active_users: number;
    avg_session_time: number;
    category_distribution: { category: string; count: number }[];
    user_distribution: { user: string; count: number }[];
    hourly_distribution: { hour: number; count: number }[];
  }

  let stats: Stats = {
    total_sites: 0,
    most_frequent_category: '',
    active_users: 0,
    avg_session_time: 0,
    category_distribution: [],
    user_distribution: [],
    hourly_distribution: []
  };
  let loadingStats = false;
  let errorStats = '';

  // Datos para los gráficos de barras
  let categoryBarData: any = { labels: [], datasets: [] };
  let userBarData: any = { labels: [], datasets: [] };
  let hourBarData: any = { labels: [], datasets: [] };
  let barOptions: any = {
    responsive: true,
    plugins: {
      legend: { display: false },
      title: { display: false },
      tooltip: { enabled: true }
    },
    scales: {
      x: {
        title: { display: true, text: '' },
        grid: { display: false }
      },
      y: {
        title: { display: true, text: 'Visitas' },
        beginAtZero: true
      }
    }
  };

  // Datos para el gráfico de barras apiladas NavegaVisor
  let stackedBarData: any = { labels: [], datasets: [] };
  let stackedBarOptions: any = {
    responsive: true,
    plugins: {
      legend: { display: true, position: 'top' },
      title: { display: false },
      tooltip: { enabled: true }
    },
    scales: {
      x: {
        title: { display: true, text: 'Hora' },
        stacked: true,
        grid: { display: false }
      },
      y: {
        title: { display: true, text: 'Visitas' },
        beginAtZero: true,
        stacked: true
      }
    }
  };

  // Datos para la tabla y gráfico de sesiones
  let sessionTable: any[] = [];
  let sessionBarData: any = { labels: [], datasets: [] };
  let sessionBarOptions: any = {
    responsive: true,
    plugins: {
      legend: { display: false },
      title: { display: false },
      tooltip: { enabled: true }
    },
    scales: {
      x: {
        title: { display: true, text: 'Usuario' },
        grid: { display: false }
      },
      y: {
        title: { display: true, text: 'Duración total (min)' },
        beginAtZero: true
      }
    }
  };

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

  async function loadLogs() {
    loading = true;
    error = '';
    try {
      const params = new URLSearchParams();
      if (userId) params.append('user_id', userId);
      if (domain) params.append('domain', domain);
      if (url) params.append('url', url);
      if (dateFrom) params.append('date_from', dateFrom);
      if (dateTo) params.append('date_to', dateTo);
      if (action && action !== 'all') params.append('action', action);
      params.append('page', page.toString());
      params.append('page_size', pageSize.toString());

      const res = await fetch(`${API_URL}/api/navigation_logs?${params.toString()}`, {
        headers: { 
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });
      const data = await res.json();
      if (data.success) {
        logs = data.data;
        total = data.total;
      } else {
        error = data.error || 'Error al cargar historial';
        logs = [];
        total = 0;
      }
    } catch (e) {
      error = 'Error de conexión';
      logs = [];
      total = 0;
    } finally {
      loading = false;
    }
  }

  function filtrar() {
    page = 1;
    loadLogs();
  }

  function nextPage() {
    if (page * pageSize < total) {
      page += 1;
      loadLogs();
    }
  }

  function prevPage() {
    if (page > 1) {
      page -= 1;
      loadLogs();
    }
  }

  async function fetchDomainSuggestions(query: string) {
    if (!query) {
      domainSuggestions = [];
      return;
    }
    try {
      const res = await fetch(`${API_URL}/api/navigation_logs/domains?q=${query}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      const data = await res.json();
      if (data.success) {
        domainSuggestions = data.data;
      }
    } catch {
      domainSuggestions = [];
    }
  }

  async function fetchUrlSuggestions(query: string) {
    if (!query) {
      urlSuggestions = [];
      return;
    }
    try {
      const res = await fetch(`${API_URL}/api/navigation_logs/urls?q=${query}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      const data = await res.json();
      if (data.success) {
        urlSuggestions = data.data;
      }
    } catch {
      urlSuggestions = [];
    }
  }

  async function blockDomain(domain: string) {
    if (!confirm(`¿Estás seguro de que deseas bloquear el dominio ${domain}?`)) {
      return;
    }
    
    blocking = true;
    blockError = '';
    blockSuccess = '';
    
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        blockError = 'No hay sesión activa';
        return;
      }

      const res = await fetch(`${API_URL}/api/navigation_logs/block`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ domain })
      });
      
      const data = await res.json();
      if (data.success) {
        blockSuccess = data.message;
        // Recargar los logs para reflejar el cambio
        await loadLogs();
      } else {
        blockError = data.error || 'Error al bloquear el dominio';
      }
    } catch (e: any) {
      blockError = e.message || 'Error al bloquear el dominio';
    } finally {
      blocking = false;
      // Limpiar mensajes después de 3 segundos
      setTimeout(() => {
        blockError = '';
        blockSuccess = '';
      }, 3000);
    }
  }

  async function loadStats() {
    loadingStats = true;
    errorStats = '';
    try {
      const params = new URLSearchParams();
      if (dateFrom) params.append('date_from', dateFrom);
      if (dateTo) params.append('date_to', dateTo);
      
      const res = await fetch(`${API_URL}/api/navigation_logs/stats?${params.toString()}`, {
        headers: { 
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });
      const data = await res.json();
      if (data.success) {
        stats = {
          total_sites: data.data.total_sites,
          most_frequent_category: data.data.most_frequent_category || 'Sin datos',
          active_users: data.data.active_users,
          avg_session_time: data.data.avg_session_time,
          category_distribution: data.data.category_distribution,
          user_distribution: data.data.user_distribution.map((item: any) => ({
            user: users.find(u => u.id === item.user_id)?.email || item.user_id,
            count: item.count
          })),
          hourly_distribution: data.data.hourly_distribution
        };
      } else {
        errorStats = data.error || 'Error al cargar estadísticas';
      }
    } catch (e) {
      errorStats = 'Error de conexión';
    } finally {
      loadingStats = false;
    }
  }

  // Cargar estadísticas cuando cambien las fechas
  $: if (dateFrom || dateTo) {
    loadStats();
  }

  // Eventos para los filtros
  $: if (userId || domain || url || dateFrom || dateTo || action !== 'all') {
    filtrar();
  }

  // Cerrar sugerencias al hacer click fuera
  function handleClickOutside(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (!target.closest('.domain-suggestions') && !target.closest('.url-suggestions')) {
      showDomainSuggestions = false;
      showUrlSuggestions = false;
    }
  }

  onMount(() => {
    loadUsers();
    loadLogs();
    loadStats();

    // Cargar datos para la pestaña activa
    if (activeTab === 'general') {
      loadStats();
    } else if (activeTab === 'historial') {
      loadLogs();
    } else if (activeTab === 'navegavisor') {
      // No hay función específica, los datos se procesan desde logs
      loadLogs();
    } else if (activeTab === 'sesio') {
      // No hay función específica, los datos se procesan desde logs
      loadLogs();
    }

    document.addEventListener('click', handleClickOutside);
    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  });

  $: if (stats) {
    // Sitios por Categoría
    categoryBarData = {
      labels: stats.category_distribution.map((item) => item.category.length > 14 ? item.category.slice(0, 14) + '…' : item.category),
      datasets: [{
        label: 'Sitios por Categoría',
        data: stats.category_distribution.map((item) => item.count),
        backgroundColor: 'rgba(99,102,241,0.7)',
        borderRadius: 4
      }]
    };
    // Distribución de Usuarios
    userBarData = {
      labels: stats.user_distribution.map((item) => item.user.length > 18 ? item.user.slice(0, 18) + '…' : item.user),
      datasets: [{
        label: 'Visitas por Usuario',
        data: stats.user_distribution.map((item) => item.count),
        backgroundColor: 'rgba(16,185,129,0.7)',
        borderRadius: 4
      }]
    };
    // Actividad por Hora
    const hours = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, '0'));
    const hourDict: Record<string, number> = {};
    (stats.hourly_distribution || []).forEach((item: any) => {
      hourDict[item.hour] = item.count;
    });
    hourBarData = {
      labels: hours.map(h => h + ':00'),
      datasets: [{
        label: 'Visitas por hora',
        data: hours.map(h => hourDict[h] || 0),
        backgroundColor: 'rgba(59,130,246,0.7)',
        borderRadius: 4
      }]
    };
  }

  $: if (logs && logs.length > 0) {
    // Procesar datos para barras apiladas (top 10 dominios)
    const domainCounts: Record<string, number[]> = {};
    logs.forEach((log: any) => {
      const domain = log.domain;
      const hour = new Date(log.timestamp).getHours();
      if (!domainCounts[domain]) domainCounts[domain] = Array(24).fill(0);
      domainCounts[domain][hour]++;
    });
    const topDomains = Object.entries(domainCounts)
      .sort((a, b) => b[1].reduce((x, y) => x + y, 0) - a[1].reduce((x, y) => x + y, 0))
      .slice(0, 10)
      .map(([domain]) => domain);
    const hours = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, '0') + ':00');
    const colors = [
      '#6366f1', '#f43f5e', '#16a34a', '#f59e42', '#8b5cf6',
      '#3b82f6', '#ec4899', '#0ea5e9', '#eab308', '#f87171'
    ];
    stackedBarData = {
      labels: hours,
      datasets: topDomains.map((domain, idx) => ({
        label: domain.length > 18 ? domain.slice(0, 18) + '…' : domain,
        data: domainCounts[domain],
        backgroundColor: colors[idx % colors.length],
        borderRadius: 3
      }))
    };

    // Procesar sesiones por usuario (timeout 30 min)
    const SESSION_TIMEOUT = 30 * 60; // 30 minutos en segundos
    const userSessions: Record<string, { start: Date, end: Date, count: number }[]> = {};
    const logsByUser: Record<string, any[]> = {};
    logs.forEach(log => {
      if (!logsByUser[log.user_id]) logsByUser[log.user_id] = [];
      logsByUser[log.user_id].push(log);
    });
    Object.entries(logsByUser).forEach(([userId, userLogs]) => {
      // Ordenar logs por timestamp
      userLogs.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
      let sessions: { start: Date, end: Date, count: number }[] = [];
      let sessionStart = new Date(userLogs[0].timestamp);
      let sessionEnd = sessionStart;
      let count = 1;
      for (let i = 1; i < userLogs.length; i++) {
        const curr = new Date(userLogs[i].timestamp);
        const prev = new Date(userLogs[i - 1].timestamp);
        if ((curr.getTime() - prev.getTime()) / 1000 > SESSION_TIMEOUT) {
          sessions.push({ start: sessionStart, end: sessionEnd, count });
          sessionStart = curr;
          count = 1;
        } else {
          count++;
        }
        sessionEnd = curr;
      }
      sessions.push({ start: sessionStart, end: sessionEnd, count });
      userSessions[userId] = sessions;
    });
    // Tabla de sesiones
    sessionTable = [];
    Object.entries(userSessions).forEach(([userId, sessions]) => {
      sessions.forEach(s => {
        sessionTable.push({
          user: users.find(u => u.id === userId)?.email || userId,
          start: s.start,
          end: s.end,
          duration: Math.round((s.end.getTime() - s.start.getTime()) / 60000),
          count: s.count
        });
      });
    });
    // Gráfico de barras: duración total por usuario
    const userDurations: Record<string, number> = {};
    sessionTable.forEach(s => {
      if (!userDurations[s.user]) userDurations[s.user] = 0;
      userDurations[s.user] += s.duration;
    });
    sessionBarData = {
      labels: Object.keys(userDurations),
      datasets: [{
        label: 'Duración total de sesiones (min)',
        data: Object.values(userDurations),
        backgroundColor: 'rgba(99,102,241,0.7)',
        borderRadius: 4
      }]
    };
  }

  function setActiveTab(tab: string) {
    activeTab = tab;
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('navigation_active_tab', tab);
    }
  }
</script>

<Navbar active="navigation" />

<div class="min-h-screen bg-gray-100">
  <div class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
    <!-- Titulo y Descripcion -->
    <div>
      <h1 class="text-2xl font-bold mb-4">Centro de Navegación</h1>
      <div class="mb-6">
        <nav class="-mb-px flex space-x-8 border-b border-gray-200">
          <button class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'general' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}" on:click={() => setActiveTab('general')}>General</button>
          <button class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'historial' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}" on:click={() => setActiveTab('historial')}>Historial</button>
          <button class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'navegavisor' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}" on:click={() => setActiveTab('navegavisor')}>NavegaVisor</button>
          <button class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'sesio' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}" on:click={() => setActiveTab('sesio')}>SesioTrack</button>
        </nav>
      </div>
    </div>

    {#if activeTab === 'general'}
      <h2 class="text-xl font-semibold mb-2">Visión General de la Actividad</h2>
      {#if loadingStats}
        <div class="text-center py-8">
          <p class="text-gray-500">Cargando estadísticas...</p>
        </div>
      {:else if errorStats}
        <div class="text-center py-8 text-red-500">
          <p>{errorStats}</p>
        </div>
      {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div class="bg-indigo-50 p-4 rounded shadow flex flex-col items-center">
            <span class="text-3xl font-bold text-indigo-700">{stats.total_sites}</span>
            <span class="text-gray-700">Total de sitios visitados</span>
          </div>
          <div class="bg-green-50 p-4 rounded shadow flex flex-col items-center">
            <span class="text-3xl font-bold text-green-700">{stats.most_frequent_category}</span>
            <span class="text-gray-700">Categoría más frecuente</span>
          </div>
          <div class="bg-yellow-50 p-4 rounded shadow flex flex-col items-center">
            <span class="text-3xl font-bold text-yellow-700">{stats.active_users}</span>
            <span class="text-gray-700">Usuarios activos hoy</span>
          </div>
          <div class="bg-blue-50 p-4 rounded shadow flex flex-col items-center">
            <span class="text-3xl font-bold text-blue-700">{stats.avg_session_time} min</span>
            <span class="text-gray-700">Tiempo promedio por sesión</span>
          </div>
        </div>

        <!-- Gráficos -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="bg-white p-4 rounded shadow">
            <h3 class="font-semibold mb-4">Sitios por Categoría</h3>
            <div class="h-80">
              <ChartBar data={categoryBarData} options={{...barOptions, scales: { ...barOptions.scales, x: { ...barOptions.scales.x, title: { display: true, text: 'Categoría' }}}}} />
            </div>
          </div>
          <div class="bg-white p-4 rounded shadow">
            <h3 class="font-semibold mb-4">Distribución de Usuarios</h3>
            <div class="h-80">
              <ChartBar data={userBarData} options={{...barOptions, scales: { ...barOptions.scales, x: { ...barOptions.scales.x, title: { display: true, text: 'Usuario' }}}}} />
            </div>
          </div>
        </div>
        <div class="mt-6 bg-white p-4 rounded shadow">
          <h3 class="font-semibold mb-4">Actividad por Hora</h3>
          <div class="h-80">
            <ChartBar data={hourBarData} options={{...barOptions, scales: { ...barOptions.scales, x: { ...barOptions.scales.x, title: { display: true, text: 'Hora' }}}}} />
          </div>
        </div>
      {/if}
    {:else if activeTab === 'historial'}
      <h2 class="text-xl font-semibold mb-2">Historial Completo de Navegación</h2>
      <!-- Filtros -->
      <div class="flex flex-wrap md:flex-nowrap gap-4 mb-6 items-end">
        <div class="min-w-[140px] flex-1">
          <label class="block text-xs font-medium text-gray-700 mb-1">Usuario</label>
          <select 
            bind:value={userId} 
            class="border rounded px-3 py-2 w-full"
            on:change={filtrar}
          >
            <option value="">Todos</option>
            {#each users as user}
              <option value={user.id}>{user.email}</option>
            {/each}
          </select>
        </div>
        <div class="min-w-[160px] flex-1">
          <label class="block text-xs font-medium text-gray-700 mb-1">Dominio</label>
          <div class="relative domain-suggestions">
            <input 
              type="text" 
              bind:value={domain} 
              on:input={(e) => fetchDomainSuggestions((e.target as HTMLInputElement).value)}
              on:focus={() => showDomainSuggestions = true}
              on:blur={() => setTimeout(() => showDomainSuggestions = false, 200)}
              class="border rounded px-3 py-2 w-full"
              placeholder="ejemplo.com"
            />
            {#if showDomainSuggestions && domainSuggestions.length > 0}
              <div class="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg">
                {#each domainSuggestions as suggestion}
                  <button 
                    class="w-full text-left px-3 py-2 hover:bg-gray-100 text-sm"
                    on:click={() => { 
                      domain = suggestion; 
                      showDomainSuggestions = false;
                      filtrar();
                    }}
                  >
                    {suggestion}
                  </button>
                {/each}
              </div>
            {/if}
          </div>
        </div>
        <div class="min-w-[180px] flex-1">
          <label class="block text-xs font-medium text-gray-700 mb-1">URL</label>
          <div class="relative url-suggestions">
            <input 
              type="text" 
              bind:value={url} 
              on:input={(e) => fetchUrlSuggestions((e.target as HTMLInputElement).value)}
              on:focus={() => showUrlSuggestions = true}
              on:blur={() => setTimeout(() => showUrlSuggestions = false, 200)}
              class="border rounded px-3 py-2 w-full"
              placeholder="https://ejemplo.com/ruta"
            />
            {#if showUrlSuggestions && urlSuggestions.length > 0}
              <div class="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg">
                {#each urlSuggestions as suggestion}
                  <button 
                    class="w-full text-left px-3 py-2 hover:bg-gray-100 text-sm"
                    on:click={() => { 
                      url = suggestion; 
                      showUrlSuggestions = false;
                      filtrar();
                    }}
                  >
                    {suggestion}
                  </button>
                {/each}
              </div>
            {/if}
          </div>
        </div>
        <div class="min-w-[120px] flex-1">
          <label class="block text-xs font-medium text-gray-700 mb-1">Desde</label>
          <input 
            type="date" 
            bind:value={dateFrom} 
            class="border rounded px-3 py-2 w-full"
            on:change={filtrar}
          />
        </div>
        <div class="min-w-[120px] flex-1">
          <label class="block text-xs font-medium text-gray-700 mb-1">Hasta</label>
          <input 
            type="date" 
            bind:value={dateTo} 
            class="border rounded px-3 py-2 w-full"
            on:change={filtrar}
          />
        </div>
        <div class="min-w-[120px] flex-1">
          <label class="block text-xs font-medium text-gray-700 mb-1">Acción</label>
          <select 
            bind:value={action} 
            class="border rounded px-3 py-2 w-full"
            on:change={filtrar}
          >
            <option value="all">Todas</option>
            <option value="bloqueado">Bloqueado</option>
            <option value="permitido">Permitido</option>
          </select>
        </div>
        <div class="flex flex-row gap-2 md:ml-2 mt-2 md:mt-0 min-w-[120px]">
          <button class="px-4 py-2 rounded bg-indigo-600 text-white font-semibold w-full md:w-auto" on:click={filtrar}>Filtrar</button>
        </div>
      </div>
      <!-- Tabla -->
      <div class="relative overflow-x-auto shadow-md sm:rounded-lg">
        <div class="w-full overflow-x-auto">
          <table class="w-full text-sm text-left text-gray-500">
            <thead class="text-xs text-gray-700 uppercase bg-gray-50">
              <tr>
                <th scope="col" class="px-4 py-3 whitespace-nowrap min-w-[150px]">Usuario</th>
                <th scope="col" class="px-4 py-3 whitespace-nowrap min-w-[120px]">Dominio</th>
                <th scope="col" class="px-4 py-3 whitespace-nowrap min-w-[200px]">URL</th>
                <th scope="col" class="px-4 py-3 whitespace-nowrap min-w-[100px]">Acción</th>
                <th scope="col" class="px-4 py-3 whitespace-nowrap min-w-[150px]">Fecha/Hora</th>
              </tr>
            </thead>
            <tbody>
              {#if loading}
                <tr class="bg-white border-b">
                  <td colspan="5" class="px-4 py-4 text-center text-gray-400">Cargando registros...</td>
                </tr>
              {:else if logs.length === 0}
                <tr class="bg-white border-b">
                  <td colspan="5" class="px-4 py-4 text-center text-gray-400">No hay registros para mostrar.</td>
                </tr>
              {:else}
                {#each logs as log}
                  <tr class="bg-white border-b hover:bg-gray-50">
                    <td class="px-4 py-4 whitespace-nowrap">{users.find(u => u.id === log.user_id)?.email || log.user_id}</td>
                    <td class="px-4 py-4 whitespace-nowrap max-w-xs break-all">
                      <div class="truncate" title={log.domain}>{log.domain}</div>
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap truncate max-w-[200px]" title={log.url}>{log.url}</td>
                    <td class="px-4 py-4 whitespace-nowrap">
                      <span class="px-2 py-1 text-xs font-semibold rounded-full {log.action === 'bloqueado' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}">
                        {log.action === 'bloqueado' ? 'Bloqueado' : 'Permitido'}
                      </span>
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap">{new Date(log.timestamp).toLocaleString()}</td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      </div>
      <!-- Paginación -->
      <div class="flex justify-end mt-4 gap-2">
        <button class="px-3 py-1 rounded bg-gray-200 text-gray-700 font-semibold" on:click={prevPage} disabled={page === 1}>Anterior</button>
        <span class="px-3 py-1">Página {page} de {Math.ceil(total/pageSize) || 1}</span>
        <button class="px-3 py-1 rounded bg-gray-200 text-gray-700 font-semibold" on:click={nextPage} disabled={page * pageSize >= total}>Siguiente</button>
      </div>
    {:else if activeTab === 'navegavisor'}
      <h2 class="text-xl font-semibold mb-2">Mapa de Navegación Corporativa</h2>
      <div class="mb-4">Actividad por hora y dominio (barras apiladas):</div>
      <div class="h-96">
        <ChartBar data={stackedBarData} options={stackedBarOptions} />
      </div>
    {:else if activeTab === 'sesio'}
      <h2 class="text-xl font-semibold mb-2">Análisis de Sesiones</h2>
      <div class="mb-4">Tabla de sesiones por usuario:</div>
      <div class="overflow-x-auto mb-8">
        <table class="w-full text-sm text-left text-gray-500">
          <thead class="text-xs text-gray-700 uppercase bg-gray-50">
            <tr>
              <th class="px-4 py-3">Usuario</th>
              <th class="px-4 py-3">Inicio</th>
              <th class="px-4 py-3">Fin</th>
              <th class="px-4 py-3">Duración (min)</th>
              <th class="px-4 py-3">Sitios visitados</th>
            </tr>
          </thead>
          <tbody>
            {#if sessionTable.length === 0}
              <tr><td colspan="5" class="text-center py-4 text-gray-400">Sin sesiones detectadas.</td></tr>
            {:else}
              {#each sessionTable as s}
                <tr>
                  <td class="px-4 py-2">{s.user}</td>
                  <td class="px-4 py-2">{s.start.toLocaleString()}</td>
                  <td class="px-4 py-2">{s.end.toLocaleString()}</td>
                  <td class="px-4 py-2">{s.duration}</td>
                  <td class="px-4 py-2">{s.count}</td>
                </tr>
              {/each}
            {/if}
          </tbody>
        </table>
      </div>
      <div class="mb-4">Duración total de sesiones por usuario:</div>
      <div class="h-96">
        <ChartBar data={sessionBarData} options={sessionBarOptions} />
      </div>
    {/if}

    {#if blockError}
      <div class="fixed bottom-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
        {blockError}
      </div>
    {/if}
    
    {#if blockSuccess}
      <div class="fixed bottom-4 right-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
        {blockSuccess}
      </div>
    {/if}
  </div>
</div> 