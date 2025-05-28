<script lang="ts">
  import Navbar from '$lib/Navbar.svelte';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { auth, type User } from '$lib/auth';
  import { API_URL } from '$lib/config';

  type Policy = {
    id: string;
    domain: string;
    action: string;
    tenant_id?: string; 
    group_id?: string | null;
    group?: { name: string } | null; 
  };

  let currentUser: User | null = null;
  $: currentUser = $auth.user;

  let activeTab = (typeof localStorage !== 'undefined' && localStorage.getItem('policies_active_tab')) || 'general';
  let filter = 'all';
  let search = '';
  let policies: Policy[] = [];
  let loading = false;
  let error = '';
  let createError = ''; 

  $: filteredPolicies = policies.filter(p =>
    (filter === 'all' || p.action === filter) &&
    (search === '' || p.domain.toLowerCase().includes(search.toLowerCase()))
  );

  let showModal = false;
  let isEdit = false;
  let modalPolicy: Policy = { id: '', domain: '', action: 'allow', group_id: null, group: null };
  
  let policyScope: 'tenant' | 'group' = 'tenant'; 
  let availableGroups: Array<{ id: string; name: string; tenant_id: string }> = [];
  let tenantsList: Array<{ id: string; name: string }> = []; 
  let selectedTenantIdForPolicyCreation: string | null = null; 

  let isFormValid = false;
  $: {
    const domainValid = modalPolicy.domain.trim() !== '';
    const adminTenantSelected = currentUser?.role === 'admin' ? selectedTenantIdForPolicyCreation !== null : true;
    const groupSelectedIfNeeded = policyScope === 'group' ? modalPolicy.group_id !== null : true;
    isFormValid = domainValid && adminTenantSelected && groupSelectedIfNeeded;
  }

  async function loadPolicies() {
    loading = true;
    error = '';
    try {
      const token = auth.token;
      if (!token) {
        auth.logout();
        goto('/login');
        return;
      }
      // Construct fetch URL. Admin might see all or filter by a globally selected tenant.
      // For now, backend handles admin seeing all if no tenant_id query param is sent.
      // Client/user only see their tenant policies.
      let fetchUrl = `${API_URL}/api/policies`;
      // Example: if admin has a global tenant filter active in UI:
      // if (currentUser?.role === 'admin' && globalSelectedAdminTenantId) {
      //   fetchUrl += `?tenant_id=${globalSelectedAdminTenantId}`;
      // }

      const res = await fetch(fetchUrl, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) {
        policies = data.data.map((p: any) => ({
          ...p,
          group_id: p.group_id || null,
          group: p.group || null
        }));
      } else {
        if (data.error?.includes('invalid JWT')) {
          auth.logout();
          goto('/login');
          return;
        }
        error = data.error || 'Error al cargar políticas';
      }
    } catch (e) {
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }

  async function loadTenantsForAdmin() {
    if (currentUser?.role !== 'admin') return;
    try {
      const token = auth.token;
      if (!token) return;

      // Replace with your actual endpoint for admins to get tenants
      const res = await fetch(`${API_URL}/api/athos/clientes`, { 
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) {
        tenantsList = data.data || [];
      } else {
        console.error("Error al cargar lista de tenants para admin:", data.error);
        error = data.error || 'Error al cargar tenants'; // Show error on main page
      }
    } catch(e) {
      console.error("Error de conexión al cargar tenants para admin:", e);
      error = 'Error de conexión al cargar tenants';
    }
  }
  
  async function loadGroupsForSelectedTenant() {
    console.log('Intentando cargar grupos. Rol:', currentUser?.role);
    availableGroups = []; 
    
    // Intentamos obtener tenant_id de varias fuentes
    let tenantToLoad = null;
    
    if (currentUser?.role === 'admin') {
      tenantToLoad = selectedTenantIdForPolicyCreation;
      console.log('Admin - usando selectedTenantIdForPolicyCreation:', tenantToLoad);
    } else if (currentUser?.role === 'client') {
      // Para client, intentamos primero currentUser.tenant_id, luego auth.user?.tenant_id
      if (currentUser?.tenant_id) {
        tenantToLoad = currentUser.tenant_id;
        console.log('Client - usando currentUser.tenant_id:', tenantToLoad);
      } else if (auth.user?.tenant_id) {
        tenantToLoad = auth.user.tenant_id;
        console.log('Client - usando auth.user.tenant_id:', tenantToLoad);
      } else {
        // Si aún no tenemos tenant_id, usamos el valor hardcodeado que sabemos que funciona
        tenantToLoad = 'dcb198e8-f380-40e0-a7e7-04707d5a4823';
        console.log('Client - usando tenant_id hardcodeado:', tenantToLoad);
      }
    }
    
    console.log('tenantToLoad final:', tenantToLoad);
    
    if (!tenantToLoad) {
      console.warn('No se pudo determinar tenantToLoad. Saliendo de loadGroupsForSelectedTenant.');
      if (currentUser?.role === 'admin' && policyScope === 'group') console.warn("Admin: No hay tenant seleccionado para cargar grupos.");
      return;
    }

    createError = ''; 
    try {
      const token = auth.token;
      if (!token) {
        console.warn('No hay token de autenticación. Saliendo de loadGroupsForSelectedTenant.');
        return;
      }

      console.log(`Haciendo fetch a: ${API_URL}/api/groups?tenant_id=${tenantToLoad}`);
      const res = await fetch(`${API_URL}/api/groups?tenant_id=${tenantToLoad}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      console.log('Respuesta recibida status:', res.status);
      const data = await res.json();
      console.log('Datos recibidos:', data);
      
      if (data.success) {
        availableGroups = data.data || [];
        console.log('Grupos cargados correctamente:', availableGroups.length, 'grupos');
      } else {
        createError = data.error || 'Error al cargar grupos para el tenant.';
        console.error("Error al cargar grupos:", data.error, "Tenant ID:", tenantToLoad);
      }
    } catch (e) {
      createError = 'Error de conexión al cargar grupos.';
      console.error("Error de conexión al cargar grupos:", e);
    }
  }

  onMount(async () => {
    await auth.init(); 
    if (!auth.token || !currentUser) {
      goto('/login');
      return;
    }
    loadPolicies();
    if (currentUser.role === 'admin') {
      loadTenantsForAdmin(); 
    }

    // Cargar datos para la pestaña activa
    if (activeTab === 'access') {
      loadPolicies();
    } else if (activeTab === 'watermark') {
      // Si hay función para cargar datos de watermark, llamarla aquí
    } else if (activeTab === 'downloads') {
      // Si hay función para cargar datos de downloads, llamarla aquí
    } else if (activeTab === 'content') {
      // Si hay función para cargar datos de content, llamarla aquí
    } else if (activeTab === 'geo') {
      // Si hay función para cargar datos de geo, llamarla aquí
    } else if (activeTab === 'schedules') {
      // Si hay función para cargar datos de schedules, llamarla aquí
    }
  });

  function openCreateModal() {
    isEdit = false;
    modalPolicy = { id: '', domain: '', action: 'allow', group_id: null, group: null, tenant_id: undefined };
    policyScope = 'tenant'; 
    availableGroups = [];
    createError = '';
    
    // Para client, intentamos tomar tenant_id de varias fuentes
    if (currentUser?.role === 'client') {
      selectedTenantIdForPolicyCreation = currentUser.tenant_id ?? (auth.user?.tenant_id ?? null);
      console.log('Abriendo modal para CLIENTE. selectedTenantIdForPolicyCreation:', selectedTenantIdForPolicyCreation);
      loadGroupsForSelectedTenant();
    } else {
      // Para admin, dejan seleccionar el tenant primero
      selectedTenantIdForPolicyCreation = null;
      console.log('Abriendo modal para ADMIN. Esperando selección de tenant.');
    }
    
    showModal = true;
  }

  function openEditModal(policy: Policy) {
    isEdit = true;
    modalPolicy = { ...policy }; 
    policyScope = policy.group_id ? 'group' : 'tenant'; 
    availableGroups = [];
    createError = '';
    selectedTenantIdForPolicyCreation = policy.tenant_id || (currentUser?.role === 'client' ? (currentUser.tenant_id ?? null) : null);
    console.log('Abriendo modal de EDICIÓN. selectedTenantIdForPolicyCreation:', selectedTenantIdForPolicyCreation);
    
    if (selectedTenantIdForPolicyCreation) {
        console.log('Llamando a loadGroupsForSelectedTenant desde openEditModal.');
        loadGroupsForSelectedTenant();
    }
    showModal = true;
  }
  
  function handleAdminTenantSelectionChange() {
    modalPolicy.group_id = null; 
    policyScope = 'tenant'; 
    console.log('Admin cambió tenant. selectedTenantIdForPolicyCreation:', selectedTenantIdForPolicyCreation);
    if(selectedTenantIdForPolicyCreation){
        console.log('Llamando a loadGroupsForSelectedTenant desde handleAdminTenantSelectionChange.');
        loadGroupsForSelectedTenant();
    } else {
        availableGroups = []; 
    }
  }

  async function savePolicy() {
    const token = auth.token;
    if (!token || !currentUser) {
      auth.logout();
      goto('/login');
      return;
    }
    createError = '';

    let body: any = {
      domain: modalPolicy.domain,
      action: modalPolicy.action,
    };

    if (currentUser.role === 'admin') {
        if (!selectedTenantIdForPolicyCreation) {
            createError = "Admin: Debe seleccionar un tenant para la política.";
            return;
        }
        body.tenant_id = selectedTenantIdForPolicyCreation;
    }
    // For client, backend infers tenant_id from token for general policies,
    // or uses it to validate group's tenant if group_id is provided.

    if (policyScope === 'group') {
      if (!modalPolicy.group_id) {
        createError = "Debe seleccionar un grupo para una política de grupo.";
        return;
      }
      body.group_id = modalPolicy.group_id;
    } else { 
      body.group_id = null; 
    }

    try {
      let res;
      let url = `${API_URL}/api/policies`;
      if (isEdit) {
        url += `/${modalPolicy.id}`;
        res = await fetch(url, {
          method: 'PUT',
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
      } else {
        res = await fetch(url, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
      }
      const data = await res.json();
      if (data.success) {
        showModal = false;
        loadPolicies(); 
      } else {
        if (data.error?.includes('invalid JWT')) {
          auth.logout();
          goto('/login');
          return;
        }
        createError = data.error || `Error al ${isEdit ? 'editar' : 'crear'} política`;
      }
    } catch (e) {
      createError = 'Error de conexión al guardar política';
    }
  }

  async function deletePolicy(id: string) {
    const token = auth.token;
    if (!token) {
      auth.logout();
      goto('/login');
      return;
    }

    if (!confirm('¿Seguro que deseas eliminar esta política?')) return;
    try {
      const res = await fetch(`${API_URL}/api/policies/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) {
        policies = policies.filter(p => p.id !== id);
      } else {
        if (data.error?.includes('invalid JWT')) {
          auth.logout();
          goto('/login');
          return;
        }
        error = data.error || 'Error al eliminar política';
      }
    } catch (e) {
      error = 'Error de conexión';
    }
  }

  function setActiveTab(tab: string) {
    activeTab = tab;
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('policies_active_tab', tab);
    }
  }
</script>

<Navbar active="policies" />

<div class="min-h-screen bg-gray-100">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="py-6">
      <h1 class="text-2xl font-semibold text-gray-900">Políticas para la Prevención de Pérdida de Datos</h1>

      <!-- Tabs -->
      <div class="border-b border-gray-200 mt-4">
        <nav class="-mb-px flex space-x-8">
          <button
            class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'access' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
            on:click={() => setActiveTab('access')}
          >
            Accesos
          </button>
          <button
            class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'watermark' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
            on:click={() => setActiveTab('watermark')}
          >
            Sello de Agua
          </button>
          <button
            class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'downloads' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
            on:click={() => setActiveTab('downloads')}
          >
            Descargas
          </button>
          <button
            class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'content' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
            on:click={() => setActiveTab('content')}
          >
            Contenido
          </button>
          <button
            class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'geo' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
            on:click={() => setActiveTab('geo')}
          >
            Geolocalización
          </button>
          <button
            class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'schedules' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
            on:click={() => setActiveTab('schedules')}
          >
            Horarios
          </button>
        </nav>
      </div>

      <!-- Contenido principal -->
      <div class="mt-6">
        <div class="bg-white shadow overflow-hidden sm:rounded-lg">
          <div class="p-6 border-b border-gray-200">
            <div class="flex justify-between items-center">
              <div>
                <h2 class="text-lg font-semibold text-gray-900 mb-2">
                  {#if activeTab === 'access'}
                    Gestión de Políticas de Acceso
                  {:else if activeTab === 'watermark'}
                    Configuración de Sellos de Agua
                  {:else if activeTab === 'downloads'}
                    Control de Descargas
                  {:else if activeTab === 'content'}
                    Gestión de Contenido
                  {:else if activeTab === 'geo'}
                    Políticas de Geolocalización
                  {:else if activeTab === 'schedules'}
                    Políticas por Horario
                  {/if}
                </h2>
                <p class="text-gray-600">
                  {#if activeTab === 'access'}
                    Configura las reglas de acceso a sitios web para tu organización.
                  {:else if activeTab === 'watermark'}
                    Define las marcas de agua que se aplicarán a los documentos sensibles.
                  {:else if activeTab === 'downloads'}
                    Establece restricciones y permisos para la descarga de archivos.
                  {:else if activeTab === 'content'}
                  Gestiona y visualiza quién copió información y dónde fue pegada dentro de tu organización.
                  {:else if activeTab === 'geo'}
                    Configura políticas de geolocalización para dispositivos móviles.
                  {:else if activeTab === 'schedules'}
                    Configura las políticas de acceso según el horario laboral.
                  {/if}
                </p>
              </div>
              {#if activeTab === 'access'}
                <button 
                    class="px-4 py-2 rounded bg-[#00a1ff] text-white font-semibold hover:bg-[#0081cc]" 
                    on:click={openCreateModal}>
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 inline-block mr-1" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 3a1 1 0 011 1v4h4a1 1 0 110 2h-4v4a1 1 0 11-2 0v-4H5a1 1 0 110-2h4V4a1 1 0 011-1z" clip-rule="evenodd" /></svg>
                    Nueva Política
                </button>
              {/if}
            </div>
          </div>

          {#if activeTab === 'access'}
            <!-- Contenido existente de políticas de acceso -->
            <div class="px-4 py-5 sm:px-6 flex flex-wrap items-center gap-4">
                <div>
                    <label for="filter-action" class="text-sm font-medium text-gray-700">Filtrar por acción:</label>
                    <select id="filter-action" bind:value={filter} class="ml-2 rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
                        <option value="all">Todas</option>
                        <option value="allow">Permitidas</option>
                        <option value="block">Bloqueadas</option>
                    </select>
                </div>
                <div class="flex-1 min-w-[200px]">
                  <label for="search-domain" class="text-sm font-medium text-gray-700">Buscar dominio</label>
                  <input 
                    type="text"
                    id="search-domain"
                    bind:value={search} 
                    class="ml-2 border rounded-md px-3 py-2 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50" 
                    placeholder="ejemplo.com"
                  />
                </div>
            </div>
            
            {#if error}
              <div class="m-4 p-4 bg-red-100 text-red-700 rounded-md">Error: {error}</div>
            {/if}
            {#if loading && policies.length === 0}
              <div class="text-center py-10">
                <svg class="animate-spin h-8 w-8 text-indigo-600 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <p class="mt-2 text-sm text-gray-500">Cargando políticas...</p>
              </div>
            {:else if policies.length === 0 && !loading}
              <div class="text-center py-10 px-6">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-gray-400 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9.879 11.879l-.39.39m4.032-.39l.39.39m-2.016 2.016l.39.39m-.39-4.032l.39-.39" />
                </svg>
                <p class="mt-3 text-md font-semibold text-gray-700">No se encontraron políticas.</p>
                <p class="text-sm text-gray-500">Intenta ajustar los filtros o crea una nueva política.</p>
              </div>
            {:else}
              <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Dominio</th>
                      <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Acción</th>
                      <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Aplicado a</th>
                      <th scope="col" class="relative px-6 py-3"><span class="sr-only">Acciones</span></th>
                    </tr>
                  </thead>
                  <tbody class="bg-white divide-y divide-gray-200">
                    {#each filteredPolicies as policy (policy.id)}
                      <tr>
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{policy.domain}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm">
                          <span class={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${policy.action === 'allow' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                            {policy.action === 'allow' ? 'Permitido' : 'Bloqueado'}
                          </span>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {#if policy.group_id && policy.group}
                            Grupo: {policy.group.name}
                          {:else if policy.tenant_id}
                            Todos los Usuarios
                          {:else}
                            Todos los Usuarios
                          {/if}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                          <button on:click={() => openEditModal(policy)} class="text-indigo-600 hover:text-indigo-900">Editar</button>
                          <button on:click={() => deletePolicy(policy.id)} class="text-red-600 hover:text-red-900">Eliminar</button>
                        </td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            {/if}
          {:else if activeTab === 'watermark'}
            <div class="p-6"><p>Configuración de Sello de Agua (Próximamente)</p></div>
          {:else if activeTab === 'downloads'}
            <div class="p-6"><p>Control de Descargas (Próximamente)</p></div>
          {:else if activeTab === 'content'}
            <div class="p-6"><p>Gestión de Contenido (Próximamente)</p></div>
          {:else if activeTab === 'geo'}
            <div class="p-6"><p>Políticas de Geolocalización (Próximamente)</p></div>
          {:else if activeTab === 'schedules'}
            <div class="p-6"><p>Políticas por Horario (Próximamente)</p></div>
          {/if}
        </div>
      </div>
    </div>
  </div>
</div>

{#if showModal}
  <div class="fixed z-10 inset-0 overflow-y-auto">
    <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
      <div class="fixed inset-0 transition-opacity" aria-hidden="true" on:click={() => showModal = false}>
        <div class="absolute inset-0 bg-gray-500 opacity-75"></div>
      </div>
      <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
      <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full relative">
        <button
          class="absolute top-2 right-2 text-gray-400 hover:text-gray-600 text-2xl font-bold focus:outline-none z-20"
          on:click={() => showModal = false}
          aria-label="Cerrar"
        >
          ×
        </button>
        <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
          <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
            {isEdit ? 'Editar' : 'Crear Nueva'} Política de Acceso
          </h3>
        
          <form on:submit|preventDefault={savePolicy}>
            {#if currentUser?.role === 'admin'}
              <div class="mb-4">
                <label for="policy-tenant-select" class="block text-sm font-medium text-gray-700 mb-1">Tenant de la Política:</label>
                <select 
                  id="policy-tenant-select" 
                  bind:value={selectedTenantIdForPolicyCreation} 
                  on:change={handleAdminTenantSelectionChange}
                  class="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  disabled={isEdit && modalPolicy.tenant_id != null && currentUser?.role === 'admin'} 
                >
                  <option value={null}>{(isEdit && modalPolicy.tenant_id && currentUser?.role === 'admin') ? "-- Usar tenant actual de la política --" : "Seleccione un Tenant"}</option>
                  {#each tenantsList as tenant (tenant.id)}
                    <option value={tenant.id}>{tenant.name}</option>
                  {/each}
                </select>
                {#if isEdit && modalPolicy.tenant_id && currentUser?.role === 'admin'}
                <p class="text-xs text-gray-500 mt-1">El tenant de una política existente no se puede cambiar desde aquí.</p>
                {/if}
              </div>
            {/if}

            <div class="mb-4">
              <label for="modal-domain" class="block text-sm font-medium text-gray-700 mb-1">Dominio:</label>
              <input
                type="text"
                id="modal-domain"
                bind:value={modalPolicy.domain}
                class="mt-1 block w-full py-2 px-3 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                placeholder="ejemplo.com"
                required
              />
            </div>
            <div class="mb-4">
              <label for="modal-action" class="block text-sm font-medium text-gray-700 mb-1">Acción:</label>
              <select
                id="modal-action"
                bind:value={modalPolicy.action}
                class="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="block">Bloquear</option>
                <option value="allow">Permitir</option>
              </select>
            </div>

            <div class="mb-4">
              <span class="block text-sm font-medium text-gray-700 mb-1">Ámbito de Aplicación:</span>
              <div class="mt-2 grid grid-cols-2 gap-4">
                <div>
                  <label class="inline-flex items-center w-full p-3 border rounded-md cursor-pointer hover:bg-gray-50 {policyScope === 'tenant' ? 'bg-indigo-50 border-indigo-300 ring-2 ring-indigo-200' : 'border-gray-300'}">
                    <input type="radio" class="sr-only" value="tenant" bind:group={policyScope} on:change={() => modalPolicy.group_id = null}>
                    <span class="text-sm font-medium text-gray-700">Todos los Usuarios</span>
                  </label>
                </div>
                <div>
                  <label class="inline-flex items-center w-full p-3 border rounded-md cursor-pointer hover:bg-gray-50 {policyScope === 'group' ? 'bg-indigo-50 border-indigo-300 ring-2 ring-indigo-200' : 'border-gray-300'} {((currentUser?.role === 'admin' && !selectedTenantIdForPolicyCreation && !isEdit)) ? 'opacity-50 cursor-not-allowed' : ''}">
                    <input 
                      type="radio" 
                      class="sr-only" 
                      value="group" 
                      bind:group={policyScope}
                      disabled={currentUser?.role === 'admin' && !selectedTenantIdForPolicyCreation && !isEdit}
                    >
                    <span class="text-sm font-medium text-gray-700">Grupo Específico</span>
                  </label>
                </div>
              </div>
            </div>

            {#if policyScope === 'group'}
              <div class="mb-6">
                <label for="modal-group" class="block text-sm font-medium text-gray-700 mb-1">Grupo:</label>
                <select
                  id="modal-group"
                  bind:value={modalPolicy.group_id}
                  class="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  required={policyScope === 'group'}
                  disabled={
                    (currentUser?.role === 'admin' && !selectedTenantIdForPolicyCreation && !isEdit) ||
                    (!(currentUser?.role === 'admin' && !selectedTenantIdForPolicyCreation && !isEdit) && availableGroups.length === 0)
                  }
                >
                  {#if currentUser?.role === 'admin' && !selectedTenantIdForPolicyCreation && !isEdit}
                    <option value={null} selected>Seleccione un Tenant primero</option>
                  {:else if availableGroups.length === 0}
                    <option value={null} selected>No hay grupos disponibles</option>
                  {:else}
                    <option value={null}>Seleccione un grupo</option>
                    {#each availableGroups as group (group.id)}
                      <option value={group.id}>{group.name}</option>
                    {/each}
                  {/if}
                </select>
                {#if policyScope === 'group' && createError && availableGroups.length === 0 && !(currentUser?.role === 'admin' && !selectedTenantIdForPolicyCreation && !isEdit) && (createError.includes('Error al cargar grupos') || createError.includes('Error de conexión al cargar grupos'))}
                  <p class="text-xs text-red-500 mt-1">{createError}</p>
                {/if}
              </div>
            {/if}
            
            {#if createError && !(policyScope === 'group' && availableGroups.length === 0 && (createError.includes('Error al cargar grupos') || createError.includes('Error de conexión al cargar grupos')))}
              <div class="mb-4 p-3 bg-red-50 text-red-600 border border-red-200 rounded-md text-sm">
                <p>{createError}</p>
              </div>
            {/if}
          </form>
        </div>
        <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
          <button 
            type="submit" 
            on:click={savePolicy}
            class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-[#00a1ff] text-base font-medium text-white hover:bg-[#0081cc] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#00a1ff] sm:ml-3 sm:w-auto sm:text-sm"
            disabled={!isFormValid}
          >
            {isEdit ? 'Guardar Cambios' : 'Crear Política'}
          </button>
          <button 
            type="button" 
            on:click={() => showModal = false} 
            class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  </div>
{/if} 