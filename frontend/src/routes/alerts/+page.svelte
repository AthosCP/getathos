<script lang="ts">
  import Navbar from '$lib/Navbar.svelte';
  import { onMount } from 'svelte';
  import { auth } from '$lib/auth';
  import { goto } from '$app/navigation';
  import { API_URL } from '$lib/config';
  import ChartBar from '../dashboard/ChartBar.svelte';
  import ChartLine from '../dashboard/ChartLine.svelte';

  let alerts: any[] = [];
  let loading = true;
  let error = '';

  // Estado de las pestañas
  type Tab = 'centro' | 'riesgo' | 'bloqueos' | 'comportamiento' | 'geo';
  let activeTab: Tab = (typeof localStorage !== 'undefined' && localStorage.getItem('alerts_active_tab') as Tab) || 'centro';

  // Interfaz para datos de riesgo
  interface RiesgoData {
    usuario: string;
    puntaje: number;
    sitio: string;
    hora: string;
    categoria: string;
    alerta: boolean;
  }

  // Estado para datos de riesgo
  let riesgoData: RiesgoData[] = [];
  let loadingRiesgo = false;
  let currentPageRiesgo = 1;
  let totalPagesRiesgo = 1;
  let pageSizeRiesgo = 20;

  // Categorías dinámicas
  let categorias: string[] = [];

  // Estado para estadísticas de alertas
  let alertStats = {
    total_alerts: 0,
    alerts_by_category: {},
    alerts_by_user: {},
    alerts_by_hour: {},
    alerts_by_severity: { high: 0, medium: 0, low: 0 },
    alerts_trend: [] as Array<{date: string, count: number}>
  };
  let loadingStats = false;

  // Tarjetas de categorías
  let tarjetas: { category: string, count: number }[] = [];

  // Filtros globales
  let users: any[] = [];
  let selectedUser = '';
  let selectedCategoria = '';
  let dateFrom = '';
  let dateTo = '';

  // Registros reales
  let registros: any[] = [];
  let loadingRegistros = false;

  // Estado para datos de comportamiento anómalo (ComportGuard)
  interface ComportamientoData {
    usuario: string;
    tipo: string;
    detalle: string;
    hora: string;
    sospechoso: boolean;
  }
  let comportamientoData: ComportamientoData[] = [];
  let loadingComportamiento = false;
  let errorComportamiento = '';
  let currentPageComport = 1;
  let totalPagesComport = 1;
  let pageSizeComport = 20;

  // Estado para GeoAlerta
  interface GeoData {
    usuario: string;
    ip: string;
    ciudad: string;
    pais: string;
    hora: string;
    alerta: boolean;
  }
  let geoData: GeoData[] = [];
  let loadingGeo = false;
  let errorGeo = '';
  let currentPageGeo = 1;
  let totalPagesGeo = 1;
  let pageSizeGeo = 20;
  // Data loaded flags
  let centroDataLoaded = false;
  let riesgoDataLoaded = false;
  let bloqNetDataLoaded = false;
  let comportamientoDataLoaded = false;
  let geoDataLoaded = false;

  let selectedUserGeo = '';
  let selectedUbicacionGeo = '';
  let selectedEstadoGeo = '';
  let dateFromGeo = '';
  let dateToGeo = '';
  const estadosGeo = [
    { value: '', label: 'Todos' },
    { value: 'habitual', label: 'IP Habitual' },
    { value: 'no_habitual', label: 'IP No Habitual' }
  ];

  // Estado para mostrar el tooltip de riesgo
  let showRiskTooltip = false;

  // Estado para mostrar el modal de riesgo
  let showRiskModal = false;

  // Filtros para ComportGuard
  let selectedUserComport = '';
  let selectedTipoComport = '';
  let dateFromComport = '';
  let dateToComport = '';
  const tiposComport = ['Cambio de horario', 'Sitio inusual', 'Patrón irregular'];

  // Filtros para RiesgoAct
  let selectedUserRiesgo = '';
  let selectedCategoriaRiesgo = '';
  let dateFromRiesgo = '';
  let dateToRiesgo = '';
  let alertaRiesgo = '';
  const alertaOptions = [
    { value: '', label: 'Todos' },
    { value: 'si', label: 'Solo alerta' },
    { value: 'no', label: 'Solo sin alerta' }
  ];

  // Filtros para BloqNet
  let selectedUserBloq = '';
  let selectedCategoriaBloq = '';
  let selectedEstadoBloq = '';
  let dateFromBloq = '';
  let dateToBloq = '';
  const estadoBloqOptions = [
    { value: '', label: 'Todos' },
    { value: 'bloqueado', label: 'Bloqueado' },
    { value: 'permitido', label: 'Permitido' }
  ];

  // Datos y opciones para los gráficos
  let categoryBarData: any = { labels: [], datasets: [] };
  let hourBarData: any = { labels: [], datasets: [] };
  let trendLineData: any = { labels: [], datasets: [] };
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
        title: { display: true, text: 'Alertas' },
        beginAtZero: true
      }
    }
  };
  let lineOptions: any = {
    responsive: true,
    plugins: {
      legend: { display: false },
      title: { display: false },
      tooltip: { enabled: true }
    },
    scales: {
      x: { title: { display: true, text: 'Fecha' } },
      y: { title: { display: true, text: 'Alertas' }, beginAtZero: true }
    }
  };

  $: if (alertStats) {
    // Distribución por categoría
    categoryBarData = {
      labels: Object.keys(alertStats.alerts_by_category).map(c => mostrarCategoria(c)),
      datasets: [{
        label: 'Alertas por Categoría',
        data: Object.values(alertStats.alerts_by_category),
        backgroundColor: 'rgba(244,63,94,0.7)',
        borderRadius: 4
      }]
    };
    // Distribución por hora
    const hours = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, '0'));
    const hourDict: Record<string, number> = alertStats.alerts_by_hour || {};
    hourBarData = {
      labels: hours.map(h => h + ':00'),
      datasets: [{
        label: 'Alertas por hora',
        data: hours.map(h => hourDict[h] || 0),
        backgroundColor: 'rgba(99,102,241,0.7)',
        borderRadius: 4
      }]
    };
    // Tendencia de alertas
    trendLineData = {
      labels: (alertStats.alerts_trend || []).map((t: any) => t.date),
      datasets: [{
        label: 'Alertas',
        data: (alertStats.alerts_trend || []).map((t: any) => t.count ?? 0),
        borderColor: '#f43f5e',
        backgroundColor: 'rgba(244,63,94,0.2)',
        tension: 0.3,
        fill: true
      }]
    };
  }

  async function loadCategorias() {
    try {
      const res = await fetch(`${API_URL}/api/prohibited_sites`);
      const data = await res.json();
      if (data.success) {
        categorias = Object.keys(data.data);
      } else {
        categorias = [];
      }
    } catch {
      categorias = [];
    }
  }

  async function loadUsers() {
    try {
      const res = await fetch(`${API_URL}/api/users`, {
        headers: { 'Authorization': `Bearer ${auth.token}` }
      });
      const data = await res.json();
      if (data.success) {
        users = data.data;
      }
    } catch {}
  }

  async function loadRegistros() {
    loadingRegistros = true;
    let params = new URLSearchParams();
    // Por defecto mostrar solo bloqueos si no hay estado seleccionado
    params.append('action', selectedEstadoBloq || 'bloqueado');
    if (selectedUserBloq) params.append('user_id', selectedUserBloq);
    if (selectedCategoriaBloq) params.append('category', selectedCategoriaBloq);
    if (dateFromBloq) params.append('date_from', dateFromBloq);
    if (dateToBloq) params.append('date_to', dateToBloq);
    try {
      const res = await fetch(`${API_URL}/api/navigation_logs?${params.toString()}`, {
        headers: { 'Authorization': `Bearer ${auth.token}` }
      });
      const data = await res.json();
      if (data.success) {
        registros = data.data
          .filter((reg: any) => reg.domain && reg.domain.trim() !== '')
          .map((reg: any) => {
            let policyInfo = reg.policy_info;
            if (typeof policyInfo === 'string') {
              try { policyInfo = JSON.parse(policyInfo); } catch { policyInfo = { category: 'sin categoría', block_reason: 'Sin motivo especificado' }; }
            }
            return {
              ...reg,
              policy_info: policyInfo || { category: 'sin categoría', block_reason: 'Sin motivo especificado' }
            };
          });
      } else {
        registros = [];
      }
    } catch (error) {
      console.error('Error cargando registros:', error);
      registros = [];
    } finally {
      loadingRegistros = false;
    }
  }

  async function loadTarjetas() {
    let params = new URLSearchParams();
    if (selectedUserBloq) params.append('user_id', selectedUserBloq);
    if (selectedCategoriaBloq) params.append('category', selectedCategoriaBloq);
    if (dateFromBloq) params.append('date_from', dateFromBloq);
    if (dateToBloq) params.append('date_to', dateToBloq);
    params.append('action', selectedEstadoBloq || 'bloqueado');
    try {
      const res = await fetch(`${API_URL}/api/navigation_logs?${params.toString()}`, {
        headers: { 'Authorization': `Bearer ${auth.token}` }
      });
      const data = await res.json();
      if (data.success) {
        // Agrupar por categoría y contar
        const categoryCounts = data.data.reduce((acc: any, reg: any) => {
          let policyInfo = reg.policy_info;
          if (typeof policyInfo === 'string') {
            try { policyInfo = JSON.parse(policyInfo); } catch { policyInfo = { category: 'sin categoría' }; }
          }
          const category = policyInfo?.category || 'sin categoría';
          acc[category] = (acc[category] || 0) + 1;
          return acc;
        }, {});
        // Convertir a formato de tarjetas
        tarjetas = categorias.map(cat => ({
          category: cat,
          count: categoryCounts[cat] || 0
        }));
      } else {
        tarjetas = categorias.map(cat => ({ category: cat, count: 0 }));
      }
    } catch {
      tarjetas = categorias.map(cat => ({ category: cat, count: 0 }));
    }
  }

  async function loadAlertStats() {
    loadingStats = true;
    let params = new URLSearchParams();
    if (selectedUser) params.append('user_id', selectedUser);
    if (selectedCategoria) params.append('category', selectedCategoria);
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    try {
      const res = await fetch(`${API_URL}/api/alerts/stats?${params.toString()}`, {
        headers: { 'Authorization': `Bearer ${auth.token}` }
      });
      const data = await res.json();
      if (data.success) {
        alertStats = data.data;
      }
    } catch (err) {
      console.error('Error cargando estadísticas:', err);
    } finally {
      loadingStats = false;
    }
  }

  async function loadRiesgoData() {
    loadingRiesgo = true;
    let params = new URLSearchParams();
    if (selectedUserRiesgo) params.append('user_id', selectedUserRiesgo);
    if (selectedCategoriaRiesgo) params.append('category', selectedCategoriaRiesgo);
    if (dateFromRiesgo) params.append('date_from', dateFromRiesgo);
    if (dateToRiesgo) params.append('date_to', dateToRiesgo);
    params.append('page', currentPageRiesgo.toString());
    params.append('page_size', pageSizeRiesgo.toString());
    
    try {
      const res = await fetch(`${API_URL}/api/navigation_logs/riesgo?${params.toString()}`, {
        headers: { 'Authorization': `Bearer ${auth.token}` }
      });
      const data = await res.json();
      if (data.success) {
        let filtrados = data.data;
        if (alertaRiesgo === 'si') filtrados = filtrados.filter(i => (i.risk_score || 0) > 80);
        if (alertaRiesgo === 'no') filtrados = filtrados.filter(i => (i.risk_score || 0) <= 80);
        riesgoData = filtrados.map((item) => ({
          usuario: users.find(u => u.id === item.user_id)?.email || item.user_id,
          puntaje: item.risk_score || 0,
          sitio: item.domain || '-',
          hora: new Date(item.timestamp).toLocaleString(),
          categoria: typeof item.policy_info === 'object' && item.policy_info ? item.policy_info.category || '-' : '-',
          alerta: (item.risk_score || 0) > 80
        }));
        totalPagesRiesgo = Math.ceil(data.total / pageSizeRiesgo);
      } else {
        riesgoData = [];
        totalPagesRiesgo = 1;
      }
    } catch (err) {
      console.error('Error cargando datos de riesgo:', err);
      riesgoData = [];
      totalPagesRiesgo = 1;
    } finally {
      loadingRiesgo = false;
    }
  }

  function changePageRiesgo(newPage: number) {
    if (newPage >= 1 && newPage <= totalPagesRiesgo) {
      currentPageRiesgo = newPage;
      loadRiesgoData();
    }
  }

  function filtrar() {
    loadRegistros();
    loadTarjetas();
    loadAlertStats();
    if (activeTab === 'riesgo') {
      loadRiesgoData();
    }
  }

  // Función para capitalizar cada palabra (primera mayúscula, resto minúscula) y mapear nombres personalizados
  function mostrarCategoria(cat: string) {
    if (cat === 'apuestas/juegos de azar') return 'Juegos de azar';
    if (cat === 'hackeo/actividades ilegales') return 'Actividades ilegales';
    if (cat === 'violencia/terrorismo') return 'Violencia';
    return cat.replace(/\w\S*/g, (txt) =>
      txt.charAt(0).toUpperCase() + txt.slice(1).toLowerCase()
    );
  }

  async function filtrarComport() {
    currentPageComport = 1;
    await loadComportamientoData();
  }

  // Modifico loadComportamientoData para filtrar por usuario, tipo y fechas
  async function loadComportamientoData() {
    loadingComportamiento = true;
    errorComportamiento = '';
    try {
      let params = new URLSearchParams();
      if (selectedUserComport) params.append('user_id', selectedUserComport);
      if (selectedTipoComport) params.append('tipo', selectedTipoComport);
      if (dateFromComport) params.append('date_from', dateFromComport);
      if (dateToComport) params.append('date_to', dateToComport);
      params.append('page', currentPageComport.toString());
      params.append('page_size', pageSizeComport.toString());
      const res = await fetch(`${API_URL}/api/navigation_logs/comport?${params.toString()}`, {
        headers: { 'Authorization': `Bearer ${auth.token}` }
      });
      const data = await res.json();
      if (data.success) {
        comportamientoData = data.data;
        totalPagesComport = Math.max(1, Math.ceil(data.total / pageSizeComport));
      } else {
        comportamientoData = [];
        totalPagesComport = 1;
        errorComportamiento = data.error || 'Error al cargar datos de comportamiento';
      }
    } catch (e) {
      errorComportamiento = 'Error al cargar datos de comportamiento';
      comportamientoData = [];
      totalPagesComport = 1;
    } finally {
      loadingComportamiento = false;
    }
  }

  function changePageComport(newPage: number) {
    if (newPage >= 1 && newPage <= totalPagesComport) {
      currentPageComport = newPage;
      loadComportamientoData();
    }
  }

  async function loadGeoData() {
    console.log('Llamando a loadGeoData');
    loadingGeo = true;
    errorGeo = '';
    try {
      let params = new URLSearchParams();
      if (selectedUserGeo) params.append('user_id', selectedUserGeo);
      if (selectedUbicacionGeo) {
        // Si la ubicación contiene una coma, separar en ciudad y país
        const [ciudad, pais] = selectedUbicacionGeo.split(',').map(s => s.trim());
        if (ciudad) params.append('ciudad', ciudad);
        if (pais) params.append('pais', pais);
      }
      if (dateFromGeo) params.append('date_from', dateFromGeo);
      if (dateToGeo) params.append('date_to', dateToGeo);
      if (selectedEstadoGeo) params.append('estado', selectedEstadoGeo);
      params.append('page', currentPageGeo.toString());
      params.append('page_size', pageSizeGeo.toString());
      const res = await fetch(`${API_URL}/api/navigation_logs/geo?${params.toString()}`, {
        headers: { 'Authorization': `Bearer ${auth.token}` }
      });
      const data = await res.json();
      if (data.success) {
        geoData = data.data;
        totalPagesGeo = Math.max(1, Math.ceil(data.total / pageSizeGeo));
      } else {
        geoData = [];
        totalPagesGeo = 1;
        errorGeo = data.error || 'Error al cargar datos de ubicación';
      }
    } catch (e) {
      errorGeo = 'Error al cargar datos de ubicación';
      geoData = [];
      totalPagesGeo = 1;
    } finally {
      loadingGeo = false;
    }
  }

  function changePageGeo(newPage: number) {
    if (newPage >= 1 && newPage <= totalPagesGeo) {
      currentPageGeo = newPage;
      loadGeoData();
    }
  }

  async function filtrarGeo() {
    currentPageGeo = 1;
    await loadGeoData();
  }

  async function filtrarRiesgo() {
    currentPageRiesgo = 1; // Reset to page 1 on filter change for this tab
    await loadRiesgoData();
  }

  async function filtrarBloq() {
    await loadRegistros();
    await loadTarjetas();
  }

  function switchTab(newTab: Tab) {
    console.log('Cambiando a pestaña:', newTab);
    activeTab = newTab;
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('alerts_active_tab', newTab);
    }
    if (newTab === 'centro' && !centroDataLoaded) {
      loadAlertStats();
      centroDataLoaded = true;
    } else if (newTab === 'riesgo' && !riesgoDataLoaded) {
      loadRiesgoData();
      riesgoDataLoaded = true;
    } else if (newTab === 'bloqueos' && !bloqNetDataLoaded) {
      loadRegistros();
      loadTarjetas(); // Assuming tarjetas are part of BloqNet
      bloqNetDataLoaded = true;
    } else if (newTab === 'comportamiento' && !comportamientoDataLoaded) {
      loadComportamientoData();
      comportamientoDataLoaded = true;
    } else if (newTab === 'geo' && !geoDataLoaded) {
      loadGeoData();
      geoDataLoaded = true;
    }
  }

  onMount(async () => {
    console.log('activeTab al montar:', activeTab);
    if (!auth.token) {
      const currentPath = window.location.pathname;
      goto(`/login?redirect=${encodeURIComponent(currentPath)}`);
      return;
    }
    await loadCategorias();
    await loadUsers();

    // Cargar datos para la pestaña activa
    if (activeTab === 'centro') {
      await loadAlertStats();
      centroDataLoaded = true;
    } else if (activeTab === 'riesgo') {
      await loadRiesgoData();
      riesgoDataLoaded = true;
    } else if (activeTab === 'bloqueos') {
      await loadRegistros();
      await loadTarjetas();
      bloqNetDataLoaded = true;
    } else if (activeTab === 'comportamiento') {
      await loadComportamientoData();
      comportamientoDataLoaded = true;
    } else if (activeTab === 'geo') {
      await loadGeoData();
      geoDataLoaded = true;
    }
  });
