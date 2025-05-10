<script lang="ts">
  import { page } from '$app/stores';
  import { derived } from 'svelte/store';
  import Navbar from '$lib/Navbar.svelte';

  // Enlaces específicos para el panel Athos Owner
  const athosLinks = [
    { label: 'Dashboard', href: '/athos/dashboard', id: 'dashboard' },
    { label: 'Admins', href: '/athos/admins', id: 'admins' },
    { label: 'Clientes', href: '/athos/clientes', id: 'clientes' },
    { label: 'Usuarios', href: '/athos/usuarios', id: 'usuarios' }
  ];

  // Detectar el enlace activo según la URL
  const active = derived(page, $page => $page.url.pathname.split('/')[2] || 'dashboard');
</script>

<Navbar links={athosLinks} active={$active} />
<slot />

<style>
nav a {
  transition: color 0.2s;
}
nav a.font-bold {
  color: #38bdf8;
}
</style> 