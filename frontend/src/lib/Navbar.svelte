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

<nav class="bg-black shadow-sm mb-0">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex justify-between h-16 items-center">
      <div class="flex items-center">
        <div class="flex-shrink-0 flex items-center">
          <a href="/dashboard" class="flex items-center">
            <!-- Typo logo con efecto glow -->
            <img 
              src="/images/typo.png" 
              alt="Athos" 
              class="h-32 w-auto glow-effect -my-8"
              style="filter: drop-shadow(0 0 10px #00a1ff);"
            />
          </a>
        </div>
        <div class="ml-6 flex h-16">
          {#each links as link}
            <a
              href={link.href}
              class="inline-flex items-center px-4 h-full text-gray-300 hover:text-white {active === link.id ? 'border-b-2 border-[#00a1ff] text-[#00a1ff]' : 'border-b-2 border-transparent'}"
            >
              {link.label}
            </a>
          {/each}
        </div>
      </div>
      <div class="flex items-center space-x-4">
        <!-- Icono de perfil de usuario (oculto en móviles) -->
        <button
          class="text-[#3b4dff] hover:text-white focus:outline-none p-2 hidden sm:block"
          title="Perfil de Usuario"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </button>
        
        <!-- Icono de cerrar sesión (visible en todos los tamaños) -->
        <button
          on:click={logout}
          class="text-[#3b4dff] hover:text-white focus:outline-none p-2"
          title="Cerrar Sesión"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 sm:h-6 sm:w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</nav>

<style>
  .glow-effect {
    filter: drop-shadow(0 0 10px rgba(0, 161, 255, 0.8));
  }
</style> 