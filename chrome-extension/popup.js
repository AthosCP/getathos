var t = (chrome.runtime.getURL("").startsWith("chrome-extension://"))
  ? "https://api.getathos.com"
  : "http://localhost:5001";

document.addEventListener('DOMContentLoaded', () => {
  const API_URL = t

  // Elementos del DOM
  const loginForm = document.getElementById('loginForm')
  const emailInput = document.getElementById('email')
  const passwordInput = document.getElementById('password')
  const errorMessage = document.getElementById('errorMessage')
  const welcomeMessage = document.getElementById('welcomeMessage')
  const policiesList = document.getElementById('policiesList')
  const logoutButton = document.getElementById('logoutButton')
  
  // Elementos para contador de bloqueos
  const blockCounter = document.createElement('div')
  blockCounter.id = 'blockCounter'
  blockCounter.className = 'block-counter'
  blockCounter.innerHTML = '<h4>Estadísticas</h4><p>Sitios bloqueados: <span id="blockedCount">0</span></p>'

  // Verificar estado de autenticación
  async function checkAuth() {
    try {
      const { jwt_token } = await chrome.storage.local.get('jwt_token')
      console.log("Token encontrado:", jwt_token ? "Sí" : "No")
      
      if (jwt_token) {
        // Verificar que el token es válido
        const response = await fetch(`${API_URL}/api/config`, {
          headers: {
            'Authorization': `Bearer ${jwt_token}`,
            'Content-Type': 'application/json'
          }
        })
        
        if (response.ok) {
          console.log("Token válido")
          showAuthenticatedUI()
          await fetchPolicies(jwt_token)
        } else {
          console.log("Token inválido")
          // Token inválido, limpiar
          await chrome.storage.local.remove('jwt_token')
          showLoginUI()
        }
      } else {
        showLoginUI()
      }
    } catch (error) {
      console.error("Error checking auth:", error)
      showError("Error de conexión")
    }
  }

  // Obtener políticas
  async function fetchPolicies(token) {
    if (!token) return;
    try {
      console.log("Obteniendo políticas con token:", token)
      const response = await fetch(`${API_URL}/api/policies`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        credentials: 'include'
      })

      if (!response.ok) {
        console.error("Error HTTP:", response.status, response.statusText)
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      console.log("Respuesta de políticas:", data)
      
      if (data.success) {
        displayPolicies(data.data)
      } else {
        console.error('Error al obtener políticas:', data.error)
        showError(data.error || "Error al obtener políticas")
      }
    } catch (error) {
      console.error("Error fetching policies:", error)
      showError("Error al obtener políticas")
    }
  }

  // Mostrar políticas en la UI
  function displayPolicies(policies) {
    if (policies.length === 0) {
      policiesList.innerHTML = '<p class="empty-state">No hay políticas activas</p>'
      return
    }

    // Separar por tipo de acción
    const blockedDomains = policies.filter(p => p.action === 'block')
    const allowedDomains = policies.filter(p => p.action === 'allow')

    let html = '<h3>Políticas activas</h3>'
    
    // Mostrar dominios bloqueados primero
    if (blockedDomains.length > 0) {
      html += '<h4>Dominios bloqueados</h4><ul class="blocked-domains">'
      html += blockedDomains.map(policy => `
        <li>
          <span class="domain">${policy.domain}</span>
          <span class="block">Bloqueado</span>
        </li>
      `).join('')
      html += '</ul>'
    }
    
    // Mostrar dominios permitidos
    if (allowedDomains.length > 0) {
      html += '<h4>Dominios permitidos</h4><ul class="allowed-domains">'
      html += allowedDomains.map(policy => `
        <li>
          <span class="domain">${policy.domain}</span>
          <span class="allow">Permitido</span>
        </li>
      `).join('')
      html += '</ul>'
    }

    policiesList.innerHTML = html
  }

  // Manejar login
  async function handleLogin(event) {
    event.preventDefault()
    try {
      showError("")
      const email = emailInput.value
      const password = passwordInput.value

      if (!email || !password) {
        showError("Por favor ingresa email y contraseña")
        return
      }

      console.log("Intentando login...")
      const response = await fetch(`${API_URL}/api/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password }),
        credentials: 'include'
      })

      const data = await response.json()
      console.log("Respuesta de login:", data)
      
      if (data.success) {
        console.log("Login exitoso, token:", data.access_token)
        await chrome.storage.local.set({ jwt_token: data.access_token })
        showAuthenticatedUI()
        await fetchPolicies(data.access_token)
      } else {
        console.error("Error en login:", data.error)
        showError(data.error || "Error al iniciar sesión")
      }
    } catch (error) {
      console.error("Error logging in:", error)
      showError("Error de conexión")
    }
  }

  // Manejar logout
  async function handleLogout() {
    try {
      console.log("Cerrando sesión...")
      await chrome.storage.local.remove('jwt_token')
      showLoginUI()
    } catch (error) {
      console.error("Error logging out:", error)
    }
  }

  // Mostrar UI de login
  function showLoginUI() {
    loginForm.style.display = 'block'
    welcomeMessage.style.display = 'none'
    policiesList.innerHTML = ''
    showError("")
  }

  // Mostrar UI autenticada
  function showAuthenticatedUI() {
    loginForm.style.display = 'none'
    welcomeMessage.style.display = 'block'
    
    // Agregar el contador de bloqueos después del welcomeMessage
    if (!document.getElementById('blockCounter')) {
      welcomeMessage.parentNode.insertBefore(blockCounter, welcomeMessage.nextSibling)
    }
    
    // Cargar contador de bloqueos
    loadBlockCount()
  }

  // Cargar contador de bloqueos desde el storage
  async function loadBlockCount() {
    try {
      const { blockedCount = 0 } = await chrome.storage.local.get('blockedCount')
      document.getElementById('blockedCount').textContent = blockedCount
    } catch (error) {
      console.error("Error loading block count:", error)
    }
  }

  // Mostrar error
  function showError(message) {
    errorMessage.textContent = message
    errorMessage.style.display = message ? 'block' : 'none'
  }

  // Event listeners
  loginForm.addEventListener('submit', handleLogin)
  logoutButton.addEventListener('click', handleLogout)

  // Inicializar
  checkAuth()
}) 