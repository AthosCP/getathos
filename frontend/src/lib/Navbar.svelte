<script lang="ts">
  import { goto } from '$app/navigation';
  import { auth } from '$lib/auth';

  export let active: string = 'dashboard';
  export let links: { label: string; href: string; id: string }[] = [
    { label: 'Dashboard', href: '/dashboard', id: 'dashboard' },
    { label: 'Usuarios', href: '/users', id: 'users' },
    { label: 'Políticas', href: '/policies', id: 'policies' },
    { label: 'Navegación', href: '/navigation', id: 'navigation' },
    { label: 'Alertas', href: '/alerts', id: 'alerts' }
  ];

  function logout() {
    auth.logout();
    goto('/login', { replaceState: true });
  }
</script>

<nav class="bg-white shadow-sm mb-0">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex justify-between h-16">
      <div class="flex">
        <div class="flex-shrink-0 flex items-center">
          <h1 class="text-xl font-bold text-indigo-600">Athos</h1>
        </div>
        <div class="ml-6 flex space-x-8">
          {#each links as link}
            <a
              href={link.href}
              class="inline-flex items-center px-1 pt-1 text-gray-500 hover:text-gray-700 {active === link.id ? 'border-b-2 border-indigo-500 text-gray-900' : ''}"
            >
              {link.label}
            </a>
          {/each}
        </div>
      </div>
      <div class="flex items-center">
        <button
          on:click={logout}
          class="ml-4 px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
        >
          Cerrar Sesión
        </button>
      </div>
    </div>
  </div>
</nav> 