</script>

<Navbar active="alerts" />

<div class="min-h-screen bg-gray-100">
  <div class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Centro de Alertas</h1>
    </div>
    <!-- Pestañas -->
    <div class="border-b border-gray-200 mt-4">
      <nav class="-mb-px flex justify-between">
        <div class="flex space-x-8">
          <button class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'centro' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}" on:click={() => switchTab('centro')}>Centro de Alertas</button>
          <button class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'riesgo' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}" on:click={() => switchTab('riesgo')}>RiesgoAct</button>
          <button class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'bloqueos' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}" on:click={() => switchTab('bloqueos')}>BloqNet</button>
          <button class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'comportamiento' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}" on:click={() => switchTab('comportamiento')}>ComportGuard</button>
          <button class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'geo' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}" on:click={() => switchTab('geo')}>GeoAlerta</button>
        </div>
      </nav>
    </div>

    <!-- Contenido principal -->
    <div class="mt-6">
      {#if activeTab === 'centro'}
        <!-- Contenido del Centro de Alertas -->
        <div class="bg-white shadow overflow-hidden sm:rounded-lg">
          <div class="p-6 border-b border-gray-200">
            <h2 class="text-lg font-semibold text-gray-900 mb-2">Centro de Alertas</h2>
            <p class="text-gray-600">Visualización y análisis de alertas de seguridad, incluyendo distribución por categoría, nivel de riesgo y tendencias temporales.</p>
          </div>
          <!-- Filtros -->
          <!--
          <div class="flex flex-wrap gap-4 mb-8 items-end mt-6 px-6">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Usuario</label>
              <select class="border rounded px-2 py-1 min-w-[180px]" bind:value={selectedUser} on:change={filtrar}>
                <option value="">Todos</option>
                {#each users as user}
                  <option value={user.id}>{user.email}</option>
                {/each}
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Categoría</label>
              <select class="border rounded px-2 py-1 min-w-[180px]" bind:value={selectedCategoria} on:change={filtrar}>
                <option value="">Todas</option>
                {#each categorias as cat}
                  <option value={cat}>{cat}</option>
                {/each}
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Desde</label>
              <input class="border rounded px-2 py-1" type="date" bind:value={dateFrom} on:change={filtrar} />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Hasta</label>
              <input class="border rounded px-2 py-1" type="date" bind:value={dateTo} on:change={filtrar} />
            </div>
          </div>
          -->
          <!-- Resumen de alertas -->
          <div class="flex flex-nowrap gap-4 mb-8 overflow-x-auto px-4 md:px-12 justify-center pt-6">
            <div class="rounded-xl px-6 py-6 bg-red-50 flex flex-col items-center min-w-[200px]">
              <span class="text-4xl font-extrabold text-red-600">{alertStats.alerts_by_severity.high}</span>
              <span class="text-base text-gray-700 mt-1">Alertas de Alto Riesgo</span>
            </div>
            <div class="rounded-xl px-6 py-6 bg-yellow-50 flex flex-col items-center min-w-[200px]">
              <span class="text-4xl font-extrabold text-yellow-600">{alertStats.alerts_by_severity.medium}</span>
              <span class="text-base text-gray-700 mt-1">Alertas de Riesgo Medio</span>
            </div>
            <div class="rounded-xl px-6 py-6 bg-green-50 flex flex-col items-center min-w-[200px]">
              <span class="text-4xl font-extrabold text-green-600">{alertStats.alerts_by_severity.low}</span>
              <span class="text-base text-gray-700 mt-1">Alertas de Bajo Riesgo</span>
            </div>
          </div>
          {#if loadingStats}
            <div class="text-center py-6">
              <p class="text-gray-500">Cargando estadísticas...</p>
            </div>
          {:else}
            <!-- Gráficos modernos -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8 px-6">
              <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-lg font-semibold mb-2">Distribución por Categoría</h3>
                <div class="h-80">
                  <ChartBar data={categoryBarData} options={{...barOptions, scales: { ...barOptions.scales, x: { ...barOptions.scales.x, title: { display: true, text: 'Categoría' }}}}} />
                </div>
              </div>
              <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-lg font-semibold mb-2">Distribución por Hora</h3>
                <div class="h-80">
                  <ChartBar data={hourBarData} options={{...barOptions, scales: { ...barOptions.scales, x: { ...barOptions.scales.x, title: { display: true, text: 'Hora' }}}}} />
                </div>
              </div>
              <div class="bg-white rounded-lg shadow p-6 col-span-2">
                <h3 class="text-lg font-semibold mb-2">Tendencia de Alertas</h3>
                <div class="h-80">
                  <ChartLine data={trendLineData} options={lineOptions} />
                </div>
              </div>
            </div>
          {/if}
        </div>
      {:else if activeTab === 'riesgo'}
        <!-- Contenido de RiesgoAct -->
        <div class="bg-white shadow overflow-hidden sm:rounded-lg">
          <div class="p-6 border-b border-gray-200">
            <div class="flex items-center gap-2 relative">
              <h2 class="text-lg font-semibold text-gray-900">Análisis de Riesgo de Navegación</h2>
              <button
                type="button"
                class="focus:outline-none"
                aria-label="Información sobre el cálculo de riesgo"
                on:click={() => showRiskModal = true}
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-400 cursor-help" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </button>
            </div>
            <p class="text-gray-600">Evaluación del nivel de riesgo asociado a la navegación de los usuarios, basado en patrones de comportamiento, sitios visitados y políticas de seguridad.</p>
          </div>

          {#if showRiskModal}
            <!-- Overlay -->
            <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity z-40" on:click={() => showRiskModal = false}></div>
            <!-- Modal -->
            <div class="fixed z-50 inset-0 flex items-center justify-center">
              <div class="bg-white rounded-lg shadow-xl max-w-lg w-full p-6 relative" on:click|stopPropagation>
                <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">¿Cómo se calcula el riesgo?</h3>
                <div class="text-sm text-gray-600">
                  <p class="mb-3">El sistema calcula un puntaje de riesgo (0-100) basado en diferentes factores:</p>
                  <h4 class="font-medium text-gray-800 mb-1">Tipos de Eventos:</h4>
                  <table class="w-full mb-3 text-xs">
                    <thead>
                      <tr class="bg-gray-50">
                        <th class="px-2 py-1 text-left">Evento</th>
                        <th class="px-2 py-1 text-right">Puntaje Base</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr class="border-b border-gray-100">
                        <td class="px-2 py-1">Formulario</td>
                        <td class="px-2 py-1 text-right">+20</td>
                      </tr>
                      <tr class="border-b border-gray-100">
                        <td class="px-2 py-1">Descarga</td>
                        <td class="px-2 py-1 text-right">+30</td>
                      </tr>
                      <tr class="border-b border-gray-100">
                        <td class="px-2 py-1">Bloqueo</td>
                        <td class="px-2 py-1 text-right">+50</td>
                      </tr>
                      <tr class="border-b border-gray-100">
                        <td class="px-2 py-1">Copiar/Pegar</td>
                        <td class="px-2 py-1 text-right">+25</td>
                      </tr>
                      <tr class="border-b border-gray-100">
                        <td class="px-2 py-1">Carga de archivo</td>
                        <td class="px-2 py-1 text-right">+35</td>
                      </tr>
                      <tr>
                        <td class="px-2 py-1">Click</td>
                        <td class="px-2 py-1 text-right">+15</td>
                      </tr>
                    </tbody>
                  </table>
                  <h4 class="font-medium text-gray-800 mb-1">Factores Adicionales:</h4>
                  <table class="w-full mb-3 text-xs">
                    <thead>
                      <tr class="bg-gray-50">
                        <th class="px-2 py-1 text-left">Factor</th>
                        <th class="px-2 py-1 text-right">Puntaje</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr class="border-b border-gray-100">
                        <td class="px-2 py-1">Campos sensibles</td>
                        <td class="px-2 py-1 text-right">+15</td>
                      </tr>
                      <tr class="border-b border-gray-100">
                        <td class="px-2 py-1">Archivo .exe/.zip/.rar</td>
                        <td class="px-2 py-1 text-right">+25</td>
                      </tr>
                      <tr>
                        <td class="px-2 py-1">Otros archivos (.pdf/.doc)</td>
                        <td class="px-2 py-1 text-right">+20</td>
                      </tr>
                    </tbody>
                  </table>
                  <div class="mt-3 text-xs">
                    <p class="font-medium text-gray-800">Niveles de Riesgo:</p>
                    <ul class="list-disc list-inside space-y-1 mt-1">
                      <li><span class="text-green-600">0-50: Bajo</span> - Actividad normal</li>
                      <li><span class="text-yellow-600">51-80: Medio</span> - Requiere atención</li>
                      <li><span class="text-red-600">81-100: Alto</span> - Acción inmediata</li>
                    </ul>
                  </div>
                </div>
                <div class="mt-6 flex justify-end">
                  <button type="button" on:click={() => showRiskModal = false} class="px-4 py-2 rounded bg-indigo-600 text-white font-semibold hover:bg-indigo-700">Cerrar</button>
                </div>
              </div>
            </div>
          {/if}

          {#if loadingRiesgo}
            <div class="text-center py-6">
              <p class="text-gray-500">Cargando datos de riesgo...</p>
            </div>
          {:else if riesgoData.length === 0}
            <div class="text-center py-6">
              <p class="text-gray-500">No hay datos de riesgo para mostrar.</p>
            </div>
          {:else}
            <div class="flex flex-wrap gap-4 mb-8 items-end mt-6 px-6">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Usuario</label>
                <select class="border rounded px-2 py-1 min-w-[180px]" bind:value={selectedUserRiesgo} on:change={filtrarRiesgo}>
                  <option value="">Todos</option>
                  {#each users as user}
                    <option value={user.id}>{user.email}</option>
                  {/each}
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Categoría</label>
                <select class="border rounded px-2 py-1 min-w-[180px]" bind:value={selectedCategoriaRiesgo} on:change={filtrarRiesgo}>
                  <option value="">Todas</option>
                  {#each categorias as cat}
                    <option value={cat}>{cat}</option>
                  {/each}
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Alerta</label>
                <select class="border rounded px-2 py-1 min-w-[120px]" bind:value={alertaRiesgo} on:change={filtrarRiesgo}>
                  {#each alertaOptions as opt}
                    <option value={opt.value}>{opt.label}</option>
                  {/each}
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Desde</label>
                <input class="border rounded px-2 py-1" type="date" bind:value={dateFromRiesgo} on:change={filtrarRiesgo} />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Hasta</label>
                <input class="border rounded px-2 py-1" type="date" bind:value={dateToRiesgo} on:change={filtrarRiesgo} />
              </div>
            </div>
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Usuario</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Puntaje</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sitio</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Hora</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Categoría</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Alerta</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                {#each riesgoData as item}
                  <tr class="hover:bg-gray-50">
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{item.usuario}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">
                      <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full {item.puntaje > 80 ? 'bg-red-100 text-red-800' : item.puntaje > 50 ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}">
                        {item.puntaje}
                      </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item.sitio}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item.hora}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item.categoria}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">
                      {#if item.alerta}
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
                          Sí
                        </span>
                      {:else}
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                          No
                        </span>
                      {/if}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>

            <!-- Paginación -->
            <div class="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
              <div class="flex-1 flex justify-between sm:hidden">
                <button
                  on:click={() => changePageRiesgo(currentPageRiesgo - 1)}
                  disabled={currentPageRiesgo === 1}
                  class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 {currentPageRiesgo === 1 ? 'opacity-50 cursor-not-allowed' : ''}"
                >
                  Anterior
                </button>
                <button
                  on:click={() => changePageRiesgo(currentPageRiesgo + 1)}
                  disabled={currentPageRiesgo === totalPagesRiesgo}
                  class="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 {currentPageRiesgo === totalPagesRiesgo ? 'opacity-50 cursor-not-allowed' : ''}"
                >
                  Siguiente
                </button>
              </div>
              <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                <div>
                  <p class="text-sm text-gray-700">
                    Mostrando página <span class="font-medium">{currentPageRiesgo}</span> de <span class="font-medium">{totalPagesRiesgo}</span>
                  </p>
                </div>
                <div>
                  <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                    <button
                      on:click={() => changePageRiesgo(currentPageRiesgo - 1)}
                      disabled={currentPageRiesgo === 1}
                      class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 {currentPageRiesgo === 1 ? 'opacity-50 cursor-not-allowed' : ''}"
                    >
                      <span class="sr-only">Anterior</span>
                      <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd" />
                      </svg>
                    </button>
                    {#each Array(Math.min(5, totalPagesRiesgo)) as _, i}
                      {@const pageNum = i + 1}
                      <button
                        on:click={() => changePageRiesgo(pageNum)}
                        class="relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium {pageNum === currentPageRiesgo ? 'text-indigo-600 bg-indigo-50' : 'text-gray-700 hover:bg-gray-50'}"
                      >
                        {pageNum}
                      </button>
                    {/each}
                    <button
                      on:click={() => changePageRiesgo(currentPageRiesgo + 1)}
                      disabled={currentPageRiesgo === totalPagesRiesgo}
                      class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 {currentPageRiesgo === totalPagesRiesgo ? 'opacity-50 cursor-not-allowed' : ''}"
                    >
                      <span class="sr-only">Siguiente</span>
                      <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
                      </svg>
                    </button>
                  </nav>
                </div>
              </div>
            </div>
          {/if}
        </div>
      {:else if activeTab === 'bloqueos'}
        <!-- Contenido de BloqNet -->
        <div class="mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-2">BloqNet</h2>
          <p class="text-gray-600 mb-4">Visualización y análisis de los intentos de acceso bloqueados o permitidos, agrupados por categoría de contenido.</p>
          <!--
          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            {#each tarjetas as tarjeta}
              <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 flex flex-col items-center">
                <span class="text-lg font-bold text-blue-700">{mostrarCategoria(tarjeta.category)}</span>
                <span class="text-2xl font-extrabold text-blue-900">{tarjeta.count}</span>
              </div>
            {/each}
          </div>
          -->
        </div>
        <!-- Filtros BloqNet -->
        <div class="flex flex-wrap gap-4 mb-8 items-end mt-6 px-6">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Usuario</label>
            <select class="border rounded px-2 py-1 min-w-[180px]" bind:value={selectedUserBloq} on:change={filtrarBloq}>
              <option value="">Todos</option>
              {#each users as user}
                <option value={user.id}>{user.email}</option>
              {/each}
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Categoría</label>
            <select class="border rounded px-2 py-1 min-w-[180px]" bind:value={selectedCategoriaBloq} on:change={filtrarBloq}>
              <option value="">Todas</option>
              {#each categorias as cat}
                <option value={cat}>{cat}</option>
              {/each}
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Estado</label>
            <select class="border rounded px-2 py-1 min-w-[120px]" bind:value={selectedEstadoBloq} on:change={filtrarBloq}>
              {#each estadoBloqOptions as opt}
                <option value={opt.value}>{opt.label}</option>
              {/each}
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Desde</label>
            <input class="border rounded px-2 py-1" type="date" bind:value={dateFromBloq} on:change={filtrarBloq} />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Hasta</label>
            <input class="border rounded px-2 py-1" type="date" bind:value={dateToBloq} on:change={filtrarBloq} />
          </div>
        </div>
        <!-- Tabla de registros -->
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200 mt-4">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Usuario</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/3">Dominio</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Categoría</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Motivo</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha/Hora</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              {#if loadingRegistros}
                <tr><td colspan="6" class="text-center text-gray-400 py-6">Cargando registros...</td></tr>
              {:else if registros.length === 0}
                <tr><td colspan="6" class="text-center text-gray-400 py-6">No hay bloqueos para mostrar.</td></tr>
              {:else}
                {#each registros as reg}
                  <tr class="hover:bg-gray-50">
                    <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{users.find(u => u.id === reg.user_id)?.email || reg.user_id}</td>
                    <td class="px-4 py-4 text-sm text-gray-500 break-all max-w-xs">
                      <div class="truncate" title={reg.domain}>{reg.domain}</div>
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap text-sm">{reg.policy_info?.category || '-'}</td>
                    <td class="px-4 py-4 whitespace-nowrap text-sm">
                      <span class="px-2 py-1 text-xs font-semibold rounded-full {reg.action === 'bloqueado' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}">
                        {reg.action === 'bloqueado' ? 'Bloqueado' : 'Permitido'}
                      </span>
                    </td>
                    <td class="px-4 py-4 text-sm text-gray-500 max-w-xs">
                      <div class="truncate" title={reg.policy_info?.block_reason || '-'}>{reg.policy_info?.block_reason || '-'}</div>
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap text-sm">{new Date(reg.timestamp).toLocaleString()}</td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      {:else if activeTab === 'comportamiento'}
        <!-- Contenido de ComportGuard -->
        <div class="bg-white shadow overflow-hidden sm:rounded-lg">
          <div class="p-6 border-b border-gray-200">
            <h2 class="text-lg font-semibold text-gray-900 mb-2">Detección de Comportamientos Anómalos</h2>
            <p class="text-gray-600">Identificación de patrones de comportamiento inusuales o sospechosos en la navegación de los usuarios, incluyendo cambios de horario, accesos a sitios inusuales y patrones irregulares.</p>
          </div>
          <!-- Filtros ComportGuard -->
          <div class="flex flex-wrap gap-4 mb-8 items-end mt-6 px-6">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Usuario</label>
              <select class="border rounded px-2 py-1 min-w-[180px]" bind:value={selectedUserComport} on:change={filtrarComport}>
                <option value="">Todos</option>
                {#each users as user}
                  <option value={user.id}>{user.email}</option>
                {/each}
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
              <select class="border rounded px-2 py-1 min-w-[180px]" bind:value={selectedTipoComport} on:change={filtrarComport}>
                <option value="">Todos</option>
                {#each tiposComport as tipo}
                  <option value={tipo}>{tipo}</option>
                {/each}
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Desde</label>
              <input class="border rounded px-2 py-1" type="date" bind:value={dateFromComport} on:change={filtrarComport} />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Hasta</label>
              <input class="border rounded px-2 py-1" type="date" bind:value={dateToComport} on:change={filtrarComport} />
            </div>
          </div>
          {#if loadingComportamiento}
            <div class="text-center py-6">
              <p class="text-gray-500">Cargando datos de comportamiento...</p>
            </div>
          {:else if errorComportamiento}
            <div class="text-center py-6 text-red-500">{errorComportamiento}</div>
          {:else if comportamientoData.length === 0}
            <div class="text-center py-6">
              <p class="text-gray-500">No hay datos de comportamiento para mostrar.</p>
            </div>
          {:else}
            <div class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">Usuario</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">Tipo</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">Detalle</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">Fecha/Hora</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">Estado</th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  {#each comportamientoData as item}
                    <tr>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{users.find(u => u.id === item.usuario)?.email || item.usuario}</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm">
                        {#if item.tipo === 'Sitio inusual'}
                          <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">{item.tipo}</span>
                        {:else}
                          <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">{item.tipo}</span>
                        {/if}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 break-all max-w-xs">
                        <div class="truncate" title={item.detalle}>{item.detalle}</div>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{new Date(item.hora).toLocaleString()}</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm">
                        {#if item.sospechoso}
                          <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">Sospechoso</span>
                        {:else}
                          <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">Normal</span>
                        {/if}
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
            <!-- Paginación -->
            <div class="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
              <div class="flex-1 flex justify-between sm:hidden">
                <button
                  on:click={() => changePageComport(currentPageComport - 1)}
                  disabled={currentPageComport === 1}
                  class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 {currentPageComport === 1 ? 'opacity-50 cursor-not-allowed' : ''}"
                >
                  Anterior
                </button>
                <button
                  on:click={() => changePageComport(currentPageComport + 1)}
                  disabled={currentPageComport === totalPagesComport}
                  class="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 {currentPageComport === totalPagesComport ? 'opacity-50 cursor-not-allowed' : ''}"
                >
                  Siguiente
                </button>
              </div>
              <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                <div>
                  <p class="text-sm text-gray-700">
                    Mostrando página <span class="font-medium">{currentPageComport}</span> de <span class="font-medium">{totalPagesComport}</span>
                  </p>
                </div>
                <div>
                  <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                    <button
                      on:click={() => changePageComport(currentPageComport - 1)}
                      disabled={currentPageComport === 1}
                      class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 {currentPageComport === 1 ? 'opacity-50 cursor-not-allowed' : ''}"
                    >
                      <span class="sr-only">Anterior</span>
                      <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd" />
                      </svg>
                    </button>
                    {#each Array(Math.min(5, totalPagesComport)) as _, i}
                      {@const pageNum = i + 1}
                      <button
                        on:click={() => changePageComport(pageNum)}
                        class="relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium {pageNum === currentPageComport ? 'text-indigo-600 bg-indigo-50' : 'text-gray-700 hover:bg-gray-50'}"
                      >
                        {pageNum}
                      </button>
                    {/each}
                    <button
                      on:click={() => changePageComport(currentPageComport + 1)}
                      disabled={currentPageComport === totalPagesComport}
                      class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 {currentPageComport === totalPagesComport ? 'opacity-50 cursor-not-allowed' : ''}"
                    >
                      <span class="sr-only">Siguiente</span>
                      <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
                      </svg>
                    </button>
                  </nav>
                </div>
              </div>
            </div>
          {/if}
        </div>
      {:else if activeTab === 'geo'}
        <!-- Contenido de GeoAlerta -->
        <div class="bg-white shadow overflow-hidden sm:rounded-lg">
          <div class="p-6 border-b border-gray-200">
            <h2 class="text-lg font-semibold text-gray-900 mb-2">Monitoreo de Accesos por Ubicación</h2>
            <p class="text-gray-600">Seguimiento de los accesos por ubicación geográfica, identificando accesos desde IPs no habituales o ubicaciones inusuales para cada usuario.</p>
          </div>
          <!-- Filtros GeoAlerta -->
          <div class="flex flex-wrap gap-4 mb-8 items-end mt-6 px-6">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Usuario</label>
              <select class="border rounded px-2 py-1 min-w-[180px]" bind:value={selectedUserGeo} on:change={filtrarGeo}>
                <option value="">Todos</option>
                {#each users as user}
                  <option value={user.id}>{user.email}</option>
                {/each}
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Ubicación</label>
              <input class="border rounded px-2 py-1 min-w-[180px]" type="text" bind:value={selectedUbicacionGeo} on:change={filtrarGeo} placeholder="Ciudad, País o ambos" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Estado</label>
              <select class="border rounded px-2 py-1 min-w-[120px]" bind:value={selectedEstadoGeo} on:change={filtrarGeo}>
                {#each estadosGeo as est}
                  <option value={est.value}>{est.label}</option>
                {/each}
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Desde</label>
              <input class="border rounded px-2 py-1" type="date" bind:value={dateFromGeo} on:change={filtrarGeo} />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Hasta</label>
              <input class="border rounded px-2 py-1" type="date" bind:value={dateToGeo} on:change={filtrarGeo} />
            </div>
          </div>
          {#if loadingGeo}
            <div class="text-center py-6">
              <p class="text-gray-500">Cargando datos de ubicación...</p>
            </div>
          {:else if errorGeo}
            <div class="text-center py-6 text-red-500">{errorGeo}</div>
          {:else if geoData.length === 0}
            <div class="text-center py-6">
              <p class="text-gray-500">No hay datos de ubicación para mostrar.</p>
            </div>
          {:else}
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Usuario</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">IP</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Hora</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                {#each geoData as item, i}
                  <tr>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{users.find((u: any) => u.id === (item as GeoData).usuario)?.email || (item as GeoData).usuario}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{(item as GeoData).ip}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">
                      {#if (item as GeoData).alerta}
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
                          IP No Habitual
                        </span>
                      {:else}
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                          IP Habitual
                        </span>
                      {/if}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{(item as GeoData).hora}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
            <!-- Paginación -->
            <div class="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
              <div class="flex-1 flex justify-between sm:hidden">
                <button
                  on:click={() => changePageGeo(currentPageGeo - 1)}
                  disabled={currentPageGeo === 1}
                  class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 {currentPageGeo === 1 ? 'opacity-50 cursor-not-allowed' : ''}"
                >
                  Anterior
                </button>
                <button
                  on:click={() => changePageGeo(currentPageGeo + 1)}
                  disabled={currentPageGeo === totalPagesGeo}
                  class="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 {currentPageGeo === totalPagesGeo ? 'opacity-50 cursor-not-allowed' : ''}"
                >
                  Siguiente
                </button>
              </div>
              <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                <div>
                  <p class="text-sm text-gray-700">
                    Mostrando página <span class="font-medium">{currentPageGeo}</span> de <span class="font-medium">{totalPagesGeo}</span>
                  </p>
                </div>
                <div>
                  <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                    <button
                      on:click={() => changePageGeo(currentPageGeo - 1)}
                      disabled={currentPageGeo === 1}
                      class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 {currentPageGeo === 1 ? 'opacity-50 cursor-not-allowed' : ''}"
                    >
                      <span class="sr-only">Anterior</span>
                      <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd" />
                      </svg>
                    </button>
                    {#each Array(Math.min(5, totalPagesGeo)) as _, i}
                      {@const pageNum = i + 1}
                      <button
                        on:click={() => changePageGeo(pageNum)}
                        class="relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium {pageNum === currentPageGeo ? 'text-indigo-600 bg-indigo-50' : 'text-gray-700 hover:bg-gray-50'}"
                      >
                        {pageNum}
                      </button>
                    {/each}
                    <button
                      on:click={() => changePageGeo(currentPageGeo + 1)}
                      disabled={currentPageGeo === totalPagesGeo}
                      class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 {currentPageGeo === totalPagesGeo ? 'opacity-50 cursor-not-allowed' : ''}"
                    >
                      <span class="sr-only">Siguiente</span>
                      <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
                      </svg>
                    </button>
                  </nav>
                </div>
              </div>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  </div>
</div> 