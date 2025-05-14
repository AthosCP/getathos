<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import Navbar from '$lib/Navbar.svelte';
  import { API_URL } from '$lib/config';

  interface User {
    id: string;
    email: string;
    role: string;
    status: string;
    created_at: string;
    last_login: string;
    tenant_id: string;
  }

  interface Group {
    id: string;
    name: string;
    status: string;
    user_count?: number;
  }

  let users: User[] = [];
  let loading = true;
  let error = '';
  let showCreateModal = false;
  let showEditModal = false;
  let selectedUser: User | null = null;
  let newUser = {
    email: '',
    password: '', 
    role: 'user', 
    tenant_id: ''
  };
  let activeTab = 'people';
  let groups: Group[] = [];
  let loadingGroups = true;
  let errorGroups = '';
  let showCreateGroupModal = false;
  let showEditGroupModal = false;
  let currentGroup = { id: '', name: '' };
  let selectedUsersForGroup: string[] = [];
  let groupError: string = '';

  let createModalActiveTab: 'simple' | 'massive' = 'simple';
  let massiveEmailsText: string = '';
  let createError: string = '';
  let massiveDefaultPassword: string = '';

  async function loadUsers() {
    loading = true;
    error = '';
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        goto('/login');
        return;
      }
      const response = await fetch(`${API_URL}/api/users`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      if (data.success) {
        users = data.data;
      } else {
        error = data.error || 'Error al cargar usuarios';
      }
    } catch (e) {
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }

  async function loadGroups() {
    loadingGroups = true;
    errorGroups = '';
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        goto('/login');
        return;
      }
      const response = await fetch(`${API_URL}/api/groups`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      if (data.success) {
        groups = data.data;
      } else {
        errorGroups = data.error || 'Error al cargar grupos';
      }
    } catch (e) {
      errorGroups = 'Error de conexión al cargar grupos';
    } finally {
      loadingGroups = false;
    }
  }

  function resetCreateModalState() {
    newUser = { email: '', password: '', role: 'user', tenant_id: '' };
    massiveEmailsText = '';
    createError = '';
    createModalActiveTab = 'simple';
    massiveDefaultPassword = '';
  }

  function resetGroupModalState() {
    currentGroup = { id: '', name: '' };
    selectedUsersForGroup = [];
    groupError = '';
  }

  async function createGroup() {
    groupError = '';
    if (!currentGroup.name.trim()) {
      groupError = 'El nombre del grupo es obligatorio.';
      return;
    }

    const token = localStorage.getItem('token');
    if (!token) {
      groupError = 'Autenticación requerida.';
      goto('/login');
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/groups`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          name: currentGroup.name,
          user_ids: selectedUsersForGroup 
        })
      });
      const data = await response.json();
      if (data.success) {
        groups = [...groups, data.data];
        showCreateGroupModal = false;
        resetGroupModalState();
      } else {
        groupError = data.error || 'Error al crear el grupo';
      }
    } catch (e) {
      groupError = 'Error de conexión al crear el grupo.';
    }
  }
  
  async function updateGroup() {
    groupError = '';
    if (!currentGroup.id) {
        groupError = 'ID de grupo no encontrado.';
        return;
    }
    if (!currentGroup.name.trim()) {
      groupError = 'El nombre del grupo es obligatorio.';
      return;
    }
    const token = localStorage.getItem('token');
    if (!token) {
      groupError = 'Autenticación requerida.';
      goto('/login');
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/groups/${currentGroup.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          name: currentGroup.name,
          user_ids: selectedUsersForGroup 
        })
      });
      const data = await response.json();
      if (data.success) {
        groups = groups.map(g => g.id === currentGroup.id ? data.data : g);
        showEditGroupModal = false;
        resetGroupModalState();
      } else {
        groupError = data.error || 'Error al actualizar el grupo';
      }
    } catch (e) {
      groupError = 'Error de conexión al actualizar el grupo.';
    }
  }

  function openEditGroupModal(group: Group) {
    currentGroup = { ...group };
    selectedUsersForGroup = [];
    showEditGroupModal = true;
  }

  async function createUser() {
    createError = '';
    const token = localStorage.getItem('token');
    if (!token) {
      goto('/login');
      return;
    }

    if (createModalActiveTab === 'simple') {
      if (!newUser.email.trim()) {
        createError = 'El correo electrónico es obligatorio.';
        return;
      }
      if (!newUser.password) { 
        createError = 'La contraseña es obligatoria.';
        return;
      }
      try {
        const response = await fetch(`${API_URL}/api/users`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(newUser) 
        });

        const data = await response.json();
        if (data.success) {
          users = [...users, data.data];
          showCreateModal = false;
          resetCreateModalState();
        } else {
          createError = data.error || 'Error al crear usuario';
        }
      } catch (e) {
        createError = 'Error de conexión al crear usuario.';
      }
    } else if (createModalActiveTab === 'massive') {
      if (!massiveDefaultPassword.trim()) {
        createError = 'La contraseña por defecto para carga masiva es obligatoria.';
        return;
      }
      let emailsToCreate: string[] = [];
      if (massiveEmailsText.trim()) {
        emailsToCreate = massiveEmailsText.split(',').map(email => email.trim()).filter(email => email);
      } else {
        createError = 'No se proporcionaron correos para la carga masiva.';
        return;
      }

      if (emailsToCreate.length === 0) {
        createError = 'No se proporcionaron correos válidos para la carga masiva.';
        return;
      }
      
      let createdCount = 0;
      let errors: string[] = [];

      for (const email of emailsToCreate) {
        if (!email) continue;
        try {
          const response = await fetch(`${API_URL}/api/users`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email: email, password: massiveDefaultPassword, role: 'user' })
          });
          const data = await response.json();
          if (data.success) {
            users = [...users, data.data];
            createdCount++;
          } else {
            errors.push(`Error con ${email}: ${data.error || 'desconocido'}`);
          }
        } catch (e) {
          errors.push(`Error de conexión con ${email}`);
        }
      }

      if (createdCount > 0 && errors.length === 0) {
        showCreateModal = false;
        resetCreateModalState();
      } else if (errors.length > 0) {
        createError = `Se crearon ${createdCount} usuarios. Errores: ${errors.join('; ')}`;
      }
       if (createdCount === 0 && errors.length === 0 && !massiveEmailsText.trim()) {
       } else if (createdCount === 0 && errors.length === 0){
         createError = "No se procesó ningún correo. Verifica el formato o la entrada.";
       }
    }
  }

  async function updateUser() {
    if (!selectedUser) return;

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/users/${selectedUser.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(selectedUser)
      });

      const data = await response.json();
      if (data.success) {
        users = users.map(u => u.id === selectedUser?.id ? data.data : u);
        showEditModal = false;
        selectedUser = null;
      } else {
        error = data.error || 'Error al actualizar usuario';
      }
    } catch (e) {
      error = 'Error de conexión';
    }
  }

  async function deleteUser(userId: string) {
    if (!confirm('¿Estás seguro de que deseas eliminar este usuario?')) return;

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();
      if (data.success) {
        users = users.filter(u => u.id !== userId);
      } else {
        error = data.error || 'Error al eliminar usuario';
      }
    } catch (e) {
      error = 'Error de conexión';
    }
  }

  onMount(async () => {
    const userRaw = localStorage.getItem('user');
    if (!userRaw) {
      goto('/login');
      return;
    }
    await loadUsers();
    await loadGroups();
  });
</script>

<Navbar active="users" />

<div class="min-h-screen bg-gray-100">
  <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
    <div class="px-4 sm:px-0">
      <h1 class="text-2xl font-semibold text-gray-900">Usuarios Protegidos</h1>

      <div class="border-b border-gray-200 mt-4">
        <nav class="-mb-px flex space-x-8">
          <button
            class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'people' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
            on:click={() => activeTab = 'people'}
          >
            Personas
          </button>
          <button
            class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'groups' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
            on:click={() => activeTab = 'groups'}
          >
            Grupos
          </button>
        </nav>
      </div>

      <div class="mt-6">
        <div class="bg-white shadow overflow-hidden sm:rounded-lg">
          {#if activeTab === 'people'}
          <div class="p-6 border-b border-gray-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h2 class="text-lg font-semibold text-gray-900 mb-1">
                Gestión de Usuarios
              </h2>
              <p class="text-gray-600 mb-0">
                Administra los usuarios que tienen acceso al sistema y sus permisos.
              </p>
            </div>
            <button
              on:click={() => showCreateModal = true}
              class="px-3 py-1.5 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
            >
              Crear Nuevo Usuario
            </button>
          </div>
          {/if}

          {#if activeTab === 'people'}
            {#if loading}
              <div class="text-center">Cargando...</div>
            {:else if error}
              <div class="text-red-500 text-center">{error}</div>
            {:else}
              <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th scope="col" class="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">Email</th>
                      <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Rol</th>
                      <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Estado</th>
                      <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Acciones</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-gray-200 bg-white">
                    {#each users as user}
                      <tr>
                        <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6">
                          {user.email}
                        </td>
                        <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                          {user.role}
                        </td>
                        <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                          {#if user.status === 'active' || user.status === 'activo'}
                            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 border border-green-200">Activo</span>
                          {:else}
                            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 border border-gray-200">Inactivo</span>
                          {/if}
                        </td>
                        <td class="whitespace-nowrap px-3 py-4 text-sm font-medium">
                          <button
                            on:click={() => {
                              selectedUser = { ...user };
                              showEditModal = true;
                            }}
                            class="text-indigo-600 hover:text-indigo-900 mr-4"
                          >
                            Editar
                          </button>
                          <button
                            on:click={() => deleteUser(user.id)}
                            class="text-red-600 hover:text-red-900"
                          >
                            Eliminar
                          </button>
                        </td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            {/if}
          {:else}
            <div class="bg-white shadow overflow-hidden sm:rounded-lg">
              <div class="p-6 border-b border-gray-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <h2 class="text-lg font-semibold text-gray-900 mb-1">Gestión de Grupos</h2>
                  <p class="text-gray-600 mb-0">Administra los grupos de usuarios para facilitar la gestión de permisos.</p>
                </div>
                <button
                  on:click={() => {
                    resetGroupModalState();
                    showCreateGroupModal = true;
                  }}
                  class="px-3 py-1.5 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
                >
                  Crear Nuevo Grupo
                </button>
              </div>
              {#if loadingGroups}
                <div class="text-center py-6 text-gray-500">Cargando grupos...</div>
              {:else if errorGroups}
                <div class="text-center py-6 text-red-500">{errorGroups}</div>
              {:else if groups.length === 0}
                <div class="text-center py-6 text-gray-400">No hay grupos registrados.</div>
              {:else}
                <div class="overflow-x-auto">
                  <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                      <tr>
                        <th scope="col" class="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">Nombre</th>
                        <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Usuarios</th>
                        <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Estado</th>
                        <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Acciones</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200 bg-white">
                      {#each groups as group}
                        <tr>
                          <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6">{group.name}</td>
                          <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{group.user_count || 0}</td>
                          <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                            {#if group.status === 'active' || group.status === 'activo'}
                              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 border border-green-200">Activo</span>
                            {:else}
                              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 border border-gray-200">Inactivo</span>
                            {/if}
                          </td>
                          <td class="whitespace-nowrap px-3 py-4 text-sm font-medium">
                            <button on:click={() => openEditGroupModal(group)} class="text-indigo-600 hover:text-indigo-900 mr-4">Editar</button>
                            <button on:click={() => {/* TODO: deleteGroup(group.id) */}} class="text-red-600 hover:text-red-900">Eliminar</button>
                          </td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              {/if}
            </div>
          {/if}
        </div>
      </div>
    </div>
  </main>
</div>

{#if showCreateModal}
  <div class="fixed z-10 inset-0 overflow-y-auto">
    <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
      <div class="fixed inset-0 transition-opacity" aria-hidden="true" on:click={() => { showCreateModal = false; resetCreateModalState(); }}>
        <div class="absolute inset-0 bg-gray-500 opacity-75"></div>
      </div>
      <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
      <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full relative">
        <button
          class="absolute top-2 right-2 text-gray-400 hover:text-gray-600 text-2xl font-bold focus:outline-none z-20"
          on:click={() => { showCreateModal = false; resetCreateModalState(); }}
          aria-label="Cerrar"
        >
          ×
        </button>
        <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
          <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
            Crear Nuevo Usuario
          </h3>
          
          <div class="border-b border-gray-200 mb-4">
            <nav class="-mb-px flex space-x-8" aria-label="Tabs">
              <button
                on:click={() => createModalActiveTab = 'simple'}
                class="{createModalActiveTab === 'simple' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'} whitespace-nowrap py-3 px-1 border-b-2 font-medium text-sm"
              >
                Carga Simple
              </button>
              <button
                on:click={() => createModalActiveTab = 'massive'}
                class="{createModalActiveTab === 'massive' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'} whitespace-nowrap py-3 px-1 border-b-2 font-medium text-sm"
              >
                Carga Masiva
              </button>
            </nav>
          </div>

          {#if createModalActiveTab === 'simple'}
            <div class="space-y-4">
              <div>
                <label for="email-create" class="block text-sm font-medium text-gray-700">Correo Electrónico</label>
                <div class="mt-1">
                  <input type="email" name="email-create" id="email-create" bind:value={newUser.email} class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md p-2" placeholder="usuario@ejemplo.com"/>
                </div>
              </div>
              <div>
                <label for="password-create" class="block text-sm font-medium text-gray-700">Contraseña</label>
                <div class="mt-1">
                  <input type="password" name="password-create" id="password-create" bind:value={newUser.password} class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md p-2" placeholder="Contraseña"/>
                </div>
              </div>
              <div>
                <label for="role-create" class="block text-sm font-medium text-gray-700">Rol</label>
                <select id="role-create" name="role-create" bind:value={newUser.role} class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md">
                  <option value="user">Usuario</option>
                  <option value="admin">Administrador</option>
                </select>
              </div>
            </div>
          {:else if createModalActiveTab === 'massive'}
            <div>
              <p class="text-sm text-gray-600 mb-3">
                Pega una lista de correos electrónicos separados por coma.
              </p>
              <div>
                <label for="massive-emails" class="block text-sm font-medium text-gray-700">
                  Pegar correos (separados por coma)
                </label>
                <textarea
                  id="massive-emails"
                  rows="4"
                  bind:value={massiveEmailsText}
                  class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md p-2 mt-1"
                  placeholder="correo1@ejemplo.com, correo2@ejemplo.com, ..."
                ></textarea>
              </div>
              <div class="mt-4">
                <label for="massive-default-password" class="block text-sm font-medium text-gray-700">Contraseña por Defecto para Carga Masiva</label>
                <div class="mt-1">
                  <input type="password" name="massive-default-password" id="massive-default-password" bind:value={massiveDefaultPassword} class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md p-2" placeholder="Contraseña por defecto"/>
                </div>
              </div>
            </div>
          {/if}
          
          {#if createError}
            <p class="text-sm text-red-600 mt-3">{createError}</p>
          {/if}
        </div>

        <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
          <button
            type="button"
            on:click={createUser}
            class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm"
          >
            Guardar
          </button>
          <button
            type="button"
            on:click={() => { showCreateModal = false; resetCreateModalState(); }}
            class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

{#if showEditModal && selectedUser}
  <div class="fixed z-10 inset-0 overflow-y-auto">
    <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
      <div class="fixed inset-0 transition-opacity" aria-hidden="true" on:click={() => { showEditModal = false; selectedUser = null; }}>
        <div class="absolute inset-0 bg-gray-500 opacity-75"></div>
      </div>
      <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
      <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full relative">
        <button
          class="absolute top-2 right-2 text-gray-400 hover:text-gray-600 text-2xl font-bold focus:outline-none z-20"
          on:click={() => { showEditModal = false; selectedUser = null; }}
          aria-label="Cerrar"
        >
          ×
        </button>
        <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
          <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
            Editar Usuario
          </h3>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700">Email</label>
              <input
                type="email"
                bind:value={selectedUser.email}
                disabled
                class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 bg-gray-50 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Rol</label>
              <select
                bind:value={selectedUser.role}
                class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="user">Usuario</option>
                <option value="admin">Administrador</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Estado</label>
              <select
                bind:value={selectedUser.status}
                class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="active">Activo</option>
                <option value="inactive">Inactivo</option>
              </select>
            </div>
          </div>
        </div>
        <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
          <button
            on:click={updateUser}
            class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm"
          >
            Guardar
          </button>
          <button
            type="button" 
            on:click={() => {
              showEditModal = false;
              selectedUser = null;
            }}
            class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

{#if showCreateGroupModal || showEditGroupModal}
  <div class="fixed z-10 inset-0 overflow-y-auto">
    <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
      <div class="fixed inset-0 transition-opacity" aria-hidden="true" on:click={() => { showCreateGroupModal = false; showEditGroupModal = false; resetGroupModalState(); }}>
        <div class="absolute inset-0 bg-gray-500 opacity-75"></div>
      </div>
      <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
      <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full relative">
        <button
          class="absolute top-2 right-2 text-gray-400 hover:text-gray-600 text-2xl font-bold focus:outline-none z-20"
          on:click={() => { showCreateGroupModal = false; showEditGroupModal = false; resetGroupModalState(); }}
          aria-label="Cerrar"
        >
          ×
        </button>
        <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
          <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
            {showEditGroupModal ? 'Editar' : 'Crear Nuevo'} Grupo
          </h3>
          <div class="space-y-4">
            <div>
              <label for="group-name" class="block text-sm font-medium text-gray-700">Nombre del Grupo</label>
              <input type="text" id="group-name" bind:value={currentGroup.name} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" placeholder="Ej: Marketing"/>
            </div>
            <div>
              <label for="group-users" class="block text-sm font-medium text-gray-700">Asociar Usuarios</label>
              {#if users.length === 0}
                <p class="text-sm text-gray-500 mt-1">No hay usuarios para seleccionar. Primero crea usuarios en la pestaña "Personas".</p>
              {:else}
                <div class="mt-1 max-h-60 overflow-y-auto border border-gray-300 rounded-md p-2">
                  {#each users as user (user.id)}
                    <label class="flex items-center space-x-3 py-1">
                      <input type="checkbox" bind:group={selectedUsersForGroup} value={user.id} class="focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300 rounded"/>
                      <span class="text-sm text-gray-700">{user.email}</span>
                    </label>
                  {/each}
                </div>
              {/if}
            </div>
            {#if groupError}
              <p class="text-sm text-red-500">{groupError}</p>
            {/if}
          </div>
        </div>
        <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
          <button
            type="button"
            on:click={showEditGroupModal ? updateGroup : createGroup}
            class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm"
          >
            {showEditGroupModal ? 'Guardar Cambios' : 'Crear Grupo'}
          </button>
          <button
            type="button"
            on:click={() => { showCreateGroupModal = false; showEditGroupModal = false; resetGroupModalState(); }}
            class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  </div>
{/if} 